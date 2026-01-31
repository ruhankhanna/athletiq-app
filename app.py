# app.py (public site + contact → Google Sheets)
from flask import Flask, render_template, send_from_directory, redirect, request
from datetime import datetime
import os

# --- Google Sheets deps ---
from google.oauth2.service_account import Credentials
import gspread

app = Flask(__name__, static_folder="static", template_folder="templates")

# -----------------------------
# Globals / helpers
# -----------------------------
@app.context_processor
def inject_globals():
    # For footer: {{ current_year }}
    return {"current_year": datetime.utcnow().year}

def _gs_client():
    """
    Build a gspread client using a service account JSON pointed to by
    GOOGLE_APPLICATION_CREDENTIALS env var.
    """
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        raise RuntimeError("Missing GOOGLE_APPLICATION_CREDENTIALS or file not found.")
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)

def _append_waitlist_row(coach_name: str, email: str, school: str, role: str | None, notes: str | None):
    """
    Append a new row to the first sheet of the spreadsheet indicated by CONTACT_SHEET_ID.
    """
    sheet_id = os.getenv("WAITLIST_SHEET_ID")
    if not sheet_id:
        raise RuntimeError("WAITLIST_SHEET_ID not set.")
    gc = _gs_client()
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1

    # If sheet appears empty, write headers once
    try:
        a1 = ws.acell("A1").value
    except Exception:
        a1 = None
    if not a1:
        ws.append_row(["timestamp_utc", "coach_name", "email", "school", "role", "notes"])

    ws.append_row([
        datetime.utcnow().isoformat(timespec="seconds") + "Z",
        coach_name,
        email,
        school,
        role or "",
        notes or "",
    ])

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

# --- Waitlist (writes to Google Sheets) ---
@app.route("/waitlist", methods=["GET", "POST"])
def waitlist():
    if request.method == "POST":
        coach_name = (request.form.get("coach_name") or "").strip()
        email      = (request.form.get("email") or "").strip()
        school     = (request.form.get("school") or "").strip()
        role       = (request.form.get("role") or "").strip()
        notes      = (request.form.get("notes") or "").strip()

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

        # append to Google Sheet
        try:
            _append_waitlist_row(coach_name, email, school, role, notes)
        except Exception as e:
            # Log to server console; show generic error to user
            print(f"[WAITLIST ERROR] {e}")

            )
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
                            return render_template("contact.html", errors=errors, form=request.form, success=False)

# Redirect old/removed routes to home
@app.route("/rankings")
                            _append_contact_row(coach_name, email, school, role, notes)
@app.route("/register")
@app.route("/dashboard")
def retired_routes():
    return redirect("/")
                                "contact.html",
# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = bool(int(os.getenv("FLASK_DEBUG", "0")))
    app.run(host="0.0.0.0", port=port, debug=debug)
