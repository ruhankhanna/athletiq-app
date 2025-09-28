# app.py (public site + waitlist)
from flask import Flask, render_template, send_from_directory, redirect, request
from datetime import datetime
import csv
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# Inject current year for footer use: {{ current_year }}
@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# --- Waitlist ---
@app.route("/waitlist", methods=["GET", "POST"])
def waitlist():
    if request.method == "POST":
        coach_name = (request.form.get("coach_name") or "").strip()
        email = (request.form.get("email") or "").strip()
        school = (request.form.get("school") or "").strip()
        role = (request.form.get("role") or "").strip()
        notes = (request.form.get("notes") or "").strip()

        # super-light validation
        errors = []
        if not coach_name:
            errors.append("Please enter your name.")
        if not email or "@" not in email:
            errors.append("Please enter a valid email.")
        if not school:
            errors.append("Please enter your school/program.")

        if errors:
            return render_template("waitlist.html", errors=errors, form=request.form, success=False)

        # Append to CSV (no DB required)
        data_dir = os.path.join(os.getcwd(), "data")
        os.makedirs(data_dir, exist_ok=True)
        csv_path = os.path.join(data_dir, "waitlist.csv")
        is_new = not os.path.exists(csv_path)

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if is_new:
                writer.writerow(["timestamp_utc", "coach_name", "email", "school", "role", "notes"])
            writer.writerow([
                datetime.utcnow().isoformat(),
                coach_name,
                email,
                school,
                role,
                notes
            ])

        return render_template("waitlist.html", success=True)

    # GET
    return render_template("waitlist.html", success=False)

# Health endpoint
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# Favicon
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.static_folder, "images"),
        "favicon.png",
        mimetype="image/png"
    )

# Redirect old/removed routes to home
@app.route("/rankings")
@app.route("/login")
@app.route("/register")
@app.route("/dashboard")
def retired_routes():
    return redirect("/")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = bool(int(os.getenv("FLASK_DEBUG", "0")))
    app.run(host="0.0.0.0", port=port, debug=debug)
