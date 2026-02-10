from datetime import datetime, timezone

from flask import Blueprint, current_app, render_template, request, abort, redirect, url_for

from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction

from app.extensions import db
from app.models import Purchase


payments_bp = Blueprint("payments", __name__, url_prefix="/pay")


def _webpay_tx() -> Transaction:
    commerce_code = current_app.config["WEBPAY_COMMERCE_CODE"]
    api_key = current_app.config["WEBPAY_API_KEY"]
    return Transaction(WebpayOptions(commerce_code, api_key, IntegrationType.TEST))


def _attach_package_occurrences_if_needed(purchase: Purchase) -> None:
    """
    Regla de negocio:
    - Si el evento es PACKAGE, al pagar se inscribe a TODAS las sesiones scheduled.
    - Si ya están asignadas, no hace nada (idempotente).
    """
    # Asegura relaciones cargadas
    event = purchase.event
    if event is None:
        return

    if event.pricing_mode != "PACKAGE":
        return

    # Si ya tiene occurrences asociadas, no duplicar trabajo
    if purchase.occurrences and len(purchase.occurrences) > 0:
        return

    scheduled = [oc for oc in (event.occurrences or []) if oc.status == "scheduled"]
    if not scheduled:
        return

    purchase.occurrences = scheduled


@payments_bp.get("/webpay/start/<int:purchase_id>")
def webpay_start(purchase_id: int):
    purchase = Purchase.query.get(purchase_id)
    if purchase is None:
        abort(404)

    if purchase.status != "pending":
        return redirect(url_for("checkout.checkout_success", purchase_id=purchase.id))

    return_url = url_for("payments.webpay_return", _external=True)
    buy_order = f"AR-{purchase.id}"
    session_id = str(purchase.id)
    amount = int(purchase.total_amount)

    tx = _webpay_tx()
    resp = tx.create(buy_order, session_id, amount, return_url)

    purchase.tbk_token = resp["token"]
    purchase.buy_order = buy_order
    db.session.commit()

    return render_template("payments/webpay_redirect.html", url=resp["url"], token=resp["token"])


@payments_bp.route("/webpay/return", methods=["GET", "POST"])
def webpay_return():
    token = request.values.get("token_ws")
    if not token:
        abort(400)

    purchase = Purchase.query.filter_by(tbk_token=token).first()
    if purchase is None:
        abort(404)

    # Si ya está resuelto, no vuelvas a commitear (idempotencia básica)
    if purchase.status in ("paid", "failed", "expired", "cancelled"):
        return redirect(url_for("checkout.checkout_success", purchase_id=purchase.id))

    tx = _webpay_tx()
    commit_resp = tx.commit(token)

    status = (commit_resp.get("status") or "").upper()

    if status == "AUTHORIZED":
        purchase.status = "paid"
        purchase.paid_at = datetime.now(timezone.utc)

        # ✅ Enlaza occurrences si es paquete
        _attach_package_occurrences_if_needed(purchase)

    else:
        purchase.status = "failed"

    db.session.commit()
    return redirect(url_for("checkout.checkout_success", purchase_id=purchase.id))