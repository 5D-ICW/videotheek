import sqlite3

from flask import Flask, render_template, request, url_for, redirect, abort, session
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_connection():
    conn = sqlite3.connect('identifier.sqlite')
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)
# noinspection SpellCheckingInspection
app.secret_key = "vwkmRR6oDO6ug9E5h2rQOwUMFTc="

@app.context_processor
def inject_signed_in():
    signed_in = False
    if "user_id" in session:
        signed_in = True

    return dict(signedIn=signed_in, rol=session.get("rol", "CLIENT"))

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/movies', methods=['GET', 'POST'])
def movies():
    if request.method == 'POST':
        if not "user_id" in session:
            abort(403)

        action = request.form['action']
        film_id = request.form['film_id']

        conn = get_db_connection()
        if action == "add":
            conn.execute('INSERT INTO favorieten (klant_id, film_id) VALUES (?, ?)', (session["user_id"], film_id))

        if action == "remove":
            conn.execute('DELETE FROM favorieten WHERE klant_id = ? AND film_id = ?', (session["user_id"], film_id))

        conn.commit()
        conn.close()

        return redirect(url_for('movies'))

    if not "user_id" in session:
        return redirect(url_for("sign_in"))

    alleen_favorieten = request.args.get('alleen_favorieten', False)

    conn = get_db_connection()
    films = []
    if alleen_favorieten:
        films = conn.execute('SELECT * FROM films WHERE film_id IN (SELECT film_id FROM favorieten WHERE klant_id = ?)', (session["user_id"],)).fetchall()

    else:
        films = conn.execute('SELECT * FROM films').fetchall()

    favorieten = conn.execute('SELECT * FROM favorieten WHERE klant_id = ?', (session["user_id"],)).fetchall()
    conn.close()


    return render_template('movies.html', films=films, favorieten=favorieten, alleen_favorieten=alleen_favorieten)

@app.route('/delete-film', methods=['POST'])
def delete_film():
    if not "user_id" in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        abort(403)

    film_id = request.form['id']

    conn = get_db_connection()
    conn.execute('DELETE FROM films WHERE film_id = ?', (film_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('movies'))


@app.route('/signin', methods=['GET', 'POST'])
def sign_in():
    if "user_id" in session:
        if session["rol"] == "ADMIN":
            return redirect(url_for("panel"))
        return redirect(url_for("movies"))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT password, klant_id FROM klanten WHERE email = ?', [email]).fetchone()
        if not user:
            return abort(401)
        rol = conn.execute('SELECT rol FROM rol WHERE klant_id = ?', [user[1]]).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user_id"] = user[1]
            if rol:
                session["rol"] = rol[0]
            else:
                session['rol'] = "CLIENT"
            return redirect(url_for("panel"))
        else:
            abort(401)

    return render_template('signin.html')


@app.route('/panel')
def panel():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    return render_template('panel.html')


@app.route('/panel/create', methods=['GET', 'POST'])
def create_user():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    if request.method == 'POST':
        name = request.form["name"]
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM klanten WHERE email = ?', [email]).fetchone()
        if user:
            # TODO: Show error message
            return abort(500)

        conn.execute('INSERT INTO klanten (naam, email, password) VALUES (?, ?, ?);', (name, email, hashed_password))
        conn.commit()
        conn.close()
        return redirect(url_for('panel'))

    return render_template('create-user.html')

@app.route('/panel/delete', methods=['GET', 'POST'])
def delete_user():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM klanten WHERE email = ?', [email]).fetchone()
        if not user:
            # TODO: Show error message
            return abort(500)

        conn.execute('DELETE FROM klanten WHERE email = ?;', [email])
        conn.commit()
        conn.close()
        return redirect(url_for('panel'))

    return render_template('delete-user.html')

@app.route('/panel/add', methods=['GET', 'POST'])
def add_movie():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
         return redirect(url_for("sign_in"))

    if request.method == 'POST':
        title = request.form['title']
        genre = request.form['genre']
        year = request.form['year']
        director = request.form['director']

        conn = get_db_connection()
        movie = conn.execute('SELECT * FROM films WHERE titel = ?', [title]).fetchone()
        if movie:
            # TODO: Show error message
            return abort(500)

        conn.execute('INSERT INTO films (titel, genre, releasejaar, regisseur) VALUES (?, ?, ?, ?)', (title, genre, year, director))
        conn.commit()
        conn.close()
        return redirect(url_for('panel'))

    return render_template('add-movie.html')

@app.route("/signout")
def sign_out():
    session.pop("user_id", None)  # Remove user session
    return redirect(url_for("sign_in"))

@app.route('/search')
def search():
    conn = get_db_connection()
    films = conn.execute('SELECT * FROM films').fetchall()
    conn.close()
    return render_template('search.html', posts=films)

if __name__ == '__main__':
    app.run()
