from django.urls import path

from atelier import views


app_name = "atelier"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("videos/", views.VideoListView.as_view(), name="video_list"),
    path("receitas/", views.RecipeListView.as_view(), name="recipe_list"),
    path("receitas/<slug:slug>/", views.RecipeDetailView.as_view(), name="recipe_detail"),
    path("receitas/<slug:slug>/comprar/", views.recipe_checkout_start, name="recipe_checkout_start"),
    path("receitas/<slug:slug>/download/", views.recipe_download, name="recipe_download"),
    path("cadastro/", views.SignUpView.as_view(), name="signup"),
    path("minha-conta/", views.DashboardView.as_view(), name="dashboard"),
    path("checkout/sucesso/", views.checkout_success, name="checkout_success"),
    path("checkout/pendente/", views.checkout_pending, name="checkout_pending"),
    path("checkout/falha/", views.checkout_failure, name="checkout_failure"),
    path("checkout/mercado-pago/notificacoes/", views.mercado_pago_webhook, name="mercado_pago_webhook"),
]
