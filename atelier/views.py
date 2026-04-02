from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.edit import FormView
from django.conf import settings

from atelier.forms import SignUpForm
from atelier.models import PurchaseOrder, Recipe, SiteContent, Video, VideoTheme
from atelier.services.emails import send_recipe_purchase_email
from atelier.services.payments import (
    PaymentGatewayError,
    create_checkout_preference,
    fetch_payment_details,
    mercado_pago_is_configured,
    update_order_from_payment_data,
)
from atelier.services.qrcode import build_qr_code_data_uri
from atelier.services.youtube import sync_on_demand_if_needed


class HomeView(TemplateView):
    template_name = "atelier/home.html"

    def get_context_data(self, **kwargs):
        sync_on_demand_if_needed()
        context = super().get_context_data(**kwargs)
        context["site_content"] = SiteContent.current()
        context["featured_videos"] = Video.objects.filter(is_published=True).order_by("-published_at", "-created_at")[:6]
        context["featured_recipes"] = Recipe.objects.filter(is_active=True).order_by("-created_at")[:6]
        context["site_qr_code"] = build_qr_code_data_uri(settings.SITE_URL)
        return context


class VideoListView(TemplateView):
    template_name = "atelier/video_list.html"

    def get_context_data(self, **kwargs):
        sync_on_demand_if_needed()
        context = super().get_context_data(**kwargs)
        themes = VideoTheme.objects.prefetch_related("videos")
        sections = []

        for theme in themes:
            videos = theme.videos.filter(is_published=True)
            if videos.exists():
                sections.append({"title": theme.name, "description": theme.description, "videos": videos})

        unthemed = Video.objects.filter(is_published=True, theme__isnull=True)
        if unthemed.exists():
            sections.append(
                {
                    "title": "Geral",
                    "description": "Vídeos recentes importados do canal no YouTube.",
                    "videos": unthemed,
                }
            )

        context["video_sections"] = sections
        context["channel_url"] = settings.YOUTUBE_CHANNEL_URL
        return context


class RecipeListView(ListView):
    template_name = "atelier/recipe_list.html"
    model = Recipe
    context_object_name = "recipes"

    def get_queryset(self):
        return Recipe.objects.filter(is_active=True)


class RecipeDetailView(DetailView):
    template_name = "atelier/recipe_detail.html"
    model = Recipe
    context_object_name = "recipe"

    def get_queryset(self):
        return Recipe.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context["user_order"] = (
                PurchaseOrder.objects.filter(
                    user=self.request.user,
                    recipe=self.object,
                    status=PurchaseOrder.Status.PAID,
                )
                .order_by("-created_at")
                .first()
            )
        return context


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "atelier/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        orders = (
            PurchaseOrder.objects.filter(user=self.request.user)
            .select_related("recipe")
            .order_by("-created_at")
        )
        context["paid_orders"] = orders.filter(status=PurchaseOrder.Status.PAID)
        context["pending_orders"] = orders.exclude(status=PurchaseOrder.Status.PAID)
        return context


class SignUpView(FormView):
    template_name = "registration/signup.html"
    form_class = SignUpForm
    success_url = reverse_lazy("atelier:dashboard")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "Cadastro realizado com sucesso.")
        return super().form_valid(form)


@require_POST
def recipe_checkout_start(request, slug):
    if not request.user.is_authenticated:
        return redirect(f"{reverse_lazy('login')}?next={request.path}")

    recipe = get_object_or_404(Recipe, slug=slug, is_active=True)
    existing_paid_order = PurchaseOrder.objects.filter(
        user=request.user,
        recipe=recipe,
        status=PurchaseOrder.Status.PAID,
    ).first()
    if existing_paid_order:
        messages.info(request, "Essa receita já está liberada na sua conta.")
        return redirect("atelier:dashboard")

    order = PurchaseOrder.objects.create(
        user=request.user,
        recipe=recipe,
        status=PurchaseOrder.Status.PENDING,
        total_amount=recipe.price,
    )

    try:
        checkout_url = create_checkout_preference(order)
    except PaymentGatewayError:
        messages.warning(
            request,
            "O checkout ainda não foi configurado. Cadastre as credenciais do Mercado Pago para ativar Pix e cartão.",
        )
        return redirect(recipe.get_absolute_url())
    except Exception as exc:
        messages.error(request, f"Não foi possível iniciar o pagamento: {exc}")
        return redirect(recipe.get_absolute_url())

    return redirect(checkout_url)


def checkout_success(request):
    return render(
        request,
        "atelier/checkout_result.html",
        {"status": "success", "gateway_enabled": mercado_pago_is_configured()},
    )


def checkout_pending(request):
    return render(
        request,
        "atelier/checkout_result.html",
        {"status": "pending", "gateway_enabled": mercado_pago_is_configured()},
    )


def checkout_failure(request):
    return render(
        request,
        "atelier/checkout_result.html",
        {"status": "failure", "gateway_enabled": mercado_pago_is_configured()},
    )


@csrf_exempt
def mercado_pago_webhook(request):
    if request.method != "POST":
        return JsonResponse({"detail": "method not allowed"}, status=405)

    payload = {}
    if request.body:
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            payload = {}

    payment_id = (
        request.GET.get("data.id")
        or payload.get("data", {}).get("id")
        or payload.get("id")
        or request.GET.get("id")
    )

    if not payment_id:
        return JsonResponse({"status": "ignored"})

    try:
        payment_data = fetch_payment_details(str(payment_id))
        order = update_order_from_payment_data(payment_data)
        if order and order.status == PurchaseOrder.Status.PAID and not order.receipt_sent_at:
            send_recipe_purchase_email(order)
    except Exception as exc:
        return JsonResponse({"status": "error", "detail": str(exc)}, status=400)

    return JsonResponse({"status": "ok"})


def recipe_download(request, slug):
    if not request.user.is_authenticated:
        return redirect(f"{reverse_lazy('login')}?next={request.path}")

    recipe = get_object_or_404(Recipe, slug=slug, is_active=True)
    order = (
        PurchaseOrder.objects.filter(
            user=request.user,
            recipe=recipe,
            status=PurchaseOrder.Status.PAID,
        )
        .order_by("-created_at")
        .first()
    )

    if not order:
        raise Http404("Você ainda não possui acesso a esta receita.")
    if not recipe.pdf_file:
        raise Http404("O PDF desta receita ainda não foi cadastrado.")

    return FileResponse(recipe.pdf_file.open("rb"), as_attachment=True, filename=recipe.pdf_file.name.split("/")[-1])
