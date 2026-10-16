from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Darshika12@",
    database="ride_sharing"
)
cursor = db.cursor(dictionary=True)

def extract_first_name(email):
    return email.split('@')[0].capitalize()

def get_booking_count(user_id):
    cursor.execute("SELECT COUNT(*) AS count FROM rides WHERE user_id=%s", (user_id,))
    return cursor.fetchone()['count']
@app.route('/introduction')
@app.route('/')
def introduction():
    return render_template('introduction.html')



@app.route('/login')
def home():
    return render_template('new_login.html')

@app.route('/payment')
def pay():
    return render_template('payment.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    role = data['role']
    name = data['name']
    email = data['email']
    password = generate_password_hash(data['password'])
    try:
        cursor.execute("INSERT INTO users (name, email, role, password) VALUES (%s,%s,%s,%s)",
                       (name, email, role.lower(), password))
        db.commit()
        session['user_id'] = cursor.lastrowid
        session['role'] = role.lower()
        session['email'] = email
        session['name'] = extract_first_name(email)
        redirect_url = '/student' if role.lower() == 'student' else '/driver'
        return jsonify({"status": "success", "redirect": redirect_url})
    except mysql.connector.IntegrityError:
        return jsonify({"status": "error", "message": "Email already exists."})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    role = data['role']
    email = data['email']
    password = data['password']
    cursor.execute("SELECT * FROM users WHERE email=%s AND role=%s", (email, role.lower()))
    user = cursor.fetchone()
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['role'] = role.lower()
        session['email'] = email
        session['name'] = extract_first_name(email)
        redirect_url = '/student' if role.lower() == 'student' else '/driver'
        return jsonify({"status": "success", "redirect": redirect_url})
    else:
        return jsonify({"status": "error", "message": "Invalid credentials."})

@app.route('/student')
def student_dashboard():
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('home'))
    user_id = session['user_id']
    cursor.execute("""
        SELECT * FROM rides 
        WHERE user_id=%s AND status IS NULL 
        ORDER BY created_at DESC
    """, (user_id,))
    pending_rides = cursor.fetchall()
    cursor.execute("""
        SELECT * FROM rides 
        WHERE user_id=%s AND status='accepted' 
        ORDER BY pickup_time ASC
    """, (user_id,))
    accepted_rides = cursor.fetchall()
    for b in pending_rides + accepted_rides:
        b['discount'] = 35 if get_booking_count(user_id) > 5 else 0
    return render_template(
        'student_page.html', 
        name=session['name'], 
        pending_rides=pending_rides, 
        upcoming_rides=accepted_rides
    )

@app.route('/book_ride', methods=['POST'])
def book_ride():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Not logged in."})
    try:
        data = request.get_json()
        pickup = data.get('pickup', '').strip()
        destination = data.get('destination', '').strip()
        pickup_time_str = data.get('pickup_time', '').strip()
        num_passengers = int(data.get('num_passengers', 1))
        user_id = session['user_id']
        if not pickup or not destination or not pickup_time_str:
            return jsonify({"status": "error", "message": "Missing ride details."})
        pickup_time = datetime.strptime(pickup_time_str, "%H:%M").replace(
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day
        )
        cursor.execute("SELECT COUNT(*) AS ride_count FROM rides WHERE user_id=%s", (user_id,))
        ride_count = cursor.fetchone()['ride_count']
        discount = 35 if (ride_count + 1) % 6 == 0 else 0
        cursor.execute("""
            INSERT INTO rides (user_id, pickup, destination, pickup_time, num_passengers, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """, (user_id, pickup, destination, pickup_time, num_passengers))
        db.commit()
        new_id = cursor.lastrowid
        cursor.execute("SELECT * FROM rides WHERE id=%s", (new_id,))
        new_ride = cursor.fetchone()
        for key, val in new_ride.items():
            if hasattr(val, "strftime"):
                new_ride[key] = val.strftime("%H:%M")
            elif not isinstance(val, (int, float, str, type(None))):
                new_ride[key] = str(val)
        new_ride['discount'] = discount
        return jsonify({"status": "success", "ride": new_ride, "discount": discount})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)})

@app.route('/driver')
def driver_dashboard():
    if 'role' not in session or session['role'] != 'driver':
        return redirect(url_for('home'))
    cursor.execute("""
        SELECT r.*, u.name AS student_name
        FROM rides r
        JOIN users u ON r.user_id = u.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at DESC
    """)
    rides = cursor.fetchall()
    return render_template('driver_page.html', name=session['name'], rides=rides)

@app.route('/accept_ride', methods=['POST'])
def accept_ride():
    if 'role' not in session or session['role'] != 'driver':
        return jsonify({"status": "error", "message": "Unauthorized"})
    data = request.get_json()
    ride_id = data.get('ride_id')
    cursor.execute("""
        UPDATE rides
        SET status='accepted'
        WHERE id=%s
    """, (ride_id,))
    db.commit()
    cursor.execute("""
        SELECT r.*, u.name AS student_name
        FROM rides r
        JOIN users u ON r.user_id = u.id
        WHERE r.id=%s
    """, (ride_id,))
    ride = cursor.fetchone()
    ride['pickup_time'] = ride['pickup_time'].strftime("%H:%M") if hasattr(ride['pickup_time'], "strftime") else str(ride['pickup_time'])
    return jsonify({"status": "success", "ride": ride})

@app.route('/new_rides')
def new_rides():
    cursor.execute("""
        SELECT r.*, u.name AS student_name
        FROM rides r
        JOIN users u ON r.user_id = u.id
        WHERE r.status = 'pending'
        ORDER BY r.created_at DESC
    """)
    rides = cursor.fetchall()
    for r in rides:
        if isinstance(r['pickup_time'], datetime):
            r['pickup_time'] = r['pickup_time'].strftime('%I:%M %p')
        else:
            r['pickup_time'] = str(r['pickup_time'])
    return jsonify({"rides": rides})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
