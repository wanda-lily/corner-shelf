# Import every model so SQLAlchemy registers them all with the metadata
# before db.create_all() is called. Order matters — tables with no
# foreign-key dependencies come first.

from .db import db
from .user import User
from .book import Tag, Book, book_tags
from .shelf import Shelf, ShelfEntry, ShelfParticipant
from .reading import ReadingLog, BookNote
from .activity import ActivityLog

__all__ = [
    "db", "User",
    "Tag", "Book", "book_tags",
    "Shelf", "ShelfEntry", "ShelfParticipant",
    "ReadingLog", "BookNote",
    "ActivityLog",
]
