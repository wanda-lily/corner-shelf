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


class Tag(db.Model):
    __tablename__ = "tag"

    id = db.Column(db.Integer,    primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)

    books = db.relationship("Book", secondary=book_tags, back_populates="tags")


class Book(db.Model):
    __tablename__ = "book"

    id = db.Column(db.Integer,     primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    author = db.Column(db.String(100))
    cover_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    google_books_id = db.Column(db.String(20),  unique=True, index=True)
    total_pages = db.Column(db.Integer)

    shelf_entries = db.relationship("ShelfEntry", back_populates="book")
    reading_logs = db.relationship("ReadingLog", back_populates="book")
    tags = db.relationship("Tag", secondary=book_tags, back_populates="books")
    notes = db.relationship("BookNote", back_populates="book")
