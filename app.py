import sqlite3

from flask import Flask, render_template, request, url_for, redirect, abort, session
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_connection():
    conn = sqlite3.connect('identifier.sqlite')
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)
app.secret_key = "vwkmRR6oDO6ug9E5h2rQOwUMFTc="

@app.context_processor
def inject_signed_in():
    signed_in = False
    if "user_id" in session:
        signed_in = True
    return dict(signedIn=signed_in)

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/favorites')
def fav():
    conn = get_db_connection()
    films = conn.execute('SELECT * FROM films').fetchall()
    verhuur_rows = conn.execute('SELECT * FROM verhuur').fetchall()
    conn.close()

    klanten = {}
    for verhuur in verhuur_rows:
        film_id = verhuur['film_id']
        klant_id = verhuur['klant_id']
        if film_id not in klanten:
            klanten[film_id] = []
        klanten[film_id].append(klant_id)

    for film_id in klanten:
        klanten[film_id].sort()

    return render_template('fav.html', films=films, klanten=klanten)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT password, id FROM users WHERE username = ?', [username]).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user_id"] = user[1]
            return redirect(url_for("panel"))
        else:
            abort(401)

    return render_template('signin.html')


@app.route('/panel')
def panel():
    if "user_id" not in session:
        abort(401)

    return render_template('panel.html')


@app.route('/panel/create', methods=['GET', 'POST'])
def create_user():
    if "user_id" not in session:
        abort(401)

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        print(username, password, hashed_password)

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', [username]).fetchone()
        if user:
            # TODO: Show error message
            return abort(500)

        conn.execute('INSERT INTO users (username, password) VALUES (?, ?);', (username, hashed_password))
        conn.commit()
        conn.close()
        return redirect(url_for('panel'))

    return render_template('create-user.html')

@app.route("/signout")
def signout():
    session.pop("user_id", None)  # Remove user session
    return redirect(url_for("signin"))


if __name__ == '__main__':
    app.run()
