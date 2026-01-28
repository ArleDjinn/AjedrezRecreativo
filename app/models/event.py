from datetime import datetime
from app.extensions import db

class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)

    # "PACKAGE" | "PER_OCCURRENCE"
    pricing_mode = db.Column(db.String(20), nullable=False)

    # CLP. Si pricing_mode=PACKAGE => precio paquete. Si PER_OCCURRENCE => precio por sesión.
    price = db.Column(db.Integer, nullable=False)

    capacity = db.Column(db.Integer, nullable=True, default=20)  # cupo global (PACKAGE)
    category = db.Column(db.String(20), nullable=False, default="class")

    location_name = db.Column(db.String(120), nullable=False, default="Casa de Sanger")
    status = db.Column(db.String(20), nullable=False, default="draft")  # draft/published/closed
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    occurrences = db.relationship(
        "Occurrence",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="Occurrence.start_dt",
    )
