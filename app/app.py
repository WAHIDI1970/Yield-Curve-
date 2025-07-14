from flask import Flask, render_template, request, redirect, url_for, session, flash
import os

app = Flask(__name__)
app.secret_key = "super_secret_key"

@app.route("/", methods=["GET", "POST"])
def dashboard():
    result = None
    error = None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "import":
            flash("Importation function triggered!", "info")
        elif action == "calculate":
            flash("Calculation function triggered!", "success")
        elif action == "interpolate":
            flash("Interpolation function triggered!", "warning")
        else:
            flash("Unknown action.", "danger")

    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True)