from sqlalchemy import func
from models.db import db


# Association table — defined here because Book owns the relationship
book_tags = db.Table(
    "book_tags",
    db.Column("book_id", db.Integer, db.ForeignKey(
        "book.id"), primary_key=True),
    db.Column("tag_id",  db.Integer, db.ForeignKey(
        "tag.id"),  primary_key=True),
)


book_authors = db.Table(
    "book_authors",
    db.Column("book_id", db.Integer, db.ForeignKey(
        "book.id"), primary_key=True),
    db.Column("author_id", db.Integer, db.ForeignKey(
        "author.id"), primary_key=True),
)


class Author(db.Model):
    __tablename__ = "author"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    books = db.relationship(
        "Book", secondary=book_authors, back_populates="authors")


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer,    primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    books = db.relationship("Book", secondary=book_tags, back_populates="tags")


class Book(db.Model):
    __tablename__ = "book"

    id = db.Column(db.Integer,     primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    cover_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    google_books_id = db.Column(db.String(20),  unique=True, index=True)
    total_pages = db.Column(db.Integer)

    shelf_entries = db.relationship("ShelfEntry", back_populates="book")
    reading_logs = db.relationship("ReadingLog", back_populates="book")
    tags = db.relationship("Tag", secondary=book_tags, back_populates="books")
    notes = db.relationship("BookNote", back_populates="book")

    authors = db.relationship(
        "Author", secondary=book_authors, back_populates="books")
