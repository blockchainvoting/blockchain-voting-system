from flask import Flask, render_template, request, redirect, session
import sqlite3
from blockchain import Blockchain

app = Flask(__name__)
app.secret_key = 'secretkey'

# ---------------- DATABASE ----------------
DB_NAME = "voting.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voters (
        voter_id TEXT PRIMARY KEY,
        voter_name TEXT,
        has_voted INTEGER DEFAULT 0
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        party TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin (
        username TEXT PRIMARY KEY,
        password TEXT
    )
    """)

    cursor.execute("SELECT * FROM admin")
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (?, ?)",
            ("admin", "admin")
        )

    conn.commit()
    conn.close()


init_db()

# ---------------- BLOCKCHAIN ----------------
blockchain = Blockchain()

# ---------------- HOME ----------------
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates")
    candidates = cursor.fetchall()
    conn.close()
    return render_template('index.html', candidates=candidates)


# ---------------- VOTE ----------------
@app.route('/vote', methods=['POST'])
def vote():
    voter_id = request.form['voter_id']
    candidate = request.form['candidate']

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,))
    voter = cursor.fetchone()

    if not voter:
        return reload_home("❌ You are not a registered voter")

    if voter['has_voted'] == 1:
        return reload_home("❌ You have already voted")

    blockchain.add_vote(voter_id, candidate)
    blockchain.create_block(blockchain.last_block()['hash'])

    cursor.execute(
        "UPDATE voters SET has_voted=1 WHERE voter_id=?",
        (voter_id,)
    )
    conn.commit()
    conn.close()

    return reload_home("✅ Vote submitted successfully")


# ---------------- ADMIN LOGIN ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        )
        admin = cursor.fetchone()
        conn.close()

        if admin:
            session['admin'] = username
            return redirect('/dashboard')
        else:
            return "Invalid Username or Password"

    return render_template('admin.html')

# ---------------- CHANGE PASSWORD ----------------
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        username = request.form['username']
        old_password = request.form['old_password']
        new_password = request.form['new_password']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, old_password)
        )
        admin = cursor.fetchone()

        if not admin:
            conn.close()
            return "❌ Username or Old Password is incorrect"

        cursor.execute(
            "UPDATE admin SET password=? WHERE username=?",
            (new_password, username)
        )

        conn.commit()
        conn.close()

        return redirect('/admin')

    return render_template('change_password.html')
# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM candidates")
    candidates = cursor.fetchall()

    cursor.execute("SELECT * FROM voters")
    voters = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        candidates=candidates,
        voters=voters
    )


# ---------------- ADD CANDIDATE ----------------
@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':
        name = request.form['name']
        party = request.form['party']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO candidates (name, party) VALUES (?, ?)",
            (name, party)
        )
        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('add_candidate.html')


# ---------------- ADD VOTER ----------------
@app.route('/add_voter', methods=['GET', 'POST'])
def add_voter():
    if 'admin' not in session:
        return redirect('/admin')

    if request.method == 'POST':
        voter_id = request.form['voter_id']
        voter_name = request.form['voter_name']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO voters (voter_id, voter_name) VALUES (?, ?)",
            (voter_id, voter_name)
        )
        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('add_voter.html')


# ---------------- DELETE CANDIDATE ----------------
@app.route('/delete_candidate/<int:id>')
def delete_candidate(id):
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM candidates WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ---------------- DELETE VOTER ----------------
@app.route('/delete_voter/<voter_id>')
def delete_voter(voter_id):
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM voters WHERE voter_id=?", (voter_id,))
    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ---------------- RESULT ----------------
@app.route('/result')
def result():
    if 'admin' not in session:
        return redirect('/admin')

    results = {}
    for block in blockchain.chain:
        for vote in block['votes']:
            name = vote['candidate']
            results[name] = results.get(name, 0) + 1

    return render_template('result.html', results=results)


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- HELPER ----------------
def reload_home(message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM candidates")
    candidates = cursor.fetchall()
    conn.close()
    return render_template('index.html', candidates=candidates, message=message)


if __name__ == '__main__':

    app.run(host='0.0.0.0',port=10000)
