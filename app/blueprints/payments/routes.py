from flask import Blueprint, current_app, render_template, request, abort, redirect, url_for
from datetime import datetime, timezone

from transbank.common.integration_type import IntegrationType
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction

from app.extensions import db
from app.models import Purchase

payments_bp = Blueprint("payments", __name__, url_prefix="/pay")


def _webpay_tx() -> Transaction:
    # TEST: usa tus credenciales de integración (o las de Transbank si decides)
    commerce_code = current_app.config["WEBPAY_COMMERCE_CODE"]
    api_key = current_app.config["WEBPAY_API_KEY"]
    return Transaction(WebpayOptions(commerce_code, api_key, IntegrationType.TEST))  # :contentReference[oaicite:4]{index=4}


@payments_bp.get("/webpay/start/<int:purchase_id>")
def webpay_start(purchase_id: int):
    purchase = Purchase.query.get(purchase_id)
    if purchase is None:
        abort(404)
    if purchase.status != "pending":
        # si ya pagó o expiró, no tiene sentido reintentar acá
        return redirect(url_for("checkout.checkout_success", purchase_id=purchase.id))

    return_url = url_for("payments.webpay_return", _external=True)
    buy_order = f"AR-{purchase.id}"
    session_id = str(purchase.id)
    amount = int(purchase.total_amount)

    tx = _webpay_tx()
    resp = tx.create(buy_order, session_id, amount, return_url)  # :contentReference[oaicite:5]{index=5}

    # resp trae: token + url (donde postear token_ws) :contentReference[oaicite:6]{index=6}
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

    tx = _webpay_tx()
    commit_resp = tx.commit(token)  # :contentReference[oaicite:7]{index=7}

    # En la respuesta viene el status (AUTHORIZED cuando aprueba)
    status = (commit_resp.get("status") or "").upper()

    if status == "AUTHORIZED":
        purchase.status = "paid"
        purchase.paid_at = datetime.now(timezone.utc)
    else:
        purchase.status = "failed"

    db.session.commit()
    return redirect(url_for("checkout.checkout_success", purchase_id=purchase.id))