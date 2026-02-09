from datetime import datetime, timezone
from app.extensions import db


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)

    # PACKAGE | PER_OCCURRENCE
    pricing_mode = db.Column(db.String(20), nullable=False)

    # CLP
    price = db.Column(db.Integer, nullable=False)

    # cupo por defecto para las sesiones
    capacity_default = db.Column(db.Integer, nullable=True)

    location_name = db.Column(db.String(120), nullable=False, default="Casa de Sanger")

    # draft | published | closed
    status = db.Column(db.String(20), nullable=False, default="draft")

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    occurrences = db.relationship(
        "Occurrence",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="Occurrence.start_dt",
    )

    purchases = db.relationship(
        "Purchase",
        back_populates="event",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Event {self.id} {self.title} mode={self.pricing_mode}>"
