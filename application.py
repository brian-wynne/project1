import os
import requests
import json
from flask import Flask, session, render_template, request, redirect, abort
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
app.config["SESSION_PERMANENT"] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SECRET_KEY'] = 'super secret key'
app.secret_key = 'another super secret key!'
Session(app)

# Set up database
engine = create_engine('postgresql://books:book@localhost:5432/project1')
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    user = session.get('user')
    if user is None:
        return render_template('index.html')
    else:
        return render_template('index.html', user=user)


@app.route("/login", methods=["GET", "POST"])
def login():
    session['user'] = None  # Force logout, the buttons should not be available if logged in
    if request.method == 'POST':
        name = request.form.get('inputUsername')
        pswd = request.form.get('inputPassword')

        results = db.execute(f"SELECT username, passwrd FROM users WHERE LOWER(username)='{name.lower()}' AND passwrd='{pswd}'")
        row = results.fetchone()

        if row is not None:     # Username found, password was correct
            session['user'] = name.upper()
            return redirect('/')
        else:
            return render_template('login.html', invalid_login=True)

    return render_template('login.html')


# TODO: Add sha256 hash
@app.route("/signup", methods=["GET", "POST"])
def signup():
    session['user'] = None  # Force logout, the buttons should not be available if logged in
    if request.method == "POST":
        name = request.form.get("inputUsername")
        pswd = request.form.get("inputPassword")
        pswd_c = request.form.get("inputConfirmPassword")

        if pswd == pswd_c and len(pswd) >= 8:
            results = db.execute(f"SELECT username FROM users WHERE LOWER(username)='{name.lower()}'")
            row = results.fetchone()

            if row is not None:     # If username already exists
                return render_template('signup.html', error_message="Username is invalid or already exists")
            else:       # If the username does not exist we want to create the new user
                db.execute(f"INSERT INTO users (username, passwrd) VALUES ('{name}', '{pswd}')")
                db.commit()
                session["user"] = name.upper()
                return redirect('/')
        elif pswd != pswd_c:
            return render_template('signup.html', error_message="Passwords do not match")
        elif len(pswd) < 8:
            return render_template('signup.html', error_message="Password must be longer than 8 characters")

    return render_template('signup.html')


@app.route("/search", methods=["POST"])
def search():
    user = session.get('user')
    if user is None or not user:
        return render_template('index.html')

    if request.method == "POST":
        srch = request.form.get('inputSearch')
        srch = remove_illegal_characters(srch)

        if len(srch) == 4 and srch.isdigit() and 1000 <= int(srch) <= 9999:
            results = db.execute(f"SELECT isbn, title, author, year FROM books WHERE year='{srch}' ORDER BY title, year")
        else:
            results = db.execute(f"""SELECT isbn, title, author, year FROM books WHERE 
                LOWER(isbn) LIKE '{srch.lower()}%' OR LOWER(title) LIKE '{srch.lower()}%' OR LOWER(author) LIKE '{srch.lower()}%' ORDER BY title, year""")

        rows = results.fetchall()

        if len(rows) > 1:   # Many results
            return render_template('search.html', user=user, data=rows)
        elif len(rows) == 1:   # One result, redirect to page
            isbn = str(rows[0][0])
            return redirect('/book/' + isbn)
        else:    # No results
            return render_template('search.html', user=user, data=None)

    return render_template('index.html', user=user)


@app.route('/book/<isbn>', methods=['GET', 'POST'])
def book(isbn):
    if request.method == 'GET':
        user = session.get('user')
        if user is None or not user:
            return render_template('index.html')

        req = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "lug01wUST50dXrnx9lAew", "isbns": str(isbn)})
        results = db.execute(f"SELECT title, author, year FROM books WHERE isbn='{isbn}' LIMIT 1")
        rows = results.fetchall()

        data = {
            'isbn': isbn,
            'title': rows[0][0],
            'author': rows[0][1],
            'year': rows[0][2]
        }

        results = db.execute(f"SELECT u.username, r.rating, r.text FROM reviews as r, users as u WHERE r.isbn='{isbn}' AND u.id=r.userid")
        rows = results.fetchall()
        return render_template('book.html', user=user, book=data, api=json.loads(req.text), reviews=rows)
    else:
        return submit_review(isbn)


def submit_review(isbn):
    user = session.get('user')
    if user is None or not user:
        abort(404)
        return

    review = request.form.get("inputReview")
    rating = request.form.get("inputRating")

    if not review or len(review) < 50:
        return redirect('/book/' + isbn)

    if int(rating) > 5:
        rating = 5
    elif int(rating) < 0:
        rating = 0

    db.execute(f"INSERT INTO reviews(userid, text, rating, isbn) VALUES((SELECT id FROM users WHERE username='{user}'), '{review}', '{rating}', '{isbn}')")
    db.commit()

    return redirect('/book/' + isbn)


@app.route('/api/<isbn>', methods=['GET'])
def api(isbn):
    results = db.execute(f"SELECT title, author, year FROM books WHERE isbn='{isbn}'")
    rows = results.fetchall()

    if not rows:
        abort(404)

    data = {
        'isbn': isbn,
        'title': rows[0][0],
        'author': rows[0][1],
        'year': rows[0][2]
    }

    return json.dumps(data)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


def remove_illegal_characters(string):
    illegals = [';', '(', ')', '+', '=', '-', '{', '}']
    for illegal in illegals:
        string = string.replace(illegal, '')

    return string


@app.route("/logout")
def logout():
    session['user'] = None
    return redirect('/')


if __name__ == '__main__':
    app.debug = True
    app.run()
