from flask import Flask, render_template, request, session, redirect, url_for
import pandas as pd
import os
import io
from datetime import date
from src.dates import get_base_date, calc_maturite
from src.io_bam import import_bam_curve
from src.bootstrap import taux_actuariel, bootstrap_zc
from src.Forward import taux_forward
from src.plotting import create_yield_curve_chart, create_forward_curve_chart
from src.interpolation import interpolate_rate

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'a_very_strong_dev_secret_key_901')
PICKLE_FILE = 'tmp_df.pkl'

def perform_calculations(df):
    df.rename(columns={
        "Date échéance": "Echeance", "Date d'échéance": "Echeance",
        "Taux moyen": "Taux moyen pondéré"
    }, inplace=True, errors='ignore')

    if "Echeance" not in df.columns or "Taux moyen pondéré" not in df.columns:
        raise ValueError("Colonnes 'Echeance' et/ou 'Taux moyen pondéré' introuvables.")

    date_base = get_base_date(df, col_name="Echeance")
    df["maturite_jours"] = df["Echeance"].apply(lambda s: calc_maturite(s, date_base))
    df.dropna(subset=["maturite_jours"], inplace=True)
    df["maturite_annees"] = df["maturite_jours"].astype(float) / 365.25
    df["Taux_decimal"] = df["Taux moyen pondéré"].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False).astype(float) / 100
    df.sort_values(by="maturite_annees", inplace=True)
    df["Taux_actuariel"] = df.apply(lambda r: taux_actuariel(r["maturite_annees"], r["Taux_decimal"]), axis=1)
    df["Taux_zero_coupon"] = bootstrap_zc(df)
    return df

@app.route('/', methods=['GET', 'POST'])
def index():
    df, df_fw = None, None
    error = None
    forward_mode = False
    zc_chart, forward_chart = None, None
    interpolated_rate = None
    interpolated_target = None
    interpolated_maturity = None

    if request.method == 'GET' and not session.get('has_data'):
        try:
            today_str = date.today().isoformat()
            df = import_bam_curve(date.today())
            df = perform_calculations(df)
            zc_chart = create_yield_curve_chart(df)
            df.to_pickle(PICKLE_FILE)
            session['has_data'] = True
            session['last_mode'] = 'bam'
            session['last_date'] = today_str
        except Exception as e:
            error = f"❌ Erreur lors du chargement automatique : {e}"
            session.clear()
    elif session.get('has_data') and os.path.exists(PICKLE_FILE):
        try:
            df = pd.read_pickle(PICKLE_FILE)
            if request.method == 'GET':
                zc_chart = create_yield_curve_chart(df)
        except (FileNotFoundError, EOFError):
            session.clear()
            error = "❌ Erreur de chargement des données de session."

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'reset':
            session.clear()
            if os.path.exists(PICKLE_FILE):
                os.remove(PICKLE_FILE)
            return redirect(url_for('index'))

        elif action == 'calculate_curves':
            mode = request.form.get('mode')
            raw_df = None
            try:
                if mode == "bam":
                    date_str = request.form.get("date_bam")
                    date_pub = pd.to_datetime(date_str).date() if date_str else date.today()
                    raw_df = import_bam_curve(date_pub)
                    session['last_mode'] = 'bam'
                    session['last_date'] = date_str
                elif mode == "upload":
                    file = request.files.get('csv')
                    if file and file.filename:
                        csv_data = io.StringIO(file.stream.read().decode("UTF-8"))
                        raw_df = pd.read_csv(csv_data, sep=';', skiprows=2, skipfooter=1, engine='python', dtype=str)
                        session['last_mode'] = 'upload'
                        session['last_filename'] = file.filename
                    else:
                        error = "❌ Aucun fichier CSV sélectionné."
                if raw_df is not None:
                    df = perform_calculations(raw_df)
                    zc_chart = create_yield_curve_chart(df)
                    df.to_pickle(PICKLE_FILE)
                    session['has_data'] = True
                    error = None
                elif not error:
                    error = "❌ Aucune donnée n'a été importée."
            except Exception as e:
                error = f"❌ Erreur lors du calcul des taux : {e}"
                session.clear()

        elif action == 'calculate_forwards':
            forward_mode = True
            if df is not None and 'Taux_zero_coupon' in df.columns:
                zc_chart = create_yield_curve_chart(df)
                if len(df) > 1:
                    mats = df["maturite_annees"].to_numpy()
                    zc = df["Taux_zero_coupon"].to_numpy()
                    mats_start, mats_end, forwards = taux_forward(mats, zc)
                    df_fw = pd.DataFrame({
                        "De (années)": [f"{x:.2f}" for x in mats_start], 
                        "À (années)": [f"{x:.2f}" for x in mats_end], 
                        "Taux Forward (%)": [f"{x*100:.2f}" for x in forwards]
                    })
                    forward_chart = create_forward_curve_chart(mats_end, forwards)
                else:
                    error = "❌ Données insuffisantes pour calculer les taux forwards."
            else:
                error = "❌ Veuillez d'abord importer et calculer les courbes de base."

        elif action == 'interpolate_date':
            date_str = request.form.get("target_date")
            if df is not None and 'Taux_zero_coupon' in df.columns and date_str:
                try:
                    date_cible = pd.to_datetime(date_str).date()
                    base_date = get_base_date(df)
                    jours = calc_maturite(date_cible.isoformat(), base_date)
                    maturity = jours / 365.25
                    mats = df["maturite_annees"].to_numpy()
                    zc = df["Taux_zero_coupon"].to_numpy()
                    interpolated = interpolate_rate(mats, zc, maturity)
                    interpolated_rate = f"{interpolated * 100:.4f}"
                    interpolated_target = date_cible.strftime("%d/%m/%Y")
                    interpolated_maturity = f"{maturity:.2f}"
                    zc_chart = create_yield_curve_chart(df)
                except Exception as e:
                    error = f"❌ Erreur lors de l'interpolation par date : {e}"
            else:
                error = "❌ Date invalide ou données manquantes pour l’interpolation."

    df_display = None
    if df is not None:
        df_display = df.copy()
        for col in ['Taux_decimal', 'Taux_actuariel', 'Taux_zero_coupon']:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: f"{x*100:.4f}%")
        if 'maturite_annees' in df_display.columns:
            df_display['maturite_annees'] = df_display['maturite_annees'].apply(lambda x: f"{x:.2f}")

    return render_template(
        "layout.html",
        df_table=df_display.to_html(classes='table table-striped', index=False) if df_display is not None else None,
        df_fw_table=df_fw.to_html(classes='table table-striped', index=False) if df_fw is not None else None,
        forward_mode=forward_mode,
        error=error,
        zc_chart=zc_chart,
        forward_chart=forward_chart,
        has_data=session.get('has_data', False),
        last_mode=session.get('last_mode', 'bam'),
        last_date=session.get('last_date', date.today().isoformat()),
        interpolated_rate=interpolated_rate,
        interpolated_target=interpolated_target,
        interpolated_maturity=interpolated_maturity
    )

if __name__ == '__main__':
    app.run(debug=True)

