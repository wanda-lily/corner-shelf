from sqlalchemy import func
from models.db import db
from models.enums import ReadingStatus


class ReadingLog(db.Model):
    __tablename__ = "reading_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        "user.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    status = db.Column(db.Enum(ReadingStatus), nullable=False,
                       default=ReadingStatus.want_to_read)
    rating = db.Column(db.Integer)
    progress_pages = db.Column(db.Integer)
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())

    user = db.relationship("User", back_populates="reading_logs")
    book = db.relationship("Book", back_populates="reading_logs")

    __table_args__ = (
        db.UniqueConstraint("user_id", "book_id",
                            name="uix_readinglog_user_book"),
        db.CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)",
                           name="chk_rating_range"),
    )


class BookNote(db.Model):
    __tablename__ = "book_note"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(
        "user.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("book.id"), nullable=False)
    content = db.Column(db.Text,    nullable=False)
    page = db.Column(db.Integer)
    created_at = db.Column(db.DateTime(timezone=True),
                           server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())

    user = db.relationship("User", backref=db.backref(
        "book_notes", lazy="dynamic"))
    book = db.relationship("Book", back_populates="notes")
