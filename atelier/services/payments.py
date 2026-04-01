from __future__ import annotations

from urllib.parse import urljoin

import requests
from django.conf import settings
from django.utils import timezone

from atelier.models import PurchaseOrder


class PaymentGatewayError(Exception):
    pass


def mercado_pago_is_configured() -> bool:
    return bool(settings.MERCADO_PAGO_ACCESS_TOKEN and settings.SITE_URL)


def build_absolute_url(path: str) -> str:
    return urljoin(f"{settings.SITE_URL.rstrip('/')}/", path.lstrip("/"))


def create_checkout_preference(order: PurchaseOrder) -> str:
    if not mercado_pago_is_configured():
        raise PaymentGatewayError("Mercado Pago ainda não está configurado.")

    endpoint = "https://api.mercadopago.com/checkout/preferences"
    headers = {
        "Authorization": f"Bearer {settings.MERCADO_PAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "items": [
            {
                "id": str(order.recipe_id),
                "title": order.recipe.title,
                "description": order.recipe.short_description,
                "quantity": 1,
                "currency_id": "BRL",
                "unit_price": float(order.total_amount),
            }
        ],
        "external_reference": order.external_reference,
        "payer": {"email": order.user.email},
        "back_urls": {
            "success": build_absolute_url("/checkout/sucesso/"),
            "pending": build_absolute_url("/checkout/pendente/"),
            "failure": build_absolute_url("/checkout/falha/"),
        },
        "auto_return": "approved",
        "notification_url": build_absolute_url("/checkout/mercado-pago/notificacoes/"),
        "statement_descriptor": "PROFSOL",
    }

    response = requests.post(endpoint, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    data = response.json()

    order.mercadopago_preference_id = data.get("id", "")
    order.checkout_url = data.get("init_point") or data.get("sandbox_init_point", "")
    order.provider_payload = data
    order.save(
        update_fields=[
            "mercadopago_preference_id",
            "checkout_url",
            "provider_payload",
            "updated_at",
        ]
    )
    return order.checkout_url


def fetch_payment_details(payment_id: str) -> dict:
    if not mercado_pago_is_configured():
        raise PaymentGatewayError("Mercado Pago ainda não está configurado.")

    endpoint = f"https://api.mercadopago.com/v1/payments/{payment_id}"
    headers = {"Authorization": f"Bearer {settings.MERCADO_PAGO_ACCESS_TOKEN}"}
    response = requests.get(endpoint, headers=headers, timeout=20)
    response.raise_for_status()
    return response.json()


def update_order_from_payment_data(payment_data: dict) -> PurchaseOrder | None:
    external_reference = payment_data.get("external_reference")
    if not external_reference:
        return None

    try:
        order = PurchaseOrder.objects.select_related("recipe", "user").get(external_reference=external_reference)
    except PurchaseOrder.DoesNotExist:
        return None

    status = payment_data.get("status")
    order.provider_payload = payment_data
    order.mercadopago_payment_id = str(payment_data.get("id", "") or "")

    if status == "approved":
        order.status = PurchaseOrder.Status.PAID
        order.paid_at = timezone.now()
    elif status in {"pending", "in_process", "authorized"}:
        order.status = PurchaseOrder.Status.PENDING
    elif status in {"cancelled", "rejected"}:
        order.status = PurchaseOrder.Status.FAILED

    order.save(
        update_fields=[
            "status",
            "paid_at",
            "mercadopago_payment_id",
            "provider_payload",
            "updated_at",
        ]
    )
    return order
