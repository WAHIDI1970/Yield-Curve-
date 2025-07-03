## Yield-Curve
# 📈 Application Streamlit - Calcul des Taux BAM

Cette application permet :
- d'importer un fichier CSV des taux BAM,
- de calculer automatiquement :
  - la maturité (jours et années),
  - le taux actuariel,
  - le taux zéro coupon,
  - un taux interpolé pour une date cible.

## ▶️ Lancer en local

```bash
pip install -r requirements.txt
streamlit run Streamlit.py
