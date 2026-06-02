from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap5
from flask_login import login_user, LoginManager, login_required, current_user, logout_user
from flask_wtf import CSRFProtect
from forms import *
from models.book import Book, Tag
from models.db import db
from models.user import User
from models.shelf import Shelf, ShelfEntry, ShelfParticipant, ShelfRole, ShelfType
import os
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def home():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Making and Editing Shelves
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Adding Books
# ---------------------------------------------------------------------------


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
            "authors": volume.get("authors", []),
            "description": volume.get("description"),
            "thumbnail": volume.get("imageLinks", {}).get("thumbnail"),
            "google_books_id": item.get("id")
        })

    return books


@app.route('/add-book-to-shelf/<int:shelf_id>', methods=["GET", "POST"])
def add_book_shelf(shelf_id):
    search_form = SearchBookForm()
    book_form = BookForm()
    books = []

    if search_form.validate_on_submit():
        query = search_form.search.data
        books = get_book(query)

    shelf = db.get_or_404(Shelf, shelf_id)

    return render_template(
        "books/add-book-to-shelf.html",
        form=search_form,
        books=books,
        shelf=shelf,
        book_form=book_form
    )


@app.route('/add-selected-book/<int:shelf_id>', methods=["POST"])
def add_selected_book(shelf_id):
    shelf = db.get_or_404(Shelf, shelf_id)

    title = request.form.get("title")
    author = request.form.get("author")
    thumbnail = request.form.get("thumbnail")

    # create book
    book = Book(
        title=title,
        author=author,
        cover_url=thumbnail
    )

    db.session.add(book)
    db.session.flush()  # get book.id

    # create shelf entry
    entry = ShelfEntry(
        shelf_id=shelf.id,
        book_id=book.id,
        added_by=current_user.id
    )

    db.session.add(entry)
    db.session.commit()

    return redirect(url_for("view_shelf", shelf_id=shelf.id))


@app.route('/add-manual-book/<int:shelf_id>', methods=["POST"])
def add_manual_book(shelf_id):
    form = BookForm()

    if not form.validate_on_submit():
        return redirect(request.url)

    book = Book(
        title=form.title.data,
        author=form.author.data,
        cover_url=form.cover_url.data,
        description=form.description.data
    )

    db.session.add(book)
    db.session.flush()

    entry = ShelfEntry(
        shelf_id=shelf_id,
        book_id=book.id,
        added_by=current_user.id
    )

    db.session.add(entry)
    db.session.commit()

    return redirect(url_for("view_shelf", shelf_id=shelf_id))


@app.route("/api/add-book/<int:shelf_id>", methods=["POST"])
@login_required
def api_add_book(shelf_id):
    data = request.get_json()

    google_id = data.get("google_books_id")

    # check if book already exists globally
    if google_id:
        book = db.session.scalar(
            db.select(Book).where(Book.google_books_id == google_id)
        )
    else:
        book = None

    if not book:
        book = Book(
            title=data.get("title"),
            author=data.get("author"),
            cover_url=data.get("thumbnail"),
            google_books_id=google_id
        )
        db.session.add(book)
        db.session.flush()

    # check if already on this shelf
    existing_entry = db.session.scalar(
        db.select(ShelfEntry).where(
            ShelfEntry.shelf_id == shelf_id,
            ShelfEntry.book_id == book.id
        )
    )

    if existing_entry:
        return {"status": "exists"}

    # add to shelf
    entry = ShelfEntry(
        shelf_id=shelf_id,
        book_id=book.id,
        added_by=current_user.id
    )

    db.session.add(entry)
    db.session.commit()

    return {"status": "added"}


@app.route("/api/search-books")
@login_required
def search_books():
    query = request.args.get("q", "")

    # google books call
    books = get_book(query)

    # get existing book IDs in THIS shelf
    shelf_id = request.args.get("shelf_id")

    existing_ids = set()

    if shelf_id:
        existing_ids = {
            b.google_books_id
            for (b,) in db.session.query(Book)
            .join(ShelfEntry)
            .filter(ShelfEntry.shelf_id == shelf_id)
            .all()
            if b.google_books_id
        }

    # mark books as already added
    for b in books:
        b["already_added"] = b.get("google_books_id") in existing_ids

    return books


@app.route('/add-note-to-book')
def add_book_note():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

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
    except Exception as e:
        db.session.rollback()
        print("DB Error:", e)
        flash("An error occurred while creating your account.")

        login_user(new_user)
        return redirect(url_for("home"))

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
