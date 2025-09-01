from flask import Flask, render_template, redirect, url_for, session, request, jsonify, flash
from authlib.integrations.flask_client import OAuth
from flask_migrate import Migrate
from sqlalchemy.exc import SQLAlchemyError
from flask_mysqldb import MySQL
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import math
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import MySQLdb
from datetime import timedelta
from ratings import get_event_rating
import re
from athletic_scraper import close_driver
from athletic_scraper import scrape_filtered_results
import MySQLdb.cursors
from datetime import date
import atexit
import time
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from athletic_scraper import (
    driver,
    login_athletic_net,
    scrape_filtered_results,
    close_driver,
)
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from email_validator import validate_email, EmailNotValidError
from selenium.common.exceptions import WebDriverException


from dotenv import load_dotenv
import os
load_dotenv()


def generate_slug(first_name, last_name):
    if not first_name or not last_name:
        return "user"
    base = f"{first_name}-{last_name}".lower()
    return re.sub(r'[^a-z0-9\-]', '', base)


def generate_unique_slug(first_name, last_name, cur):
    base = generate_slug(first_name, last_name)
    slug = base
    counter = 1
    while True:
        cur.execute("SELECT 1 FROM user WHERE slug = %s", (slug,))
        if not cur.fetchone():
            break
        slug = f"{base}-{counter}"
        counter += 1
    return slug


def convert_time_to_seconds(time_str):
    try:
        # Remove "c" or "h" suffixes
        cleaned_time_str = re.sub(r'[a-zA-Z]', '', time_str)
        
        if ':' in cleaned_time_str:
            parts = cleaned_time_str.split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            elif len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        
        return float(cleaned_time_str)
    except:
        return None


def normalize_event_name(event_name):
    mapping = {
        "100 Meters": "100M",
        "200 Meters": "200M",
        "400 Meters": "400M",
        "800 Meters": "800M",
        "1500 Meters": "1500M",
        "1600 Meters": "1600M",
        "3000 Meters": "3000M",
        "3200 Meters": "3200M",
        "5000 Meters": "5K",
        "5K XC": "5K",
        "XC": "5K",
    }
    return mapping.get(event_name, event_name.replace(" Meters", "M").upper())

def rescrape_all_users():
    with app.app_context():
        cur = mysql.connection.cursor()
        cur.execute("SELECT email, profile_link FROM user WHERE profile_link IS NOT NULL")
        users = cur.fetchall()

        for email, link in users:
            try:
                scraped_results = scrape_filtered_results(link)

                # Delete previous results
                cur.execute("DELETE FROM results WHERE email = %s", (email,))

                y_values = []
                for event, time_str, date, meet, place in scraped_results:
                    normalized_event = normalize_event_name(event)

                    try:
                        time_in_sec = convert_time_to_seconds(time_str)
                        if time_in_sec is None:
                            continue

                        rating = get_event_rating(normalized_event, time_in_sec)
                        if rating is None:
                            continue

                        date_obj = datetime.strptime(date, "%b %d, %Y")
                        formatted_date = date_obj.strftime("%Y-%m-%d")

                        cleaned_time_str = re.sub(r'[a-zA-Z]', '', time_str).strip()

                        cur.execute(
                            """
                            INSERT INTO results
                            (email, event_name, event_time, event_date, meet_name, rating, finishing_place)
                            VALUES
                            (%s, %s, %s, %s, %s, %s, %s)
                            """,
                            (email, normalized_event, cleaned_time_str, formatted_date, meet, rating, place)
                        )
                        y_values.append(rating)
                    except Exception as inner_e:
                        print(f"[ERROR] Failed to process result: {event}, error: {inner_e}")
                        continue

                # Update average rating in user table
                if y_values:
                    avg_rating = sum(y_values) / len(y_values)
                    cur.execute("UPDATE user SET rating = %s WHERE email = %s", (avg_rating, email))

                mysql.connection.commit()
            except Exception as e:
                print(f"[FAILED to scrape {email}]: {e}")

        cur.close()



# -------------------------------------------------------------------
# GHOST PROFILE IMPORTER
# -------------------------------------------------------------------
def import_ghost_profiles(start_id: int, end_id: int, batch: int = 100):
    with app.app_context():
        cur = mysql.connection.cursor()
        for athlete_id in range(start_id, end_id + 1):
            profile_url = f"https://www.athletic.net/TrackAndField/Athlete.aspx?AID={athlete_id}"
            try:
                driver.get(profile_url)
                time.sleep(2)
                soup = BeautifulSoup(driver.page_source, "html.parser")
                name_tag = soup.select_one("a.me-2.text-sport")
                if not name_tag:
                    continue
                full_name = name_tag.get_text(strip=True)
                first, *last = full_name.split()
                last = " ".join(last) or ""
                slug = generate_slug(first, last)
                cur.execute("SELECT 1 FROM user WHERE slug=%s", (slug,))
                if cur.fetchone():
                    continue

                cur.execute("""
                    INSERT INTO user
                    (email, password, first_name, last_name, gender, birthday, age,
                    city, state, school, club, grad_year, profile_link, slug, is_ghost)
                    VALUES
                    (%s, %s, %s, %s, %s, %s, %s,
                     %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (
                    None, None, first, last, None, None, None,
                    None, None, None, None, None, profile_url, slug
                ))

                try:
                    scraped_results = scrape_filtered_results(profile_url)
                    y_values = []

                    for event, time_str, date, meet, place in scraped_results:
                        normalized = normalize_event_name(event)
                        secs = convert_time_to_seconds(time_str)
                        if secs is None:
                            continue
                        rating = get_event_rating(normalized, secs)
                        if rating is None:
                            continue
                        formatted_date = datetime.strptime(date, "%b %d, %Y").strftime("%Y-%m-%d")
                        cleaned = re.sub(r"[a-zA-Z]", "", time_str).strip()
                        cur.execute("""
                            INSERT INTO results (email, event_name, event_time, event_date, meet_name, rating, finishing_place)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (None, normalized, cleaned, formatted_date, meet, rating, place))
                        y_values.append(rating)

                    if y_values:
                        avg = sum(y_values) / len(y_values)
                        cur.execute("UPDATE user SET rating = %s WHERE slug = %s", (avg, slug))

                except Exception as e:
                    print(f"[GHOST SCRAPE ERROR] Failed to scrape results for ghost {slug}: {e}")

                if athlete_id % batch == 0:
                    mysql.connection.commit()
                    print(f"[GHOST IMPORT] up to ID {athlete_id}")
            except Exception:
                continue
        mysql.connection.commit()
        cur.close()

# -------------------------------------------------------------------









app = Flask(__name__)
app.permanent_session_lifetime = timedelta(days=2)  # or hours=1, minutes=30, etc.

app.secret_key = os.getenv('SECRET_KEY')


app.config.update(
    MAIL_SERVER   = os.getenv('MAIL_SERVER'),
    MAIL_PORT     = int(os.getenv('MAIL_PORT')),
    MAIL_USE_TLS  = True,
    MAIL_USERNAME = os.getenv('MAIL_USERNAME'),
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD'),
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
)

mail = Mail(app)

# Serializer for generating tokens
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


@app.template_filter('truncate_rating')
def truncate_rating(value):
    if value is None:
        return "–.–"
    return f"{int(value)}.xx"


@app.before_request
def make_session_permanent_and_check_timeout():
    session.permanent = True  # ensures expiry is used

    if 'email' in session:
        now = datetime.utcnow()
        last_active = session.get('last_active')

        # If user is inactive too long, log them out
        if last_active:
            last_active_dt = datetime.strptime(last_active, "%Y-%m-%d %H:%M:%S")
            if now - last_active_dt > app.permanent_session_lifetime:
                session.clear()
                flash("You were logged out due to inactivity.", "warning")
                return redirect(url_for('login'))

        # Update last activity time
        session['last_active'] = now.strftime("%Y-%m-%d %H:%M:%S")



app.secret_key = os.getenv('SECRET_KEY')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")



from collections import defaultdict

@app.route("/rankings")
def rankings():

    if 'email' not in session:
        flash("Please log in to view rankings.", "warning")
        return redirect(url_for('login'))
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    display_events = ["100M","200M","400M","800M","1 Mile","2 Mile","5K"]
    event_map = {
        "100M": ["100M"],
        "200M": ["200M"],
        "400M": ["400M"],
        "800M": ["800M"],
        "1 Mile": ["1500M", "1600M"],
        "2 Mile": ["3000M", "3200M"],
        "5K": ["5K"]
    }

    genders = ["Male","Female"]

    # We'll build a nested dict: rankings[event][gender] = [ {first_name,…,slug,rating}, … ]
    rankings = defaultdict(lambda: defaultdict(list))

    for event in display_events:
        for gender in genders:
            placeholders = ','.join(['%s'] * len(event_map[event]))
            query = f"""
                SELECT u.first_name, u.last_name, u.slug, AVG(r.rating) AS event_rating
                FROM user u
                JOIN results r ON u.email = r.email
                WHERE r.event_name IN ({placeholders})
                AND u.gender = %s
                AND u.profile_link IS NOT NULL
                GROUP BY u.first_name, u.last_name, u.slug
                ORDER BY event_rating DESC
                LIMIT 10
            """
            params = (*event_map[event], gender)
            cur.execute(query, params)


            rows = cur.fetchall()
            # filter out any missing slugs just in case
            rankings[event][gender] = [
                {
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "slug": row["slug"],
                    "rating": round(row["event_rating"], 2) if row["event_rating"] else None
                }
                for row in rows if row.get("slug")
            ]


    cur.close()

    current_year = datetime.today().year

    return render_template("rankings.html",
      display_events=display_events,
      genders=genders,
      rankings=rankings,
      current_year=current_year
    )


@app.route("/login", methods=['GET', 'POST'])
def login():
    if 'email' in session:
        return redirect(url_for('dashboard'))  # Redirect if already logged in

    if request.method == 'POST':
        email = request.form['email']
        # Validate email format early
        try:
            validated = validate_email(email)
            email = validated.email  # normalized email
        except EmailNotValidError as e:
            flash("Invalid email address. Please use a valid format like yourname@example.com", "danger")
            return render_template("register.html", error=str(e))

        password = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT email, password, email_confirmed FROM user WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[1], password):
            if not user[2]:
                flash("Please confirm your email first.", "warning")
                return redirect(url_for('unconfirmed'))
            session['email'] = email
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid email or password')
    
    return render_template("login.html")

def calculate_age(birthday: str) -> int:
    """
    birthday: 'YYYY-MM-DD'
    Returns a non-negative integer age. Future birthdays clamp to 0.
    """
    today = datetime.today().date()
    try:
        birthdate = datetime.strptime(birthday, '%Y-%m-%d').date()
    except ValueError:
        # Bad format -> treat as 0 (or raise; up to you)
        return 0

    # If the date is in the future, clamp to 0
    if birthdate > today:
        return 0

    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return max(0, age)


from requests.exceptions import RequestException  # put this at the top of the file

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # 1) Gather form inputs
        email        = request.form["email"]
        password     = generate_password_hash(request.form["password"], method="pbkdf2:sha256")
        first_name   = request.form["first_name"]
        last_name    = request.form["last_name"]
        gender       = request.form["gender"]
        birthday     = request.form["birthday"]
        age          = calculate_age(birthday)
        city         = request.form["city"]
        state        = request.form["state"]
        school       = request.form.get("school") or None
        club         = request.form.get("club_team") or None
        grad_year    = request.form.get("grad_year") or None
        profile_link = request.form["profile_link"]

        print(f"[REGISTER] Attempting to register {email}")

        cur = mysql.connection.cursor()

        # block duplicate profile claims
        cur.execute("SELECT 1 FROM user WHERE profile_link = %s", (profile_link,))
        if cur.fetchone():
            cur.close()
            return render_template("register.html", error="Profile link already in use.")

        try:
    # 2) Insert user into DB
            slug = generate_unique_slug(first_name, last_name, cur)
            cur.execute(
                """
                INSERT INTO user (
                  email, password, first_name, last_name,
                  gender, birthday, age,
                  city, state, school, club, grad_year,
                  profile_link, slug
                ) VALUES (
                  %s, %s, %s, %s,
                  %s, %s, %s,
                  %s, %s, %s, %s, %s,
                  %s, %s
                )
                """,
                (
                  email, password, first_name, last_name,
                  gender, birthday, age,
                  city, state, school, club, grad_year,
                  profile_link, slug
                )
            )
            mysql.connection.commit()
            print(f"[REGISTER] Created user row for {email}")
        
            # 3) Offload scraping via subprocess
            import subprocess
            print(f"[REGISTER] Offloading scrape for {email}")
            subprocess.Popen([
                "python3",
                "/home/athletiqadmin/athletiq-app/scraper_runner.py",
                email,
                first_name,
                last_name,
                profile_link
            ])
        
        except MySQLdb.IntegrityError:
            # Duplicate email
            cur.close()
            return render_template("register.html", error="Email already taken.")
        finally:
            try:
                cur.close()
            except Exception:
                pass


        # === Email confirmation phase (open a fresh cursor) ===
        cur = mysql.connection.cursor()

        # prevent spammy resend
        cur.execute("SELECT confirm_sent_at FROM user WHERE email = %s", (email,))
        row = cur.fetchone()
        if row and row[0] and datetime.utcnow() - row[0] < timedelta(minutes=10):
            flash("Confirmation email was sent recently. Please wait before resending.", "info")
            cur.close()
            return redirect(url_for('unconfirmed'))

        token = serializer.dumps(email, salt='email-confirm-salt')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        html_body = render_template('email/confirm.html', confirm_url=confirm_url, first_name=first_name)

        msg = Message(
            subject="Welcome to athletIQ – Please confirm your email",
            recipients=[email],
            html=html_body,
            sender="Ruhan from athletIQ <your@email.com>"
        )
        mail.send(msg)

        cur.execute("UPDATE user SET confirm_sent_at = NOW() WHERE email = %s", (email,))
        mysql.connection.commit()
        cur.close()

        session["email"] = email
        session.permanent = True
        return redirect(url_for('unconfirmed'))

    # GET => just render form
    return render_template("register.html")







def update_ages():
    with app.app_context():
        cur = mysql.connection.cursor()
        cur.execute("SELECT email, birthday FROM user")
        users = cur.fetchall()
        for user in users:
            email, birthday = user
            age = calculate_age(birthday)
            cur.execute("UPDATE user SET age = %s WHERE email = %s", (age, email))
        mysql.connection.commit()
        cur.close()


scheduler = BackgroundScheduler()
scheduler.add_job(func=rescrape_all_users, trigger="interval", hours=24)
scheduler.add_job(func=update_ages, trigger="interval", days=1)
scheduler.add_job(
    func=lambda: import_ghost_profiles(start_id=1, end_id=50000, batch=500),
    trigger="cron",
    hour=3  # run nightly at 3am
)
scheduler.start()

@app.route("/logout")
def logout():
    session.pop('email', None)
    return redirect(url_for('home'))



@app.route('/resend-confirmation', methods=["POST"])
def resend_confirmation():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    cur = mysql.connection.cursor()
    cur.execute("SELECT first_name, email_confirmed, confirm_sent_at FROM user WHERE email = %s", (email,))
    row = cur.fetchone()

    if not row:
        return redirect(url_for('login'))

    first_name, confirmed, last_sent = row

    if confirmed:
        return redirect(url_for('dashboard'))

    if last_sent and datetime.utcnow() - last_sent < timedelta(minutes=10):
        flash("Confirmation email was sent recently. Please wait before resending.", "info")
        return redirect(url_for('unconfirmed'))

    # Generate and send confirmation email
    token = serializer.dumps(email, salt='email-confirm-salt')
    confirm_url = url_for('confirm_email', token=token, _external=True)
    html_body = render_template('email/confirm.html', confirm_url=confirm_url, first_name=first_name)

    msg = Message(
        subject="Please confirm your email",
        recipients=[email],
        html=html_body
    )
    mail.send(msg)

    cur.execute("UPDATE user SET confirm_sent_at = NOW() WHERE email = %s", (email,))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('unconfirmed'))






@app.route("/dashboard")
def dashboard():
    if 'email' in session:
        email = session['email']
        cur = mysql.connection.cursor()

        # Get user bio info including school & club
        cur.execute("SELECT first_name, last_name, age, school, club, grad_year, city, state FROM user WHERE email = %s", (email,))
        user = cur.fetchone()


        # Get recent results (include meet name)
        # GET RECENT RESULTS (include meet name & place)
        cur.execute("""
            SELECT
            event_name,
            event_time,
            event_date,
            meet_name,
            finishing_place
            FROM results
            WHERE email = %s
            ORDER BY event_date DESC
        """, (email,))
        results = cur.fetchall()


        # Get results from the past year only for rating calculations
        cur.execute("""
            SELECT event_name, event_time
            FROM results
            WHERE email = %s AND event_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
        """, (email,))
        raw_results = cur.fetchall()

        # Unread messages
        cur.execute("SELECT COUNT(*) FROM messages WHERE receiver_email = %s AND is_read = 0", (email,))
        unread_count = cur.fetchone()[0]
        cur.close()

        # Supported events in short format
        all_events = ["100M", "200M", "400M", "800M", "1500M", "1600M", "3000M", "3200M", "5K"]

        # STEP 1: Clearly initialize dictionaries first!
        event_ratings = {}
        event_counts = {}

        # STEP 2: Populate dictionaries from results
        for event_name, event_time in raw_results:
            normalized_event = normalize_event_name(event_name)
            time_in_sec = convert_time_to_seconds(event_time)
            if time_in_sec is None:
                continue
            rating = get_event_rating(normalized_event, time_in_sec)
            if rating is None:
                continue
            if normalized_event not in event_ratings:
                event_ratings[normalized_event] = 0
                event_counts[normalized_event] = 0
            event_ratings[normalized_event] += rating
            event_counts[normalized_event] += 1

        # STEP 3: Calculate average ratings clearly and carefully
        for event in event_ratings:
            event_ratings[event] = round(event_ratings[event] / event_counts[event], 2)

        # STEP 4: Now merge the final displayed events clearly
        final_events = ["100M", "200M", "400M", "800M", "1 Mile", "2 Mile", "5K"]

        merged_event_ratings = {}

        # Merge "1 Mile" (1500M and 1600M)
        mile_events = ["1500M", "1600M"]
        mile_total = sum(event_ratings.get(ev, 0) * event_counts.get(ev, 0) for ev in mile_events)
        mile_count = sum(event_counts.get(ev, 0) for ev in mile_events)
        merged_event_ratings["1 Mile"] = round(mile_total / mile_count, 2) if mile_count else None

        # Merge "2 Mile" (3000M and 3200M)
        two_mile_events = ["3000M", "3200M"]
        two_mile_total = sum(event_ratings.get(ev, 0) * event_counts.get(ev, 0) for ev in two_mile_events)
        two_mile_count = sum(event_counts.get(ev, 0) for ev in two_mile_events)
        merged_event_ratings["2 Mile"] = round(two_mile_total / two_mile_count, 2) if two_mile_count else None

        # Fill direct matches explicitly
        for ev in ["100M", "200M", "400M", "800M", "5K"]:
            merged_event_ratings[ev] = event_ratings.get(ev)

        # STEP 5: Set the final ratings clearly for use in the template
        event_ratings = merged_event_ratings

        


        # Best event logic
        best_event = "100M"
        best_value = -1
        for event, value in event_ratings.items():
            if value is not None and value > best_value:
                best_event = event
                best_value = value

        if not any(v for v in event_ratings.values() if v is not None):
            best_event = "100M"

        avg_y = event_ratings.get("100M", 0) or 0

        # Get all unique years and events from results
        unique_years = sorted({r[2].year for r in results if r[2]}, reverse=True)
        unique_events = sorted({r[0] for r in results if r[0]})


        if user:
            first_name, last_name, age, school, club, grad_year, city, state = user
            return render_template(
                "dashboard.html",
                first_name=first_name,
                last_name=last_name,
                age=age,
                school=school,
                club=club,
                grad_year=grad_year,
                city=city,
                state=state,
                avg_y=avg_y,
                best_event=best_event,
                event_ratings=event_ratings,
                results=results,
                unread_count=unread_count,
                years=unique_years,
                filterable_events=unique_events
            )


    return redirect(url_for('login'))



@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=86400)
    except Exception:
        flash("The confirmation link is invalid or has expired.", "danger")
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT email_confirmed FROM user WHERE email = %s", (email,))
    already_confirmed = cur.fetchone()
    if already_confirmed and already_confirmed[0]:
        flash("Your email was already confirmed. You can log in.", "info")
        return redirect(url_for('login'))

    cur.execute(
        "UPDATE user SET email_confirmed = 1 WHERE email = %s",
        (email,)
    )
    mysql.connection.commit()
    cur.close()

    flash("Your email has been confirmed! You can now log in.", "success")
    return redirect(url_for('login'))



@app.route('/unconfirmed')
def unconfirmed():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('unconfirmed.html')


@app.route("/search")
def search():
    if 'email' not in session:
        flash("Please log in to search for runners.", "warning")
        return redirect(url_for('login'))

    query = request.args.get('query')
    cur = mysql.connection.cursor()
    
    names = query.split()
    
    if len(names) == 2:
        first_name, last_name = names
        cur.execute("SELECT first_name, last_name, slug FROM user WHERE first_name LIKE %s AND last_name LIKE %s", (f"%{first_name}%", f"%{last_name}%"))
    else:
        cur.execute("SELECT first_name, last_name, slug FROM user WHERE first_name LIKE %s OR last_name LIKE %s", (f"%{query}%", f"%{query}%"))
    
    results = cur.fetchall()
    cur.close()
    return render_template("search_results.html", results=results, query=query)


@app.route("/profile/<slug>")
def profile(slug):
    cur = mysql.connection.cursor()

    cur.execute("SELECT first_name, last_name, gender, age, email FROM user WHERE slug = %s", (slug,))
    user = cur.fetchone()

    if not user:
        cur.close()
        return redirect(url_for('home'))

    first_name, last_name, gender, age, email = user

    # ← updated: now select meet_name and finishing_place as well
    cur.execute("""
        SELECT
            event_name,
            event_time,
            event_date,
            meet_name,
            finishing_place
        FROM results
        WHERE email = %s
        ORDER BY event_date DESC
    """, (email,))
    results = cur.fetchall()

    # unchanged: fetch raw_results for ratings
    cur.execute("""
        SELECT event_name, event_time
        FROM results
        WHERE email = %s AND event_date >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
    """, (email,))
    raw_results = cur.fetchall()

    # Get unread message count (only for session user)
    unread_count = 0
    if 'email' in session:
        cur.execute(
            "SELECT COUNT(*) FROM messages WHERE receiver_email = %s AND is_read = 0",
            (session['email'],)
        )
        unread_count = cur.fetchone()[0]

    cur.close()

    # Supported events
    all_events = ["100M", "200M", "400M", "800M", "1 Mile", "2 Mile", "5K"]

    # Raw event ratings before merging
    raw_event_ratings = {}
    event_counts = {}

    for event_name, event_time in raw_results:
        try:
            time_in_sec = convert_time_to_seconds(event_time)
            if time_in_sec is None:
                continue
            y = get_event_rating(event_name, time_in_sec)
            if y is None:
                continue
            if event_name not in raw_event_ratings:
                raw_event_ratings[event_name] = 0
                event_counts[event_name] = 0
            raw_event_ratings[event_name] += y
            event_counts[event_name] += 1
        except ValueError:
            continue

    # Average each original event
    for event in raw_event_ratings:
        raw_event_ratings[event] = round(raw_event_ratings[event] / event_counts[event], 2)

    # Merge into standard display events
    event_ratings = {}
    combined_event_map = {
        "1 Mile": ["1500M", "1600M"],
        "2 Mile": ["3000M", "3200M"]
    }

    # Merge 1 Mile and 2 Mile
    for display_event, source_events in combined_event_map.items():
        total = 0
        count = 0
        for ev in source_events:
            if ev in raw_event_ratings:
                total += raw_event_ratings[ev]
                count += 1
        event_ratings[display_event] = round(total / count, 2) if count > 0 else None

    # Fill in direct matches (e.g., 800M)
    for ev in all_events:
        if ev not in event_ratings:
            event_ratings[ev] = raw_event_ratings.get(ev)

    # Determine best event AFTER merge
    best_event = "100M"
    best_value = -1
    for event, score in event_ratings.items():
        if score is not None and score > best_value:
            best_event = event
            best_value = score

    if not any(v for v in event_ratings.values() if v is not None):
        best_event = "100M"

    unique_years = sorted({r[2].year for r in results if r[2]}, reverse=True)
    unique_events = sorted({r[0] for r in results if r[0]})

    return render_template(
        "profile.html",
        first_name=first_name,
        last_name=last_name,
        gender=gender,
        age=age,
        event_ratings=event_ratings,
        best_event=best_event,
        results=results,
        email=email,             # still passed if needed in template logic
        session_email=session.get('email'),
        unread_count=unread_count,
        years=unique_years,          # ← added so filter dropdown shows years
        filterable_events=unique_events  # ← added so filter dropdown shows events
    )



    
@app.route("/add_result", methods=['POST'])
def add_result():
    if 'email' in session:
        email = session['email']
        event_name = request.form['event_name']
        event_time = request.form['event_time']
        event_date = request.form['event_date']
        y = get_event_rating(event_name, float(event_time))
        if y is None:
            flash("Invalid event name. Rating could not be calculated.")
            return redirect(url_for('dashboard'))
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO results (email, event_name, event_time, event_date) VALUES (%s, %s, %s, %s)", (email, event_name, event_time, event_date))
        mysql.connection.commit()
        cur.execute("SELECT event_name, event_time FROM results WHERE email = %s", (email,))
        user_results = cur.fetchall()

        y_values = []
        for event, time in user_results:
            time_in_sec = convert_time_to_seconds(time)
            if time_in_sec is None:
                flash("Invalid time format.", "danger")
                return redirect(url_for('dashboard'))

            y = get_event_rating(event_name, time_in_sec)

            if y is not None:
                y_values.append(y)

        average_y = sum(y_values) / len(y_values) if y_values else 0
        average_y = sum(y_values) / len(y_values) if y_values else 0
        cur.execute("UPDATE user SET rating = %s WHERE email = %s", (average_y, email))
        mysql.connection.commit()  # Ensure the commit is called after the update
        
        cur.close()
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/messages", methods=['GET'])
@app.route("/messages/<receiver_email>", methods=['GET'])
def messages(receiver_email=None):
    if 'email' not in session:
        return redirect(url_for('login'))

    sender_email = session['email']
    cur = mysql.connection.cursor()

    # --- Fetch latest message for each conversation partner ---
    cur.execute("""
        SELECT 
            CASE 
                WHEN sender_email = %s THEN receiver_email 
                ELSE sender_email 
            END AS partner,
            MAX(timestamp) AS last_time
        FROM messages
        WHERE sender_email = %s OR receiver_email = %s
        GROUP BY partner
        ORDER BY last_time DESC
    """, (sender_email, sender_email, sender_email))
    partner_rows = cur.fetchall()

    conversations = []
    for partner_email, last_time in partner_rows:
        cur.execute("SELECT first_name, last_name FROM user WHERE email = %s", (partner_email,))
        name_result = cur.fetchone()
        name = f"{name_result[0]} {name_result[1]}" if name_result else partner_email

        # Check if there are unread messages from this partner
        cur.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE sender_email = %s AND receiver_email = %s AND is_read = 0
        """, (partner_email, sender_email))
        unread = cur.fetchone()[0] > 0

        conversations.append({
            'email': partner_email,
            'name': name,
            'last_time': last_time,
            'has_unread': unread
        })

    # --- Fetch search results ---
    query = request.args.get('query')
    search_results = []
    if query:
        names = query.strip().split()
        if len(names) == 2:
            first_name, last_name = names
            cur.execute(
                "SELECT email, first_name, last_name FROM user WHERE first_name LIKE %s AND last_name LIKE %s",
                (f"%{first_name}%", f"%{last_name}%"))
        else:
            cur.execute(
                "SELECT email, first_name, last_name FROM user WHERE first_name LIKE %s OR last_name LIKE %s",
                (f"%{query}%", f"%{query}%"))
        
        search_results = [{'email': email, 'name': f"{fn} {ln}"} for email, fn, ln in cur.fetchall()]



    # --- Fetch messages for selected conversation ---
    messages_list = []
    receiver_name = None
    if receiver_email:
        # Fetch receiver's name
        cur.execute("SELECT first_name, last_name FROM user WHERE email = %s", (receiver_email,))
        receiver_info = cur.fetchone()
        receiver_name = f"{receiver_info[0]} {receiver_info[1]}" if receiver_info else receiver_email

        # Get messages between sender and receiver
        cur.execute("""
            SELECT sender_email, receiver_email, content, timestamp 
            FROM messages 
            WHERE (sender_email = %s AND receiver_email = %s) 
               OR (sender_email = %s AND receiver_email = %s)
            ORDER BY timestamp ASC
        """, (sender_email, receiver_email, receiver_email, sender_email))
        messages_list = cur.fetchall()

        # Mark all messages from receiver as read
        cur.execute("""
            UPDATE messages
            SET is_read = 1
            WHERE sender_email = %s AND receiver_email = %s AND is_read = 0
        """, (receiver_email, sender_email))
        mysql.connection.commit()

    cur.close()
    return render_template("messages.html",
                           conversations=conversations,
                           receiver_email=receiver_email,
                           receiver_name=receiver_name,
                           sender_email=sender_email,
                           messages=messages_list,
                           search_results=search_results,
                           query=query)


@app.route("/update_profile", methods=["POST"])
def update_profile():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    school = request.form.get("school")
    club = request.form.get("club_team")
    city = request.form.get("city")
    state = request.form.get("state")
    grad_year = request.form.get("grad_year")
    profile_link = request.form.get("profile_link")

    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE user
        SET school = %s, club = %s, city = %s, state = %s, grad_year = %s, profile_link = %s
        WHERE email = %s
    """, (school, club, city, state, grad_year, profile_link, email))
    mysql.connection.commit()
    cur.close()

    flash("Profile updated successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/delete_account", methods=["POST"])
def delete_account():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    cur = mysql.connection.cursor()

    try:
        # Delete results and messages first if you have foreign key constraints
        cur.execute("DELETE FROM results WHERE email = %s", (email,))
        cur.execute("DELETE FROM messages WHERE sender_email = %s OR receiver_email = %s", (email, email))
        cur.execute("DELETE FROM user WHERE email = %s", (email,))

        mysql.connection.commit()
        cur.close()

        session.clear()  # Log user out
        flash("Your account has been deleted.", "info")
        return redirect(url_for('home'))

    except Exception as e:
        cur.close()
        flash("Failed to delete account. Please try again.", "danger")
        print(f"[ERROR] Account deletion failed for {email}: {e}")
        return redirect(url_for('dashboard'))




@app.route("/send_message", methods=['POST'])
def send_message():
    if 'email' not in session:
        return redirect(url_for('login'))

    sender_email = session['email']
    receiver_email = request.form['receiver_email']

    content = request.form['content']

    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (sender_email, receiver_email, content) VALUES (%s, %s, %s)",
                (sender_email, receiver_email, content))
    mysql.connection.commit()
    cur.close()

    return redirect(url_for('messages', receiver_email=receiver_email))


atexit.register(lambda: scheduler.shutdown())
atexit.register(close_driver)


if __name__ == "__main__":
    app.run(port=8000, debug=False)

