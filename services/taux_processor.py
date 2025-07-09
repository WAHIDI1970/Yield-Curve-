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

    # Forwards
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
