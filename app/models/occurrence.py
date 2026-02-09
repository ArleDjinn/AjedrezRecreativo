from datetime import datetime
from app.extensions import db


class Occurrence(db.Model):
    __tablename__ = "occurrences"
    __table_args__ = (
        db.UniqueConstraint("event_id", "start_dt", name="uq_event_start"),
    )

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    start_dt = db.Column(db.DateTime(timezone=True), nullable=False)
    end_dt = db.Column(db.DateTime(timezone=True), nullable=False)

    # override opcional
    capacity_override = db.Column(db.Integer, nullable=True)
    price_override = db.Column(db.Integer, nullable=True)

    # scheduled | cancelled
    status = db.Column(db.String(20), nullable=False, default="scheduled")

    event = db.relationship("Event", back_populates="occurrences")

    purchases = db.relationship(
        "Purchase",
        secondary="purchase_occurrences",
        back_populates="occurrences",
    )

    def effective_capacity(self) -> int | None:
        return self.capacity_override or self.event.capacity_default

    def effective_price(self) -> int:
        return self.price_override or self.event.price

    def __repr__(self) -> str:
        return f"<Occurrence {self.id} event={self.event_id} {self.start_dt.isoformat()}>"

