from flask import Blueprint, render_template, abort
from app.models import Event

public_bp = Blueprint("public", __name__)


@public_bp.get("/")
def home():
    events = (
        Event.query
        .filter_by(status="published", pricing_mode="PACKAGE")
        .order_by(Event.created_at.desc())
        .all()
    )
    return render_template("public/home.html", events=events)


@public_bp.get("/events/<int:event_id>")
def event_detail(event_id: int):
    event = Event.query.get(event_id)
    if event is None:
        abort(404)

    # Importante: aquí sí puedes mostrar las fechas "humanas"
    # sin hablar de "occurrences" como concepto técnico.
    # Solo: "Fechas incluidas".
    occurrences = sorted(
        event.occurrences,
        key=lambda o: o.start_dt
    )

    return render_template(
        "public/event_detail.html",
        event=event,
        occurrences=occurrences
    )
