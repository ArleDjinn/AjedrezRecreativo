# app/models/purchase_occurrence.py
from app.extensions import db

purchase_occurrences = db.Table(
    "purchase_occurrences",
    db.Column("purchase_id", db.Integer, db.ForeignKey("purchases.id", ondelete="CASCADE"), primary_key=True),
    db.Column("occurrence_id", db.Integer, db.ForeignKey("occurrences.id", ondelete="CASCADE"), primary_key=True),
)