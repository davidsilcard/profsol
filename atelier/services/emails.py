from __future__ import annotations

from pathlib import Path
from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import EmailMessage
from django.urls import reverse
from django.utils import timezone

from atelier.models import PurchaseOrder


def send_recipe_purchase_email(order: PurchaseOrder) -> None:
    if not order.user.email:
        return

    download_path = reverse("atelier:recipe_download", kwargs={"slug": order.recipe.slug})
    download_url = urljoin(f"{settings.SITE_URL.rstrip('/')}/", download_path.lstrip("/"))
    subject = f"Sua receita {order.recipe.title} já está disponível"
    body = (
        f"Olá, {order.user.first_name or order.user.username}!\n\n"
        f"Seu pagamento foi aprovado e a receita {order.recipe.title} já está liberada.\n"
        f"Você pode baixar o PDF na sua área logada ou pelo link abaixo:\n\n"
        f"{download_url}\n\n"
        "Obrigada por apoiar o ateliê."
    )

    message = EmailMessage(subject=subject, body=body, to=[order.user.email], from_email=settings.DEFAULT_FROM_EMAIL)
    if order.recipe.pdf_file:
        message.attach_file(str(Path(order.recipe.pdf_file.path)))
    message.send(fail_silently=False)

    order.receipt_sent_at = timezone.now()
    order.save(update_fields=["receipt_sent_at", "updated_at"])
