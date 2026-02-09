from datetime import datetime, timezone
from app.extensions import db
from app.models.purchase_occurrence import purchase_occurrences


class Purchase(db.Model):
    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )

    buyer_name = db.Column(db.String(120), nullable=False)
    buyer_email = db.Column(db.String(120), nullable=False)
    buyer_phone = db.Column(db.String(30), nullable=False)

    total_amount = db.Column(db.Integer, nullable=False)

    # Transbank
    tbk_token = db.Column(db.String(120), unique=True, nullable=True)
    buy_order = db.Column(db.String(120), unique=True, nullable=True)

    # pending | paid | failed | expired | cancelled
    status = db.Column(db.String(20), nullable=False, default="pending")

    paid_at = db.Column(db.DateTime(timezone=True), nullable=True)

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    event = db.relationship("Event", back_populates="purchases")

    occurrences = db.relationship(
        "Occurrence",
        secondary=purchase_occurrences,
        back_populates="purchases",
        lazy="subquery",
    )

    participants = db.relationship(
        "PurchaseParticipant",
        cascade="all, delete-orphan",
        back_populates="purchase",
    )

    def __repr__(self) -> str:
        return f"<Purchase {self.id} event={self.event_id} status={self.status}>"
