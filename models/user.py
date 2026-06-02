from flask_login import UserMixin
from models.db import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer,    primary_key=True)
    name = db.Column(db.String(50),  nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)

    shelf_entries = db.relationship("ShelfEntry",       back_populates="user")
    shelves = db.relationship("Shelf",            back_populates="owner",
                              foreign_keys="Shelf.owner_id")
    participations = db.relationship("ShelfParticipant", back_populates="user")
    reading_logs = db.relationship("ReadingLog",       back_populates="user")
