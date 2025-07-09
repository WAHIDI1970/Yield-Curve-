# mon_app_flask/app.py
from flask import Flask, render_template, request, send_file
import pandas as pd
import numpy as np
import io
from services.taux_processor import process_dataframe, interpolate_user_date

app = Flask(__name__)
app.secret_key = "super-secret-key"

df_resultats = None
df_forwards = None
date_base = None

@app.route("/", methods=["GET", "POST"])
def index():
    global df_resultats, df_forwards, date_base

    message, taux_interp, interp_date = "", None, None

    if request.method == "POST":
        if "upload" in request.files and request.files["upload"].filename != "":
            try:
                file = request.files["upload"]
                df = pd.read_csv(file, sep=';', skiprows=2, skipfooter=1, engine='python', dtype=str)
                message = "✅ CSV chargé"
            except Exception as e:
                return render_template("index.html", message=f"❌ Erreur : {e}")

        elif "bam_date" in request.form:
            from src.io_bam import import_bam_curve
            try:
                date_pub = pd.to_datetime(request.form["bam_date"])
                df = import_bam_curve(date_pub)
                message = "✅ Données BAM importées"
            except Exception as e:
                return render_template("index.html", message=f"❌ Erreur BAM : {e}")

        else:
            df = None

        try:
            df, df_forwards, date_base = process_dataframe(df)
            df_resultats = df
        except Exception as e:
            return render_template("index.html", message=f"❌ Erreur traitement : {e}")

    if request.method == "GET" and "date_interp" in request.args:
        saisie = request.args["date_interp"]
        if df_resultats is not None:
            try:
                taux_interp, interp_date = interpolate_user_date(saisie, df_resultats, date_base)
            except Exception as e:
                message = f"⚠️ Interpolation : {e}"

    return render_template("index.html",
                           df=df_resultats,
                           df_forwards=df_forwards,
                           taux_interp=taux_interp,
                           interp_date=interp_date,
                           message=message)

@app.route("/download")
def download():
    if df_resultats is not None:
        csv = df_resultats.to_csv(index=False, sep=';', decimal=',').encode("utf-8-sig")
        return send_file(io.BytesIO(csv), as_attachment=True, download_name="resultats_taux.csv", mimetype="text/csv")
    return "Aucun résultat disponible"

@app.route("/download_fw")
def download_fw():
    if df_forwards is not None:
        csv = df_forwards.to_csv(index=False, sep=';', decimal=',').encode("utf-8-sig")
        return send_file(io.BytesIO(csv), as_attachment=True, download_name="taux_forwards.csv", mimetype="text/csv")
    return "Aucun forward disponible"

# mon_app_flask/services/taux_processor.py
import pandas as pd
import numpy as np
from src.dates import get_base_date, calc_maturite, parse_date_flexible
from src.bootstrap import taux_actuariel, bootstrap_zc
from src.interpolation import interpolate_rate
from src.Forward import taux_forward

def process_dataframe(df):
    df.rename(columns={
        "Date échéance": "Echeance",
        "Date d'échéance": "Echeance",
        "Taux moyen": "Taux moyen pondéré"
    }, inplace=True, errors='ignore')

    if "Echeance" not in df.columns or "Taux moyen pondéré" not in df.columns:
        raise Exception("Colonnes manquantes")

    base_date = get_base_date(df, "Echeance")
    df["maturite_jours"] = df["Echeance"].apply(lambda s: calc_maturite(s, base_date))
    df = df.dropna(subset=["maturite_jours"])
    df["maturite_annees"] = df["maturite_jours"].astype(float) / 365
    df["Taux_decimal"] = df["Taux moyen pondéré"].str.replace('%', '').str.replace(',', '.').astype(float) / 100
    df = df.sort_values(by="maturite_annees").reset_index(drop=True)

    df["Taux_actuariel"] = df.apply(lambda r: taux_actuariel(r["maturite_annees"], r["Taux_decimal"]), axis=1)
    df["Taux_zero_coupon"] = bootstrap_zc(df)

    mats_start, mats_end, forwards = taux_forward(df["maturite_annees"], df["Taux_zero_coupon"])
    df_fw = pd.DataFrame({
        "De (années)": mats_start,
        "À (années)": mats_end,
        "Taux Forward (%)": forwards * 100
    })

    return df, df_fw, base_date

def interpolate_user_date(date_str, df, base_date):
    d = parse_date_flexible(date_str).date()
    if d <= base_date:
        raise Exception("La date doit être postérieure à la date de base.")
    maturite = (d - base_date).days / 365
    taux = interpolate_rate(df["maturite_annees"], df["Taux_zero_coupon"], np.array([maturite]))[0]
    return taux, d
