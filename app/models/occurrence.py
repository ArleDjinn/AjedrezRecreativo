# app/models/occurrence.py
from app.extensions import db

class Occurrence(db.Model):
    __tablename__ = "occurrences"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id", ondelete="CASCADE"), nullable=False)

    start_dt = db.Column(db.DateTime, nullable=False)
    end_dt = db.Column(db.DateTime, nullable=False)

    # cupo por occurrence (solo lo usas si pricing_mode == PER_OCCURRENCE)
    capacity = db.Column(db.Integer, nullable=True)

    status = db.Column(db.String(20), nullable=False, default="scheduled")

    event = db.relationship("Event", back_populates="occurrences")
