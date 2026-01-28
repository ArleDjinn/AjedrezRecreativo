from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User
from .forms import LoginForm
from sqlalchemy import func
from app.models import Event, Occurrence, Purchase, PurchaseParticipant

admin_bp = Blueprint("admin", __name__, template_folder="templates")

@admin_bp.get("/")
@login_required
def admin_home():
    return render_template("admin/home.html")

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.admin_home"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not user.is_active or not user.check_password(form.password.data):
            flash("Credenciales inválidas.", "danger")
            return render_template("admin/login.html", form=form), 401

        login_user(user, remember=True)
        flash("Bienvenido.", "success")

        next_url = request.args.get("next")
        return redirect(next_url or url_for("admin.admin_home"))

    return render_template("admin/login.html", form=form)

@admin_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("admin.login"))

from .forms import EventForm, OccurrenceForm

@admin_bp.get("/events")
@login_required
def events_list():
    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template("admin/events_list.html", events=events)

@admin_bp.route("/events/new", methods=["GET", "POST"])
@login_required
def events_new():
    form = EventForm()
    if form.validate_on_submit():
        capacity_value = form.capacity.data if form.pricing_mode.data == "PACKAGE" else None
        ev = Event(
            title=form.title.data.strip(),
            category=form.category.data,
            pricing_mode=form.pricing_mode.data,
            price=form.price.data,
            capacity=capacity_value,
            location_name=form.location_name.data.strip(),
            status=form.status.data,
        )
        db.session.add(ev)
        db.session.commit()
        flash("Evento creado.", "success")
        return redirect(url_for("admin.event_detail", event_id=ev.id))
    return render_template("admin/event_form.html", form=form, mode="new")

@admin_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def events_edit(event_id):
    ev = Event.query.get_or_404(event_id)
    form = EventForm(obj=ev)

    if form.validate_on_submit():
        ev.title = form.title.data.strip()
        ev.category = form.category.data
        ev.pricing_mode = form.pricing_mode.data
        ev.price = form.price.data
        ev.capacity = form.capacity.data if form.pricing_mode.data == "PACKAGE" else None
        ev.location_name = form.location_name.data.strip()
        ev.status = form.status.data

        db.session.commit()
        flash("Evento actualizado.", "success")
        return redirect(url_for("admin.event_detail", event_id=ev.id))

    return render_template("admin/event_form.html", form=form, mode="edit", event=ev)

def _paid_participants_count_for_event(event_id: int) -> int:
    # cupo por participante: suma de participants en compras pagadas del evento
    return (
        db.session.query(func.count(PurchaseParticipant.id))
        .join(Purchase, PurchaseParticipant.purchase_id == Purchase.id)
        .filter(Purchase.event_id == event_id, Purchase.status == "paid")
        .scalar()
    ) or 0

def _paid_participants_count_for_occurrence(occurrence_id: int) -> int:
    # cuenta participantes de compras pagadas que incluyen esa occurrence
    return (
        db.session.query(func.count(PurchaseParticipant.id))
        .join(Purchase, PurchaseParticipant.purchase_id == Purchase.id)
        .join(Purchase.occurrences)  # many-to-many
        .filter(Purchase.status == "paid", Occurrence.id == occurrence_id)
        .scalar()
    ) or 0

@admin_bp.get("/events/<int:event_id>")
@login_required
def event_detail(event_id):
    ev = Event.query.get_or_404(event_id)

    paid_participants = _paid_participants_count_for_event(ev.id)
    remaining_event = None
    if ev.capacity is not None:
        remaining_event = max(ev.capacity - paid_participants, 0)

    # occurrences ordenadas (ya lo defines en relationship)
    occs = ev.occurrences

    occ_stats = []
    for oc in occs:
        if ev.pricing_mode == "PER_OCCURRENCE":
            oc_capacity = oc.capacity or 0
            oc_paid = _paid_participants_count_for_occurrence(oc.id)
            oc_remaining = max(oc_capacity - oc_paid, 0)
        else:
            oc_capacity = None
            oc_paid = None
            oc_remaining = None
        occ_stats.append((oc, oc_capacity, oc_paid, oc_remaining))

    return render_template(
        "admin/event_detail.html",
        event=ev,
        paid_participants=paid_participants,
        remaining_event=remaining_event,
        occ_stats=occ_stats,
    )

@admin_bp.route("/events/<int:event_id>/occurrences/new", methods=["GET", "POST"])
@login_required
def occurrence_new(event_id):
    ev = Event.query.get_or_404(event_id)
    form = OccurrenceForm()

    if form.validate_on_submit():
        # Regla de negocio:
        # - PER_OCCURRENCE → capacity OBLIGATORIA
        # - PACKAGE → capacity DEBE ser None
        if ev.pricing_mode == "PER_OCCURRENCE":
            if not form.capacity.data:
                form.capacity.errors.append(
                    "El cupo es obligatorio cuando el evento es 'Por sesión'."
                )
                return render_template(
                    "admin/occurrence_form.html", form=form, event=ev
                )
            capacity = form.capacity.data
        else:
            capacity = None

        oc = Occurrence(
            event_id=ev.id,
            start_dt=form.start_dt.data,
            end_dt=form.end_dt.data,
            capacity=capacity,
            status="scheduled",
        )
        db.session.add(oc)
        db.session.commit()

        flash("Sesión creada correctamente.", "success")
        return redirect(url_for("admin.event_detail", event_id=ev.id))

    return render_template("admin/occurrence_form.html", form=form, event=ev)

@admin_bp.post("/occurrences/<int:occurrence_id>/cancel")
@login_required
def occurrence_cancel(occurrence_id):
    oc = Occurrence.query.get_or_404(occurrence_id)
    oc.status = "cancelled"
    db.session.commit()
    flash("Sesión cancelada.", "warning")
    return redirect(url_for("admin.event_detail", event_id=oc.event_id))
