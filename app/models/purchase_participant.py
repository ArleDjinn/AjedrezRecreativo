from app.extensions import db

class PurchaseParticipant(db.Model):
    __tablename__ = "purchase_participants"

    id = db.Column(db.Integer, primary_key=True)
    purchase_id = db.Column(db.Integer, db.ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False)

    name = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)

    purchase = db.relationship("Purchase", backref=db.backref("participants", cascade="all, delete-orphan"))