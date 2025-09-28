# app.py (minimal public site)
from flask import Flask, render_template, send_from_directory, redirect
from datetime import datetime
import os

# Create app
app = Flask(__name__, static_folder="static", template_folder="templates")

# Inject current year for footer use: {{ current_year }}
@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}

# --- Routes ---

@app.route("/")
def home():
    # Renders templates/index.html (your updated Home page)
    return render_template("index.html")

@app.route("/about")
def about():
    # Renders templates/about.html (your updated About page)
    return render_template("about.html")

# Health/monitoring endpoint (useful on Azure or any host)
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# Serve favicon if requested by browsers
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.static_folder, "images"),
        "favicon.png",
        mimetype="image/png"
    )

# Optional: redirect old/removed routes to home (since public site is simplified)
@app.route("/rankings")
@app.route("/login")
@app.route("/register")
@app.route("/dashboard")
def retired_routes():
    return redirect("/")

if __name__ == "__main__":
    # Keep defaults simple; override via env if needed (e.g., PORT=8080 FLASK_DEBUG=1)
    port = int(os.getenv("PORT", 8000))
    debug = bool(int(os.getenv("FLASK_DEBUG", "0")))
    app.run(host="0.0.0.0", port=port, debug=debug)
