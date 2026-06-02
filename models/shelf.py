from sqlalchemy import func
from models.db import db
from models.enums import ShelfType, ShelfRole


class Shelf(db.Model):
    __tablename__ = "shelf"

    id = db.Column(db.Integer,          primary_key=True)
    name = db.Column(db.String(100),       nullable=False)
    owner_id = db.Column(
        db.Integer,           db.ForeignKey("user.id"), nullable=False)
    shelf_type = db.Column(db.Enum(ShelfType),
                           nullable=False, default=ShelfType.personal)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    owner = db.relationship("User",             back_populates="shelves",
                            foreign_keys=[owner_id])
    entries = db.relationship("ShelfEntry",       back_populates="shelf")
    participants = db.relationship("ShelfParticipant", back_populates="shelf")


class ShelfEntry(db.Model):
    __tablename__ = "shelf_entry"

    id = db.Column(db.Integer, primary_key=True)
    shelf_id = db.Column(db.Integer, db.ForeignKey("shelf.id"), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"),  nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey("user.id"),  nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())

    shelf = db.relationship("Shelf", back_populates="entries")
    book = db.relationship("Book",  back_populates="shelf_entries")
    user = db.relationship("User",  back_populates="shelf_entries",
                           foreign_keys=[added_by])

    __table_args__ = (
        db.UniqueConstraint("shelf_id", "book_id", name="uix_shelf_book"),
    )


class ShelfParticipant(db.Model):
    __tablename__ = "shelf_participant"

    id = db.Column(db.Integer, primary_key=True)
    shelf_id = db.Column(db.Integer, db.ForeignKey("shelf.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"),  nullable=False)
    role = db.Column(db.Enum(ShelfRole), nullable=False,
                     default=ShelfRole.viewer)
    joined_at = db.Column(db.DateTime(timezone=True),
                          server_default=func.now())

    shelf = db.relationship("Shelf", back_populates="participants")
    user = db.relationship("User",  back_populates="participations")

    __table_args__ = (
        db.UniqueConstraint("shelf_id", "user_id",
                            name="uix_shelf_participant"),
    )
