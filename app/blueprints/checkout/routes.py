import json
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, abort, request, redirect, url_for
from app.extensions import db
from app.models import Event, Purchase, PurchaseParticipant


checkout_bp = Blueprint("checkout", __name__)


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


def _pending_or_paid_participants_for_event(event_id: int) -> int:
    # Reserva cupos con pending (hasta que expiren) y cuenta paid.
    return (
        db.session.query(PurchaseParticipant.id)
        .join(Purchase, PurchaseParticipant.purchase_id == Purchase.id)
        .filter(
            Purchase.event_id == event_id,
            Purchase.status.in_(["pending", "paid"]),
        )
        .count()
    )


def remaining_capacity(event: Event) -> int | None:
    """
    Para PACKAGE: el cupo real es por sesión.
    En MVP, el cupo del pack es el mínimo cupo efectivo entre sesiones scheduled.
    remaining = min_cap - used (used = participantes en pending/paid del evento)

    Si no hay sesiones scheduled, devolvemos None (no bloqueamos por cupo aquí).
    Si alguna sesión no tiene cupo (cap None), lo tratamos como ilimitado (None) y
    entonces el pack queda ilimitado; PERO en tu admin estás exigiendo capacity_default
    para PACKAGE, así que en la práctica cap debería existir.
    """
    scheduled = [oc for oc in (event.occurrences or []) if oc.status == "scheduled"]
    if not scheduled:
        return None

    caps = []
    for oc in scheduled:
        cap = oc.effective_capacity()  # override o default del evento
        if cap is None:
            # cupo ilimitado en alguna sesión => pack ilimitado
            return None
        caps.append(int(cap))

    cap_pack = min(caps) if caps else None
    if cap_pack is None:
        return None

    used = _pending_or_paid_participants_for_event(event.id)
    return max(cap_pack - used, 0)


def compute_total_price(event: Event) -> int:
    # En este blueprint solo estamos manejando PACKAGE.
    return int(event.price or 0)


@checkout_bp.get("/event/<int:event_id>")
def checkout_event(event_id: int):
    event = Event.query.get(event_id)
    if event is None or event.status != "published":
        abort(404)

    # Este checkout es solo para PACKAGE (como lo tenías).
    if event.pricing_mode != "PACKAGE":
        abort(400)

    expire_old_pending(event)

    occurrences = sorted(
        [oc for oc in (event.occurrences or []) if oc.status == "scheduled"],
        key=lambda o: o.start_dt,
    )

    total_price = compute_total_price(event)

    capacity_left = remaining_capacity(event)
    if capacity_left is not None and capacity_left <= 0:
        abort(409)

    return render_template(
        "checkout/event_checkout.html",
        event=event,
        occurrences=occurrences,
        total_price=total_price,
        capacity_left=capacity_left,
        error=None,
        form=None,
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

    occurrences = sorted(
        [oc for oc in (event.occurrences or []) if oc.status == "scheduled"],
        key=lambda o: o.start_dt,
    )

    if capacity_left is not None and capacity_left <= 0:
        return render_template(
            "checkout/event_checkout.html",
            event=event,
            occurrences=occurrences,
            total_price=compute_total_price(event),
            capacity_left=capacity_left,
            error="No quedan cupos disponibles para este evento.",
            form=None,
        ), 409

    # 2) Buyer
    buyer_name = (request.form.get("buyer_name") or "").strip()
    buyer_email = (request.form.get("buyer_email") or "").strip()
    buyer_phone = (request.form.get("buyer_phone") or "").strip()

    # 3) Cantidad participantes
    try:
        participant_count = int(request.form.get("participant_count") or "1")
    except ValueError:
        participant_count = 1
    participant_count = max(participant_count, 1)

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

    # 5) Validaciones
    if not buyer_name or not buyer_email or not buyer_phone or not participants:
        return render_template(
            "checkout/event_checkout.html",
            event=event,
            occurrences=occurrences,
            total_price=compute_total_price(event) * participant_count,
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

    if capacity_left is not None and participant_count > capacity_left:
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

    # 6) Precio: pack POR PARTICIPANTE
    unit_price = compute_total_price(event)
    total_price = unit_price * participant_count

    # 7) Crear Purchase + participants
    purchase = Purchase(
        event_id=event.id,
        buyer_name=buyer_name,
        buyer_email=buyer_email,
        buyer_phone=buyer_phone,
        total_amount=total_price,
        status="pending",
    )

    db.session.add(purchase)
    db.session.flush()

    for p in participants:
        db.session.add(
            PurchaseParticipant(
                purchase_id=purchase.id,
                name=p["name"],
                age=p["age"],
            )
        )

    db.session.commit()

    return redirect(url_for("payments.webpay_start", purchase_id=purchase.id))


@checkout_bp.get("/success/<int:purchase_id>")
def checkout_success(purchase_id: int):
    purchase = Purchase.query.get(purchase_id)
    if purchase is None:
        abort(404)
    return render_template("checkout/success.html", purchase=purchase)