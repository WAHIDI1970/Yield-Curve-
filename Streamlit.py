import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime

# --- Configuration de la page Streamlit ---
st.set_page_config(page_title="Calculateur de Taux Zéro-Coupon", layout="wide")

# Titre de l'application
st.title("Calculateur de Taux Actuariel et Zéro-Coupon 📈")
st.write(
    "Téléversez un fichier CSV avec les colonnes 'Echeance' et 'Taux moyen pondéré' "
    "pour calculer la courbe des taux zéro-coupon par la méthode du bootstrapping."
)

# --- Fonctions de calcul (basées sur votre notebook) ---

def calculate_rates(df, base_date):
    """
    Calcule la maturité, le taux actuariel et le taux zéro-coupon à partir d'un DataFrame.

    Args:
        df (pd.DataFrame): DataFrame contenant les colonnes 'Echeance' et 'Taux moyen pondéré'.
        base_date (datetime): La date de référence pour les calculs de maturité.

    Returns:
        pd.DataFrame: Le DataFrame enrichi avec les nouvelles colonnes.
    """
    # Copie pour éviter les avertissements sur la modification de la vue
    df = df.copy()

    # S'assurer que les colonnes nécessaires existent
    if 'Echeance' not in df.columns or 'Taux moyen pondéré' not in df.columns:
        st.error("Le fichier CSV doit contenir les colonnes 'Echeance' et 'Taux moyen pondéré'.")
        return None

    try:
        # Étape 1 : Calculer la maturité en jours et en années
        df["maturite_en_jours"] = df["Echeance"].apply(
            lambda x: max((datetime.strptime(x, "%d/%m/%Y") - base_date).days, 1)
        )
        df["maturite_en_ans"] = df["maturite_en_jours"] / 365

        # Étape 2 : Conversion du taux en décimal
        df['Taux decimal'] = pd.to_numeric(df['Taux moyen pondéré'], errors='coerce') / 100

        # Étape 3 : Calcul du taux actuariel
        def taux_actuariel(row):
            T = row['maturite_en_ans']
            t = row['Taux decimal']
            if T < 1.0:
                n = 1 / T
                return (1 + t / n)**n - 1
            else:
                return t
        df['Taux actuariel'] = df.apply(taux_actuariel, axis=1)

        # Trier par maturité pour le bootstrapping
        df = df.sort_values(by="maturite_en_ans").reset_index(drop=True)

        # Étape 4 : Bootstrapping pour les taux zéro-coupon
        taux_zc_dict = {}
        zc_list = []

        for _, row in df.iterrows():
            T = row["maturite_en_ans"]
            # Le taux de coupon est supposé être le taux actuariel
            C = row["Taux actuariel"]

            if T <= 1.0:
                zc = C  # Pour T<=1, le taux ZC est le taux actuariel
            else:
                sum_coupons = 0.0
                # Somme des coupons intermédiaires actualisés
                # Note: cette boucle suppose un coupon annuel
                for k in range(1, int(np.floor(T)) + 1):
                    # Trouver le taux ZC pour le coupon intermédiaire
                    if k in taux_zc_dict:
                        z_k = taux_zc_dict[k]
                    else:
                        # Interpolation simple si le taux exact n'est pas trouvé
                        z_k = list(taux_zc_dict.values())[-1] if taux_zc_dict else C
                    sum_coupons += C / ((1 + z_k)**k)

                denom = 1 - sum_coupons
                # Sécurité pour éviter la division par zéro ou un dénominateur négatif
                if denom <= 0:
                    zc = C # Si le calcul échoue, on fallback sur le taux actuariel
                else:
                    zc = ((1 + C) / denom)**(1 / T) - 1

            # Arrondir la maturité pour la clé du dictionnaire
            taux_zc_dict[int(round(T))] = zc
            zc_list.append(zc)

        df["Taux zero coupon"] = zc_list
        df["Taux zero coupon (%)"] = df["Taux zero coupon"] * 100
        df["Taux actuariel (%)"] = df["Taux actuariel"] * 100

        return df

    except Exception as e:
        st.error(f"Une erreur est survenue lors du traitement des données : {e}")
        return None


# --- Interface utilisateur de Streamlit ---

# Zone de téléversement
uploaded_file = st.file_uploader("Choisissez un fichier CSV", type="csv")

if uploaded_file is not None:
    # Lecture des données
    data = pd.read_csv(uploaded_file)
    st.success("Fichier téléversé avec succès ! Voici un aperçu des données brutes :")
    st.dataframe(data.head())

    # Définir une date de base pour le calcul
    # On utilise la date du jour comme référence, modifiable par l'utilisateur
    base_date_input = st.date_input("Date de base pour le calcul de la maturité", datetime.now())

    # Bouton pour lancer le calcul
    if st.button("Calculer les Taux"):
        with st.spinner("Calcul en cours..."):
            # Appel de la fonction de traitement
            processed_df = calculate_rates(data, datetime.combine(base_date_input, datetime.min.time()))

            if processed_df is not None:
                st.success("Calculs terminés !")

                # Affichage des résultats
                st.subheader("Tableau des Taux Calculés")
                st.dataframe(processed_df[[
                    "Echeance",
                    "maturite_en_ans",
                    "Taux moyen pondéré",
                    "Taux actuariel (%)",
                    "Taux zero coupon (%)"
                ]].round(4))

                # Affichage du graphique de la courbe des taux
                st.subheader("Courbe des Taux")
                chart_data = processed_df.rename(columns={
                    "maturite_en_ans": "Maturité (années)",
                    "Taux actuariel (%)": "Taux Actuariel",
                    "Taux zero coupon (%)": "Taux Zéro-Coupon"
                })

                st.line_chart(
                    chart_data,
                    x="Maturité (années)",
                    y=["Taux Actuariel", "Taux Zéro-Coupon"]
                )

else:
    st.info("En attente du téléversement d'un fichier CSV.")