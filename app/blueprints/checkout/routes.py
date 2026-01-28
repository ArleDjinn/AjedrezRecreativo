import json
from flask import Blueprint, render_template, abort, request, redirect, url_for
from app.extensions import db
from app.models import Event, Purchase, PurchaseParticipant
from datetime import datetime, timedelta, timezone

def remaining_capacity(event) -> int:
    if event.capacity is None:
        return 0
    used = (
        db.session.query(PurchaseParticipant)
        .join(Purchase, PurchaseParticipant.purchase_id == Purchase.id)
        .filter(
            Purchase.event_id == event.id,
            Purchase.status.in_(["pending", "paid"]),
        )
        .count()
    )
    return max(event.capacity - used, 0)

def expire_old_pending(event) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    (
        Purchase.query
        .filter(
            Purchase.event_id == event.id,
            Purchase.status == "pending",
            Purchase.created_at < cutoff,
        )
        .update({"status": "expired"}, synchronize_session=False)
    )
    db.session.commit()

checkout_bp = Blueprint("checkout", __name__)

def compute_total_price(event: Event) -> int:
    occurrences = sorted(event.occurrences, key=lambda o: o.start_dt)

    if event.pricing_mode == "PACKAGE":
        return int(event.price or 0)

    return int((event.price or 0) * len(occurrences))

@checkout_bp.get("/event/<int:event_id>")
def checkout_event(event_id: int):
    event = Event.query.get(event_id)

    if event is None or event.status != "published":
        abort(404)
    if event.pricing_mode != "PACKAGE":
        abort(400)

    occurrences = sorted(event.occurrences, key=lambda o: o.start_dt)
    total_price = compute_total_price(event)

    expire_old_pending(event)

    capacity_left = remaining_capacity(event)
    if capacity_left <= 0:
        abort(409)  # Conflict: no hay cupos

    return render_template(
        "checkout/event_checkout.html",
        event=event,
        occurrences=occurrences,
        total_price=total_price,
        capacity_left=capacity_left,
    )

@checkout_bp.post("/event/<int:event_id>")
def checkout_event_post(event_id: int):
    event = Event.query.get(event_id)

    if event is None or event.status != "published":
        abort(404)
    if event.pricing_mode != "PACKAGE":
        abort(400)

    # 1) Expira pending antiguos y recalcula cupos reales
    expire_old_pending(event)
    capacity_left = remaining_capacity(event)

    if capacity_left <= 0:
        occurrences = sorted(event.occurrences, key=lambda o: o.start_dt)
        return render_template(
            "checkout/event_checkout.html",
            event=event,
            occurrences=occurrences,
            total_price=0,
            capacity_left=capacity_left,
            error="No quedan cupos disponibles para este evento.",
        ), 409

    # 2) Buyer (siempre)
    buyer_name = (request.form.get("buyer_name") or "").strip()
    buyer_email = (request.form.get("buyer_email") or "").strip()
    buyer_phone = (request.form.get("buyer_phone") or "").strip()

    # 3) Cantidad participantes
    try:
        participant_count = int(request.form.get("participant_count") or "1")
    except ValueError:
        participant_count = 1

    if participant_count < 1:
        participant_count = 1

    # 4) Lee participantes dinámicos
    participants = []
    for i in range(participant_count):
        pname = (request.form.get(f"participant_name_{i}") or "").strip()
        page_raw = request.form.get(f"participant_age_{i}")

        try:
            page = int(page_raw)
        except (TypeError, ValueError):
            page = None

        if (not pname) or (page is None) or (page <= 0):
            participants = None
            break

        participants.append({"name": pname, "age": page})

    occurrences = sorted(event.occurrences, key=lambda o: o.start_dt)

    # 5) Validaciones
    if not buyer_name or not buyer_email or not buyer_phone or not participants:
        return render_template(
            "checkout/event_checkout.html",
            event=event,
            occurrences=occurrences,
            total_price=compute_total_price(event) * max(participant_count, 1),
            capacity_left=capacity_left,
            error="Revisa los datos del comprador y de los participantes.",
            form={
                "buyer_name": buyer_name,
                "buyer_email": buyer_email,
                "buyer_phone": buyer_phone,
                "participant_count": str(participant_count),
                "participants_json": json.dumps(participants if participants else []),
            },
        ), 400

    if participant_count > capacity_left:
        return render_template(
            "checkout/event_checkout.html",
            event=event,
            occurrences=occurrences,
            total_price=compute_total_price(event) * participant_count,
            capacity_left=capacity_left,
            error=f"No hay cupos suficientes. Disponibles: {capacity_left}.",
            form={
                "buyer_name": buyer_name,
                "buyer_email": buyer_email,
                "buyer_phone": buyer_phone,
                "participant_count": str(participant_count),
                "participants_json": json.dumps(participants),
            },
        ), 409

    # 6) Precio: pack POR PARTICIPANTE (estándar industria)
    unit_price = compute_total_price(event)  # pack por persona
    total_price = unit_price * participant_count

    # 7) Crear Purchase + participants (1 commit)
    purchase = Purchase(
        event_id=event.id,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        total_amount=total_price,
        status="pending",
    )

    db.session.add(purchase)
    db.session.flush()  # para obtener purchase.id sin commit

    for p in participants:
        db.session.add(PurchaseParticipant(
            purchase_id=purchase.id,
            name=p["name"],
            age=p["age"],
        ))

    db.session.commit()

    return redirect(url_for("payments.webpay_start", purchase_id=purchase.id))

@checkout_bp.get("/success/<int:purchase_id>")
def checkout_success(purchase_id: int):
    purchase = Purchase.query.get(purchase_id)
    if purchase is None:
        abort(404)
    return render_template("checkout/success.html", purchase=purchase)
