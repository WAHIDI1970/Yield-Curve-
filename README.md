# 📈 Yield Curve Analyzer – BAM Curve Dashboard

Ce projet est un **dashboard interactif** pour l'analyse et le calcul des **taux actuariels**, **taux zéro coupon**, et **taux forward** à partir des courbes de taux publiées par la **Banque Al-Maghrib (BAM)**. Il est conçu pour les analystes financiers, ingénieurs quantitatifs, chercheurs ou toute personne intéressée par la modélisation des courbes de taux.

## 🧰 Fonctionnalités principales

- 📥 Importation de courbes BAM au format CSV
- 📊 Visualisation interactive des courbes (Plotly)
- 🧮 Calcul des taux actuariels
- 🪙 Bootstrap des taux zéro coupon
- ⏩ Calcul des taux forwards pour différentes maturités
- 🧩 Interpolation personnalisée d’échéance
- 🧑‍💻 Interface web professionnelle (Flask/Streamlit)
- 🐳 Dockerisation pour déploiement simple

## 📂 Structure du projet

```bash
yield-curve-analyzer/
│
├── app.py                     # Point d'entrée principal (Flask ou Streamlit)
├── requirements.txt           # Dépendances Python
├── Dockerfile                 # Image Docker (si utilisé)
├── README.md                  # Fichier de documentation
├── static/                    # Fichiers CSS, JS, images
├── templates/                 # Layout HTML (Flask)
│
├── data/                      # Données d’entrée (CSV BAM)
├── output/                    # Résultats calculés/exportés
│
└── app/src/                       # Modules Python
       ├── io_bam.py              # Importation et nettoyage des données BAM
       ├── dates.py               # Gestion des échéances et maturités
       ├── bootstrap.py           # Calcul des taux actuariels et ZC
       ├── interpolation.py       # Interpolation spline/linéaire
       └── forward.py             # Calculs des taux forwards






<img width="944" height="430" alt="image" src="https://github.com/user-attachments/assets/c2933b7c-b083-4728-97b9-041176d02d93" />

<img width="794" height="422" alt="image" src="https://github.com/user-attachments/assets/dcb533f9-da06-4306-a54b-70af8f2c053f" />

<img width="785" height="333" alt="image" src="https://github.com/user-attachments/assets/b26ce523-98e3-4ab3-84ea-003daa3b7f7f" />





