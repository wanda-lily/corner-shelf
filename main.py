from bs4 import BeautifulSoup
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from flask_wtf import CSRFProtect
from forms import *
import html
from models.book import Book, Tag, Author
from models.db import db
from models.user import User
from models.shelf import Shelf, ShelfEntry, ShelfParticipant, ShelfRole, ShelfType
import os
import re
import requests
from werkzeug.security import generate_password_hash, check_password_hash


load_dotenv()  # reads .env file into environment variables


def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me")

    # remember me cookie settings
    app.config["REMEMBER_COOKIE_SECURE"] = True      # HTTPS only
    app.config["REMEMBER_COOKIE_HTTPONLY"] = True    # no JS access
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=7)
    app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] = True

    db.init_app(app)

    with app.app_context():
        import models  # registers all models with SQLAlchemy metadata
        db.create_all()

    return app


app = create_app()
Bootstrap5(app)
csrf = CSRFProtect(app)

# Configure Flask-Login's Login Manager
login_manager = LoginManager()
login_manager.init_app(app)


# Create a user_loader callback to reload the user object from the user ID stored in the session
@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template("index.html")


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# Making and Editing Shelves
# ------------------------------------------------------------------------------------------------------------------------------------------------------

@app.route('/create-shelf', methods=["GET", "POST"])
@login_required
def create_shelf():
    form = ShelfForm()
    message = ""

    if form.validate_on_submit():
        # Form was submitted and validated
        shelf_name = form.name.data
        shelf_type = form.shelf_type.data
        shelf_owner = current_user.id

        print(shelf_name, shelf_type)
        # save to DB
        new_shelf = Shelf(
            name=shelf_name,
            shelf_type=shelf_type,
            owner_id=shelf_owner)

        db.session.add(new_shelf)
        db.session.flush()  # get new_shelf.id

        # add creator as a shelf participant
        owner_participant = ShelfParticipant(
            shelf_id=new_shelf.id,
            user_id=current_user.id,
            role=ShelfRole.owner
        )

        db.session.add(owner_participant)
        db.session.commit()

        message = "Shelf created successfully!"

        # Reset form if you want
        form.name.data = ""
        form.shelf_type.data = ShelfType.personal.value

        return redirect(url_for("view_my_shelves"))
    else:
        # GET request or form failed validation
        print(form.errors)
        return render_template("shelves/create-shelf.html", form=form, message=message)


@app.route('/my-shelves')
@login_required
def view_my_shelves():
    shelves = db.session.scalars(
        db.select(Shelf).where(
            (Shelf.owner_id == current_user.id) & (
                Shelf.shelf_type == "personal")
        )
    ).all()
    return render_template("shelves/my-shelves.html", shelves=shelves)


@app.route('/shared-shelves')
@login_required
def view_shared_shelves():
    shelves = db.session.scalars(
        db.select(Shelf).where(Shelf.shelf_type == "shared")
        .join(ShelfParticipant)
        .where(ShelfParticipant.user_id == current_user.id)
    ).all()
    return render_template("shelves/shared-shelves.html", shelves=shelves)


@app.route('/edit-shelf/<int:shelf_id>', methods=["GET", "POST"])
def edit_shelf(shelf_id):
    shelf = db.get_or_404(Shelf, shelf_id)
    edit_form = ShelfForm(shelf_name=shelf.name,
                          shelf_type=shelf.type)

    if edit_form.validate_on_submit():
        shelf.name = edit_form.name.data
        shelf.shelf_type = edit_form.shelf_type.data
        shelf.owner_id = current_user.id
        db.session.commit()
        return redirect(url_for("open_shelf", shelf_id=shelf_id))
    return render_template("shelves/create-shelf.html", form=edit_form, is_edit=True)


@app.route('/open-shelf/<int:shelf_id>', methods=["GET", "POST"])
def open_shelf(shelf_id):
    shelf = db.get_or_404(Shelf, shelf_id)
    return render_template("shelves/shelf-content.html", shelf=shelf)

# ------------------------------------------------------------------------------------------------------------------------------------------------------
# Adding Books
# ------------------------------------------------------------------------------------------------------------------------------------------------------


def clean_description(text):
    if not text:
        return ""
    text = html.unescape(text)
    soup = BeautifulSoup(text, "html.parser")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    cleaned = soup.get_text()
    return re.sub(r"\n+", "\n", cleaned).strip()


def get_or_create_author(name):
    name = name.strip()
    author = Author.query.filter_by(name=name).first()
    if not author:
        author = Author(name=name)
        db.session.add(author)
    return author


def get_book(query):
    books_api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={books_api_key}"

    response = requests.get(url)
    if response.status_code != 200:
        return []
    data = response.json()
    books = []
    for item in data.get("items", []):
        volume = item.get("volumeInfo", {})
        books.append({
            "title": volume.get("title"),
            "authors": [get_or_create_author(name) for name in volume.get("authors", [])],
            "description": clean_description(volume.get("description")),
            "thumbnail": volume.get("imageLinks", {}).get("thumbnail"),
            "google_books_id": item.get("id")
        })

    return books


def get_book_by_id(book_id):
    books_api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
    url = f"https://www.googleapis.com/books/v1/volumes/{book_id}?key={books_api_key}"

    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    volume = data.get("volumeInfo", {})

    return {
        "title": volume.get("title"),
        "authors": [get_or_create_author(name) for name in volume.get("authors", [])],
        "description": clean_description(volume.get("description")),
        "thumbnail": volume.get("imageLinks", {}).get("thumbnail"),
        "google_books_id": data.get("id")
    }


@app.route('/add-book-from-api/<int:shelf_id>', methods=["GET", "POST"])
def add_book_from_api(shelf_id):
    search_form = SearchBookForm()
    books = []

    if search_form.validate_on_submit():
        query = search_form.search.data
        books = get_book(query)
    shelf = db.get_or_404(Shelf, shelf_id)
    return render_template(
        "books/search-book-api.html",
        form=search_form,
        books=books,
        shelf=shelf,
    )


@app.route('/prepare-book/<int:shelf_id>/<book_id>')
def prepare_book(shelf_id, book_id):

    shelf = db.get_or_404(Shelf, shelf_id)

    book_data = get_book_by_id(book_id)
    if not book_data:
        return redirect(url_for("add_book_from_api", shelf_id=shelf_id))

    book_form = BookForm(
        title=book_data["title"],
        author=",".join(a.name for a in book_data.get("authors", [])),
        description=book_data.get("description"),
        cover_url=book_data.get("thumbnail"),
        google_books_id=book_id
    )

    return render_template(
        "books/add-book-to-shelf.html",
        book_form=book_form,
        shelf=shelf
    )


def get_or_create_author(name):
    name = name.strip()
    author = db.session.scalar(db.select(Author).where(Author.name == name))
    if not author:
        author = Author(name=name)
        db.session.add(author)
    return author


def get_or_create_book(book_data):
    google_id = book_data["google_books_id"]
    book = db.session.scalar(
        db.select(Book).where(Book.google_books_id == google_id)
    )
    if book:
        return book

    # remove from dict before unpacking
    author_names = book_data.pop("authors", [])
    book = Book(**book_data)
    db.session.add(book)

    # handle authors as a list or a comma-separated string
    if isinstance(author_names, str):
        author_names = [a.strip() for a in author_names.split(",")]
    book.authors = [get_or_create_author(name)
                    for name in author_names if name]

    db.session.flush()
    return book


@app.route('/add-book-to-shelf/<int:shelf_id>', methods=["POST"])
@login_required
def add_book_to_shelf(shelf_id):
    form = BookForm()

    if not form.validate_on_submit():
        return render_template(
            "books/add-book-to-shelf.html",
            book_form=form
        )

    book = get_or_create_book({
        "title": form.title.data,
        "authors": form.author.data,
        "description": form.description.data,
        "cover_url": form.cover_url.data,
        "google_books_id": form.google_books_id.data,
    })

    # prevent duplicate shelf entry
    existing = db.session.scalar(
        db.select(ShelfEntry).where(
            ShelfEntry.shelf_id == shelf_id,
            ShelfEntry.book_id == book.id
        )
    )

    if existing:
        flash("Book already exists on this shelf.")
        return redirect(url_for("open_shelf", shelf_id=shelf_id))

    entry = ShelfEntry(
        shelf_id=shelf_id,
        book_id=book.id,
        added_by=current_user.id
    )

    db.session.add(entry)
    db.session.commit()

    return redirect(url_for("open_shelf", shelf_id=shelf_id))


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# Adding Notes
# ------------------------------------------------------------------------------------------------------------------------------------------------------


@app.route('/add-note-to-book')
def add_book_note():
    return render_template("index.html")


# ------------------------------------------------------------------------------------------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------------------------------------------------------------------------------------------

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        result = db.session.execute(
            db.select(User).where(User.email == email)
        )
        user = result.scalar()

        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))

        elif not check_password_hash(user.password_hash, password):
            flash("Password incorrect, please try again.")
            return redirect(url_for('login'))

        login_user(user, remember=form.remember.data)
        return redirect(url_for('home'))

    return render_template("auth/login.html", form=form)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegistrationForm()

    if form.validate_on_submit():
        email = form.email.data

        # Check if user already exists
        result = db.session.execute(
            db.select(User).where(User.email == email)
        )
        user = result.scalar()

        if user:
            flash("You've already signed up with that email, log in instead!")
            print("Query result:", user)
            return redirect(url_for('login'))

        # Hash password
        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )

        # Create new user
        new_user = User(
            email=form.email.data,
            password_hash=hash_and_salted_password,
            name=form.name.data,
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("home"))

        except Exception as e:
            db.session.rollback()
            print("DB Error:", e)
            flash("An error occurred while creating your account.")

    return render_template("auth/register.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/debug-db")
def debug_db():
    print(app.config["SQLALCHEMY_DATABASE_URI"])
    return str(db.engine.url)


if __name__ == "__main__":
    app.run(debug=True)
