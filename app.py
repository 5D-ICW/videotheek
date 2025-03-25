import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    url_for,
    redirect,
    abort,
    session,
)
from werkzeug.security import generate_password_hash, check_password_hash


def get_db_connection():
    conn = sqlite3.connect("identifier.sqlite")
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


@app.route("/")
def home():
    return render_template("home.jinja")


@app.route("/movies", methods=["GET", "POST"])
def movies():
    if request.method == "POST":
        if not "user_id" in session:
            abort(403)

        action = request.form["action"]
        film_id = request.form["film_id"]

        conn = get_db_connection()
        if action == "add":
            conn.execute(
                "INSERT INTO favorieten (klant_id, film_id) VALUES (?, ?)",
                (session["user_id"], film_id),
            )

        if action == "remove":
            conn.execute(
                "DELETE FROM favorieten WHERE klant_id = ? AND film_id = ?",
                (session["user_id"], film_id),
            )

        conn.commit()
        conn.close()

        return redirect(url_for("movies"))

    if not "user_id" in session:
        return redirect(url_for("sign_in"))

    alleen_favorieten = request.args.get("alleen_favorieten", "off")
    q = request.args.get("q", "")
    sort = request.args.get("sort", "film_id")

    query = "SELECT * FROM films"
    params = []

    if alleen_favorieten == "on":
        query += " WHERE film_id IN (SELECT film_id FROM favorieten WHERE klant_id = ?)"
        params.append(session["user_id"])

    if q:
        if "WHERE" in query:
            query += " AND"
        else:
            query += " WHERE"
        query += " LOWER(titel) LIKE LOWER(?)"
        params.append(f"%{q}%")

    query += f" ORDER BY {sort}"

    conn = get_db_connection()
    films = conn.execute(query, params).fetchall()

    favorieten = conn.execute(
        "SELECT * FROM favorieten WHERE klant_id = ?", (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template(
        "movies.jinja",
        films=films,
        favorieten=favorieten,
        q=q,
        sort=sort,
        alleen_favorieten=alleen_favorieten,
    )


@app.route("/delete-film", methods=["POST"])
def delete_film():
    if not "user_id" in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        abort(403)

    film_id = request.form["id"]

    conn = get_db_connection()
    conn.execute("DELETE FROM films WHERE film_id = ?", (film_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("movies"))


@app.route("/signin", methods=["GET", "POST"])
def sign_in():
    if "user_id" in session:
        if session["rol"] == "ADMIN":
            return redirect(url_for("panel"))
        return redirect(url_for("movies"))

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute(
            "SELECT password, klant_id FROM klanten WHERE email = ?", [email]
        ).fetchone()
        if not user:
            return abort(401)
        rol = conn.execute(
            "SELECT rol FROM rol WHERE klant_id = ?", [user[1]]
        ).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            session["user_id"] = user[1]
            if rol:
                session["rol"] = rol[0]
            else:
                session["rol"] = "CLIENT"
            return redirect(url_for("panel"))
        else:
            abort(401)

    return render_template("signin.jinja")


@app.route("/signup", methods=["GET", "POST"])
def sign_up():
    if "user_id" in session:
        if session["rol"] == "ADMIN":
            return redirect(url_for("panel"))
        return redirect(url_for("movies"))

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM klanten WHERE email = ?", [email]).fetchone()
        if user:
            # TODO: Show error message
            return abort(500)

        conn.execute(
            "INSERT INTO klanten (naam, email, password) VALUES (?, ?, ?);",
            (name, email, hashed_password),
        )
        conn.commit()
        user = conn.execute(
            "SELECT klant_id FROM klanten WHERE email = ?", [email]
        ).fetchone()
        conn.close()

        session["user_id"] = user[0]
        session["rol"] = "CLIENT"
        return redirect(url_for("panel"))

    return render_template("signup.jinja")


@app.route("/panel")
def panel():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    return render_template("panel.jinja")


@app.route("/panel/create", methods=["GET", "POST"])
def create_user():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        admin = request.form.get("admin", "off")

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM klanten WHERE email = ?", [email]).fetchone()
        if user:
            # TODO: Show error message
            return abort(500)

        conn.execute(
            "INSERT INTO klanten (naam, email, password) VALUES (?, ?, ?);",
            (name, email, hashed_password),
        )
        if admin == "on":
            conn.execute(
                "INSERT INTO rol (klant_id, rol) VALUES ((SELECT klant_id FROM klanten WHERE email = ?), 'ADMIN');",
                [email],
            )

        conn.commit()
        conn.close()
        return redirect(url_for("panel"))

    return render_template("create_user.jinja")


@app.route("/panel/list")
def list_users():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    conn = get_db_connection()
    users = conn.execute("SELECT * FROM klanten").fetchall()
    conn.close()

    return render_template("list-users.jinja", users=users)


@app.route("/panel/delete", methods=["GET", "POST"])
def delete_user():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    if request.method == "POST":
        email = request.form["email"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM klanten WHERE email = ?", [email]).fetchone()
        if not user:
            # TODO: Show error message
            return abort(500)

        conn.execute("DELETE FROM klanten WHERE email = ?;", [email])
        conn.commit()
        conn.close()
        return redirect(url_for("panel"))

    return render_template("delete_user.jinja")


@app.route("/panel/add", methods=["GET", "POST"])
def add_movie():
    if "user_id" not in session:
        return redirect(url_for("sign_in"))

    if session["rol"] != "ADMIN":
        return redirect(url_for("sign_in"))

    if request.method == "POST":
        title = request.form["title"]
        genre = request.form["genre"]
        year = request.form["year"]
        director = request.form["director"]
        description = request.form["description"]

        conn = get_db_connection()
        movie = conn.execute("SELECT * FROM films WHERE titel = ?", [title]).fetchone()
        if movie:
            # TODO: Show error message
            return abort(500)

        conn.execute(
            "INSERT INTO films (titel, genre, releasejaar, regisseur, beschrijving) VALUES (?, ?, ?, ?, ?)",
            (title, genre, year, director, description),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("panel"))

    return render_template("add-movie.jinja")


@app.route("/signout")
def sign_out():
    session.pop("user_id", None)  # Remove user session
    return redirect(url_for("sign_in"))


@app.route("/<int:film_id>/review", methods=("GET", "POST"))
def review(film_id):
    if request.method == "POST":
        rating = request.form["rating"]
        recensie = request.form["recensie"]

        conn = get_db_connection()
        film = conn.execute(
            "SELECT * FROM reviews WHERE klant_id = ? AND film_id = ?",
            (session["user_id"], film_id),
        ).fetchone()

        if film:
            film = conn.execute(
                "SELECT * FROM films WHERE films.film_id = ?", (film_id,)
            ).fetchone()
            conn.close()

            return render_template(
                "reviews.jinja",
                film=film,
                error="Error: You already wrote a review for this movie",
            )

        conn.execute(
            "INSERT INTO reviews (klant_id, film_id, rating, recensie) VALUES (?, ?, ?, ?)",
            (session["user_id"], film_id, rating, recensie),
        )
        conn.commit()
        conn.close()
        return redirect(url_for("get_info", film_id=film_id))

    conn = get_db_connection()
    film = conn.execute(
        "SELECT * FROM films WHERE films.film_id = ?", (film_id,)
    ).fetchone()
    conn.close()

    return render_template("reviews.jinja", film=film)


@app.route("/<int:film_id>")
def get_info(film_id):
    conn = get_db_connection()
    reviews = conn.execute(
        "SELECT * FROM reviews WHERE film_id = ?", (film_id,)
    ).fetchall()
    film = conn.execute(
        "SELECT * FROM films WHERE films.film_id = ?", (film_id,)
    ).fetchone()
    conn.close()
    return render_template("film_info.jinja", film=film, reviews=reviews)


if __name__ == "__main__":
    app.run()
