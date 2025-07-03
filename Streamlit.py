import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from scipy.interpolate import interp1d

st.set_page_config(page_title="Calcul Taux - Courbe BAM", layout="wide")

st.title("📈 Application de calcul des taux (actuariel & zéro coupon)")

# Upload du fichier
uploaded_file = st.file_uploader("Choisissez un fichier CSV contenant les données BAM", type=["csv"])

if uploaded_file is not None:
    # Lecture des données
    df = pd.read_csv(uploaded_file)

    # Nettoyage initial
    if 'Transactions' in df.columns:
        df.drop('Transactions', axis=1, inplace=True)
    if 'Date de valeur' in df.columns:
        df.drop('Date de valeur', axis=1, inplace=True)
    if df.shape[0] > 10:
        df = df.drop(index=10)  # comme dans le notebook original

    # Date de base = date de la première ligne
    try:
        date_base = datetime.strptime(df["Echeance"][0], "%d/%m/%Y")
    except:
        date_base = datetime.today()

    # Maturité en jours
    df["maturite_en_jours"] = df["Echeance"].apply(
        lambda x: max((datetime.strptime(x, "%d/%m/%Y") - date_base).days,1)
    )

    # Maturité en années
    df["maturite_en_ans"] = df["maturite_en_jours"] / 365

    # Taux en décimal
    df["Taux decimal"] = df["Taux moyen pondéré"] / 100

    # Fonction de calcul du taux actuariel
    def taux_actuariel(row):
        T = row['maturite_en_ans']
        t = row['Taux decimal']
        if T < 1.0:
            n = 1 / T
            return (1 + t / n)**n - 1
        else:
            return t

    df["Taux actuariel"] = df.apply(taux_actuariel, axis=1)
    df["Taux actuariel (%)"] = df["Taux actuariel"] * 100

    # Calcul taux zéro coupon
    taux_zc_dict = {}
    zc_list = []

    for idx, row in df.iterrows():
        T = row["maturite_en_ans"]
        r = row["Taux actuariel"]
        C = r

        if T <= 1.0:
            zc = r
        else:
            sum_coupons = 0.0
            for k in range(1, int(np.floor(T)) + 1):
                z_k = taux_zc_dict.get(k, list(taux_zc_dict.values())[-1] if taux_zc_dict else r)
                sum_coupons += C / (1 + z_k)**k

            denom = 1 - sum_coupons
            if denom <= 0:
                zc = r
            else:
                zc = ((1 + C) / denom) ** (1 / T) - 1

        taux_zc_dict[int(round(T))] = zc
        zc_list.append(zc)

    df["Taux zero coupon"] = zc_list
    df["Taux zero coupon (%)"] = df["Taux zero coupon"] * 100

    # Affichage des résultats
    st.subheader("📊 Résultat des calculs :")
    st.dataframe(df[[
        "Echeance",
        "maturite_en_jours",
        "maturite_en_ans",
        "Taux moyen pondéré",
        "Taux actuariel (%)",
        "Taux zero coupon (%)"
    ]], use_container_width=True)

    # Interpolation pour date personnalisée
    st.subheader("🔍 Interpolation du taux pour une nouvelle échéance")
    date_user = st.date_input("Sélectionnez une nouvelle date d'échéance")

    if date_user:
        delta = (date_user - date_base).days
        maturity_user = delta / 365

        interpolation_func = interp1d(df["maturite_en_ans"], df["Taux zero coupon"], kind='linear', fill_value="extrapolate")
        taux_interpole = interpolation_func(maturity_user) * 100

        st.markdown(f"**Taux zéro coupon interpolé pour la maturité de {maturity_user:.2f} ans : {taux_interpole:.3f}%**")

    # Option de téléchargement
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Télécharger les résultats au format CSV", data=csv, file_name="resultats_taux.csv", mime="text/csv")

else:
    st.info("Veuillez importer un fichier CSV contenant les colonnes 'Echeance', 'Taux moyen pondéré' et 'Date'.")
    



