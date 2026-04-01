from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


User = get_user_model()


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


def build_unique_slug(instance, value: str, slug_field: str = "slug") -> str:
    base_slug = slugify(value) or uuid.uuid4().hex[:10]
    slug = base_slug
    model_class = instance.__class__
    counter = 2

    while model_class.objects.filter(**{slug_field: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


class SiteContent(TimestampedModel):
    brand_name = models.CharField("nome da marca", max_length=120, default="Prof. Sol Tricô & Crochê")
    teacher_name = models.CharField("nome da professora", max_length=120, default="Professora Sol")
    hero_title = models.CharField(
        "título principal",
        max_length=160,
        default="Tricô e crochê com afeto, técnica e peças encantadoras.",
    )
    hero_subtitle = models.TextField(
        "subtítulo",
        default=(
            "Espaço para apresentar a professora, a proposta da marca e o estilo das aulas, "
            "receitas e projetos em fios."
        ),
    )
    about_title = models.CharField("título sobre", max_length=120, default="Um ateliê para aprender e criar")
    about_text = models.TextField(
        "texto sobre",
        default=(
            "Aqui entra a biografia da professora, sua experiência com tricô e crochê, "
            "método de ensino e a proposta do ateliê."
        ),
    )
    highlight_text = models.CharField(
        "frase de destaque",
        max_length=200,
        default="Modelos delicados, explicações cuidadosas e receitas pensadas para quem ama fios.",
    )
    hero_image = models.ImageField("foto principal", upload_to="site/hero/", blank=True)
    contact_email = models.EmailField("e-mail de contato", blank=True)
    instagram_url = models.URLField("Instagram", blank=True)
    whatsapp_number = models.CharField("WhatsApp", max_length=30, blank=True)

    class Meta:
        verbose_name = "conteúdo do site"
        verbose_name_plural = "conteúdo do site"

    def __str__(self) -> str:
        return self.brand_name

    @classmethod
    def current(cls) -> "SiteContent | None":
        return cls.objects.order_by("id").first()


class VideoTheme(TimestampedModel):
    name = models.CharField("tema", max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.TextField("descrição", blank=True)
    display_order = models.PositiveIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "tema de vídeo"
        verbose_name_plural = "temas de vídeo"
        ordering = ["display_order", "name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Video(TimestampedModel):
    theme = models.ForeignKey(
        VideoTheme,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="videos",
        verbose_name="tema",
    )
    title = models.CharField("título", max_length=200)
    youtube_id = models.CharField("ID do YouTube", max_length=30, unique=True)
    youtube_url = models.URLField("URL do vídeo")
    thumbnail_url = models.URLField("thumbnail", blank=True)
    description = models.TextField("descrição", blank=True)
    published_at = models.DateTimeField("publicado em", null=True, blank=True)
    imported_at = models.DateTimeField("importado em", auto_now_add=True)
    is_published = models.BooleanField("publicado no site", default=True)
    is_featured = models.BooleanField("destacar na home", default=False)

    class Meta:
        verbose_name = "vídeo"
        verbose_name_plural = "vídeos"
        ordering = ["-published_at", "-created_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def theme_label(self) -> str:
        return self.theme.name if self.theme else "Geral"


class Recipe(TimestampedModel):
    title = models.CharField("título", max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    short_description = models.CharField("descrição curta", max_length=220)
    description = models.TextField("descrição completa")
    cover_image = models.ImageField("imagem de capa", upload_to="recipes/covers/", blank=True)
    pdf_file = models.FileField("PDF da receita", upload_to="recipes/pdfs/", blank=True)
    price = models.DecimalField(
        "valor",
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    is_active = models.BooleanField("ativo", default=True)
    is_featured = models.BooleanField("destacar na home", default=False)

    class Meta:
        verbose_name = "receita"
        verbose_name_plural = "receitas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = build_unique_slug(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("atelier:recipe_detail", kwargs={"slug": self.slug})


class PurchaseOrder(TimestampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PENDING = "pending", "Pendente"
        PAID = "paid", "Pago"
        FAILED = "failed", "Falhou"
        CANCELED = "canceled", "Cancelado"
        REFUNDED = "refunded", "Reembolsado"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchase_orders")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="orders")
    status = models.CharField("status", max_length=20, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField("total", max_digits=8, decimal_places=2)
    external_reference = models.CharField(
        "referência externa",
        max_length=40,
        unique=True,
        default=uuid.uuid4,
        editable=False,
    )
    checkout_url = models.URLField("link de checkout", blank=True)
    mercadopago_preference_id = models.CharField("preference id", max_length=80, blank=True)
    mercadopago_payment_id = models.CharField("payment id", max_length=80, blank=True)
    provider_payload = models.JSONField("payload do gateway", blank=True, default=dict)
    paid_at = models.DateTimeField("pago em", null=True, blank=True)
    receipt_sent_at = models.DateTimeField("e-mail enviado em", null=True, blank=True)

    class Meta:
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.recipe.title} - {self.user}"

    @property
    def can_download(self) -> bool:
        return self.status == self.Status.PAID

    def mark_paid(self, payment_id: str = "") -> None:
        self.status = self.Status.PAID
        self.paid_at = timezone.now()
        if payment_id:
            self.mercadopago_payment_id = payment_id
        self.save(
            update_fields=[
                "status",
                "paid_at",
                "mercadopago_payment_id",
                "updated_at",
            ]
        )
