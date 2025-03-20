import sqlite3
from flask import Flask, render_template, request, url_for, redirect, abort

def get_db_connection():
    conn = sqlite3.connect('identifier.sqlite')
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)

@app.route('/')
def home():
    conn = get_db_connection()
    variable = conn.execute('SELECT * FROM films').fetchall()
    conn.close()
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

if __name__ == '__main__':
    app.run()
