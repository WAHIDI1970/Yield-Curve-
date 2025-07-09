import streamlit as st
import pandas as pd
import numpy as np

from src.io_bam import import_bam_curve
from src.dates import parse_date_flexible, get_base_date, calc_maturite
from src.interpolation import interpolate_rate
from src.bootstrap import taux_actuariel, bootstrap_zc
from src.Forward import taux_forward  # <-- Ajout du module de taux forwards

st.set_page_config(page_title="💼 Taux Quant", layout="wide")
st.title("📈 Calcul de taux actuariels, zéro-coupon & forwards")

# ------------------ INIT STATE ------------------
for var in ["df", "taux_calcules", "date_base"]:
    if var not in st.session_state:
        st.session_state[var] = None

# ------------------ IMPORT / UPLOAD ------------------
st.sidebar.header("⚙️ Paramètres")
mode = st.sidebar.radio("Source des données", ["Upload CSV", "Auto BAM"])

if mode == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader("📁 Fichier CSV", type="csv")
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file, sep=';', skiprows=2, skipfooter=1, engine='python', dtype=str)
            st.session_state.df = df
            st.session_state.taux_calcules = False
            st.sidebar.success("✅ Fichier chargé")
        except Exception as e:
            st.sidebar.error(f"❌ Erreur de lecture : {e}")
else:
    date_pub = st.sidebar.date_input("📅 Date publication BAM", value=pd.Timestamp.today().date())
    if st.sidebar.button("📡 Import BAM"):
        try:
            with st.spinner("Importation en cours..."):
                df = import_bam_curve(date_pub)
            st.session_state.df = df
            st.session_state.taux_calcules = False
            st.sidebar.success("✅ Import réussi")
        except Exception as e:
            st.sidebar.error(f"❌ Erreur import BAM : {e}")

# ------------------ AFFICHAGE DONNÉES ------------------
if st.session_state.df is None:
    st.info("📄 Veuillez charger ou importer une base de données pour continuer.")
    st.stop()

df = st.session_state.df.copy()

st.header("1️⃣ Données brutes")
st.dataframe(df, use_container_width=True)

# ------------------ PRÉ-TRAITEMENT ------------------
df.rename(columns={
    "Date échéance": "Echeance",
    "Date d'échéance": "Echeance",
    "Taux moyen": "Taux moyen pondéré"
}, inplace=True, errors='ignore')

if "Echeance" not in df.columns or "Taux moyen pondéré" not in df.columns:
    st.error("❌ Colonnes manquantes : 'Echeance' et/ou 'Taux moyen pondéré'")
    st.stop()

date_base = get_base_date(df, col_name="Echeance")
st.session_state.date_base = date_base

df["maturite_jours"] = df["Echeance"].apply(lambda s: calc_maturite(s, date_base))
df = df.dropna(subset=["maturite_jours"])
df["maturite_annees"] = df["maturite_jours"].astype(float) / 365
df["Taux_decimal"] = df["Taux moyen pondéré"].astype(str).str.replace('%', '', regex=False).str.replace(',', '.', regex=False).astype(float) / 100
df = df.sort_values(by="maturite_annees").reset_index(drop=True)

# ------------------ CALCUL TAUX ------------------
if st.button("🧮 Calculer les taux"):
    try:
        df["Taux_actuariel"] = df.apply(lambda r: taux_actuariel(r["maturite_annees"], r["Taux_decimal"]), axis=1)
        df["Taux_actuariel (%)"] = df["Taux_actuariel"] * 100
        df["Taux_zero_coupon"] = bootstrap_zc(df)
        df["Taux_zero_coupon (%)"] = df["Taux_zero_coupon"] * 100

        st.session_state.df = df
        st.session_state.taux_calcules = True

    except Exception as e:
        st.error(f"Erreur lors du calcul : {e}")
        st.stop()

# ------------------ RÉSULTATS ------------------
if st.session_state.taux_calcules:
    df = st.session_state.df
    st.header("2️⃣ Résultats calculés")
    st.dataframe(df[["Echeance", "maturite_annees", "Taux_actuariel (%)", "Taux_zero_coupon (%)"]])

    # Courbes
    st.subheader("📊 Courbes interpolées")
    mats = np.linspace(df["maturite_annees"].min(), df["maturite_annees"].max(), 100)

    zc_interp = interpolate_rate(df["maturite_annees"], df["Taux_zero_coupon"], mats)
    actuarial_interp = interpolate_rate(df["maturite_annees"], df["Taux_actuariel"], mats)

    chart_df = pd.DataFrame({
        "Maturité (années)": mats,
        "Taux ZC (%)": zc_interp * 100,
        "Taux Actuariel (%)": actuarial_interp * 100
    }).set_index("Maturité (années)")

    st.line_chart(chart_df)

    st.download_button(
        label="📥 Télécharger les résultats (CSV)",
        data=df.to_csv(index=False, sep=';', decimal=',').encode("utf-8-sig"),
        file_name="resultats_taux.csv"
    )

# ------------------ INTERPOLATION PERSONNALISÉE ------------------
if st.session_state.taux_calcules and "Taux_zero_coupon" in st.session_state.df.columns:
    st.header("3️⃣ Taux interpolé à une échéance personnalisée")

    mode = st.radio("Mode de saisie", ["📅 Sélection de date", "⌨️ Saisie manuelle (jj/mm/aaaa)"], key="mode_saisie")

    date_ech = None
    if mode == "📅 Sélection de date":
        date_ech = st.date_input("Date d’échéance", min_value=st.session_state.date_base)
    else:
        saisie = st.text_input("Entrez une date (ex: 15/08/2030)")
        if saisie:
            try:
                date_ech = parse_date_flexible(saisie).date()
                if date_ech <= st.session_state.date_base:
                    st.warning("⚠️ La date doit être postérieure à la date de base.")
                    date_ech = None
            except Exception:
                st.error("❌ Format de date invalide. Utilisez jj/mm/aaaa.")

    if date_ech:
        mat_user = (date_ech - st.session_state.date_base).days / 365
        df = st.session_state.df
        taux_interp = interpolate_rate(df["maturite_annees"], df["Taux_zero_coupon"], np.array([mat_user]))[0]
        st.success(f"📅 Échéance : {date_ech.strftime('%d/%m/%Y')} (maturité : {mat_user:.3f} ans)")
        st.metric("Taux Zéro-Coupon interpolé", f"{taux_interp*100:.4f} %")

# ------------------ TAUX FORWARDS ------------------
if st.session_state.taux_calcules and "Taux_zero_coupon" in st.session_state.df.columns:
    st.header("4️⃣ Taux Forwards implicites")

    df = st.session_state.df
    mats = df["maturite_annees"].to_numpy()
    zc = df["Taux_zero_coupon"].to_numpy()

    try:
        mats_start, mats_end, forwards = taux_forward(mats, zc)
        df_fw = pd.DataFrame({
            "De (années)": mats_start,
            "À (années)": mats_end,
            "Taux Forward (%)": forwards * 100
        })

        st.dataframe(df_fw, use_container_width=True)

        # Courbe
        st.subheader("📈 Courbe des Taux Forwards")
        st.line_chart(
            pd.DataFrame({
                "Forward (%)": forwards * 100
            }, index=mats_end)
        )

        # Téléchargement
        csv_fw = df_fw.to_csv(index=False, sep=';', decimal=',').encode("utf-8-sig")
        st.download_button("📥 Télécharger les taux forwards (CSV)", data=csv_fw, file_name="taux_forwards.csv")

    except Exception as e:
        st.error(f"Erreur lors du calcul des forwards : {e}")

# ------------------ RESET ------------------
with st.sidebar:
    if st.button("🔄 Réinitialiser"):
        st.session_state.clear()
        st.experimental_rerun()

