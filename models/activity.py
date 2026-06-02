from sqlalchemy import func, JSON
from models.db import db


class ActivityLog(db.Model):
    """Append-only audit trail. Never update rows here."""
    __tablename__ = "activity_log"

    id = db.Column(db.Integer,     primary_key=True)
    user_id = db.Column(db.Integer,     db.ForeignKey(
        "user.id"), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(JSON)
    timestamp = db.Column(db.DateTime(timezone=True),
                          server_default=func.now(), index=True)
