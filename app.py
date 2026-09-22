from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

app = Flask(__name__)
app.secret_key = "movie-booking-demo-secret"
DB_PATH = Path(__file__).with_name("movie_booking.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        genre TEXT NOT NULL,
        duration INTEGER NOT NULL,
        language TEXT NOT NULL,
        certificate TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS shows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_id INTEGER NOT NULL,
        show_date TEXT NOT NULL,
        show_time TEXT NOT NULL,
        screen TEXT NOT NULL,
        total_seats INTEGER NOT NULL DEFAULT 60,
        price REAL NOT NULL,
        FOREIGN KEY(movie_id) REFERENCES movies(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_code TEXT UNIQUE NOT NULL,
        customer_name TEXT NOT NULL,
        email TEXT NOT NULL,
        phone TEXT NOT NULL,
        show_id INTEGER NOT NULL,
        seats TEXT NOT NULL,
        seat_count INTEGER NOT NULL,
        total_amount REAL NOT NULL,
        status TEXT NOT NULL DEFAULT 'Pending',
        request_time TEXT NOT NULL,
        confirmation_time TEXT,
        notification_sent INTEGER NOT NULL DEFAULT 0,
        sla_due TEXT NOT NULL,
        FOREIGN KEY(show_id) REFERENCES shows(id)
    );

    CREATE TABLE IF NOT EXISTS booking_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER NOT NULL,
        event TEXT NOT NULL,
        event_time TEXT NOT NULL,
        FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
    );
    """)
    movie_count = conn.execute("SELECT COUNT(*) FROM movies").fetchone()[0]
    if movie_count == 0:
        movies = [
            ("Vettaiyan", "Action", 163, "Tamil", "UA", "Action drama with a strong investigative storyline."),
            ("The Greatest of All Time", "Action", 183, "Tamil", "UA", "High-energy action entertainer."),
            ("Amaran", "Biographical", 169, "Tamil", "UA", "An inspiring story of courage and dedication."),
            ("Interstellar", "Sci-Fi", 169, "English", "U/A", "A journey through space, time and human survival."),
        ]
        conn.executemany(
            "INSERT INTO movies(title,genre,duration,language,certificate,description) VALUES(?,?,?,?,?,?)",
            movies
        )
        today = datetime.now().date()
        movie_ids = [r[0] for r in conn.execute("SELECT id FROM movies ORDER BY id").fetchall()]
        shows = []
        times = [("10:00", "Screen 1", 180), ("14:00", "Screen 2", 200),
                 ("18:00", "Screen 1", 220), ("21:00", "Screen 3", 240)]
        for day_offset in range(0, 5):
            d = (today + timedelta(days=day_offset)).isoformat()
            for i, movie_id in enumerate(movie_ids):
                t, screen, price = times[i]
                shows.append((movie_id, d, t, screen, 60, price))
        conn.executemany(
            "INSERT INTO shows(movie_id,show_date,show_time,screen,total_seats,price) VALUES(?,?,?,?,?,?)",
            shows
        )
    conn.commit()
    conn.close()

def available_seats(conn, show_id):
    show = conn.execute("SELECT total_seats FROM shows WHERE id=?", (show_id,)).fetchone()
    if not show:
        return []
    occupied = set()
    rows = conn.execute(
        "SELECT seats FROM bookings WHERE show_id=? AND status IN ('Pending','Confirmed','Processing')",
        (show_id,)
    ).fetchall()
    for row in rows:
        occupied.update(s.strip() for s in row["seats"].split(",") if s.strip())
    all_seats = [f"{r}{n}" for r in "ABCDEFGHIJ" for n in range(1, 7)]
    return [s for s in all_seats if s not in occupied][:show["total_seats"]]

@app.route("/")
def index():
    conn = get_db()
    movies = conn.execute("SELECT * FROM movies ORDER BY id").fetchall()
    shows = conn.execute("""
        SELECT s.*, m.title, m.genre, m.language
        FROM shows s JOIN movies m ON m.id=s.movie_id
        WHERE s.show_date >= date('now','localtime')
        ORDER BY s.show_date, s.show_time
    """).fetchall()
    conn.close()
    return render_template("index.html", movies=movies, shows=shows)

@app.route("/book/<int:show_id>", methods=["GET", "POST"])
def book(show_id):
    conn = get_db()
    show = conn.execute("""
        SELECT s.*, m.title, m.genre, m.language, m.certificate
        FROM shows s JOIN movies m ON m.id=s.movie_id WHERE s.id=?
    """, (show_id,)).fetchone()
    if not show:
        conn.close()
        return "Show not found", 404
    seats = available_seats(conn, show_id)
    if request.method == "POST":
        name = request.form.get("customer_name","").strip()
        email = request.form.get("email","").strip()
        phone = request.form.get("phone","").strip()
        selected = [s for s in request.form.get("seats","").split(",") if s]
        if not name or not email or not phone or not selected:
            flash("Please provide customer details and select at least one seat.", "error")
        elif not all(s in seats for s in selected):
            flash("One or more selected seats are no longer available.", "error")
        else:
            code = f"MTB{datetime.now().strftime('%y%m%d%H%M%S')}{show_id}"
            now = datetime.now()
            sla = now + timedelta(minutes=30)
            total = len(selected) * show["price"]
            cur = conn.execute("""
                INSERT INTO bookings
                (booking_code,customer_name,email,phone,show_id,seats,seat_count,total_amount,status,request_time,sla_due)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (code,name,email,phone,show_id,",".join(selected),len(selected),total,
                  "Pending",now.isoformat(timespec="seconds"),sla.isoformat(timespec="seconds")))
            booking_id = cur.lastrowid
            conn.execute("INSERT INTO booking_events(booking_id,event,event_time) VALUES(?,?,?)",
                         (booking_id,"Booking request submitted",now.isoformat(timespec="seconds")))
            conn.commit()
            conn.close()
            return redirect(url_for("review", booking_id=booking_id))
    conn.close()
    return render_template("book.html", show=show, seats=seats)

@app.route("/review/<int:booking_id>")
def review(booking_id):
    conn = get_db()
    booking = conn.execute("""
        SELECT b.*, s.show_date, s.show_time, s.screen, m.title
        FROM bookings b JOIN shows s ON s.id=b.show_id JOIN movies m ON m.id=s.movie_id
        WHERE b.id=?
    """, (booking_id,)).fetchone()
    events = conn.execute("SELECT * FROM booking_events WHERE booking_id=? ORDER BY id", (booking_id,)).fetchall()
    conn.close()
    if not booking:
        return "Booking not found", 404
    return render_template("review.html", booking=booking, events=events)

@app.route("/confirm/<int:booking_id>", methods=["POST"])
def confirm(booking_id):
    conn = get_db()
    booking = conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
    if not booking:
        conn.close()
        return "Booking not found", 404
    now = datetime.now().isoformat(timespec="seconds")
    conn.execute("UPDATE bookings SET status='Confirmed', confirmation_time=?, notification_sent=1 WHERE id=?",
                 (now, booking_id))
    conn.execute("INSERT INTO booking_events(booking_id,event,event_time) VALUES(?,?,?)",
                 (booking_id,"Booking confirmed and customer notification generated",now))
    conn.commit()
    conn.close()
    flash("Booking confirmed successfully. A confirmation notification has been generated.", "success")
    return redirect(url_for("dashboard"))

@app.route("/dashboard")
def dashboard():
    conn = get_db()
    bookings = conn.execute("""
        SELECT b.*, s.show_date, s.show_time, s.screen, m.title
        FROM bookings b JOIN shows s ON s.id=b.show_id JOIN movies m ON m.id=s.movie_id
        ORDER BY b.id DESC
    """).fetchall()
    pending = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Pending'").fetchone()[0]
    confirmed = conn.execute("SELECT COUNT(*) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    revenue = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM bookings WHERE status='Confirmed'").fetchone()[0]
    conn.close()
    return render_template("dashboard.html", bookings=bookings, pending=pending,
                           confirmed=confirmed, revenue=revenue)

@app.route("/admin/movies", methods=["GET", "POST"])
def movies():
    conn = get_db()
    if request.method == "POST":
        title = request.form["title"].strip()
        genre = request.form["genre"].strip()
        duration = int(request.form["duration"])
        language = request.form["language"].strip()
        certificate = request.form["certificate"].strip()
        description = request.form.get("description","").strip()
        conn.execute("INSERT INTO movies(title,genre,duration,language,certificate,description) VALUES(?,?,?,?,?,?)",
                     (title,genre,duration,language,certificate,description))
        conn.commit()
        flash("Movie added successfully.", "success")
    rows = conn.execute("SELECT * FROM movies ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("movies.html", movies=rows)

@app.route("/api/availability/<int:show_id>")
def availability_api(show_id):
    conn = get_db()
    seats = available_seats(conn, show_id)
    conn.close()
    return jsonify({"show_id": show_id, "available": seats, "count": len(seats)})

@app.route("/api/booking/<code>")
def booking_api(code):
    conn = get_db()
    row = conn.execute("""
        SELECT b.booking_code,b.customer_name,b.email,b.phone,b.seats,b.seat_count,
               b.total_amount,b.status,b.request_time,b.confirmation_time,
               s.show_date,s.show_time,s.screen,m.title
        FROM bookings b JOIN shows s ON s.id=b.show_id JOIN movies m ON m.id=s.movie_id
        WHERE b.booking_code=?
    """, (code,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Booking not found"}), 404
    return jsonify(dict(row))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
