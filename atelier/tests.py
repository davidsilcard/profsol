from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from atelier.models import PurchaseOrder, Recipe


class PublicPagesTests(TestCase):
    def test_home_page_loads(self):
        response = self.client.get(reverse("atelier:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QR code para abrir o site da professora Sol")

    def test_home_shows_six_most_recent_recipes(self):
        for index in range(7):
            Recipe.objects.create(
                title=f"Receita {index}",
                short_description="Descricao curta",
                description="Descricao longa",
                price="19.90",
            )

        response = self.client.get(reverse("atelier:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Receita 6")
        self.assertContains(response, "Receita 1")
        self.assertNotContains(response, "Receita 0")

    def test_recipe_list_loads(self):
        Recipe.objects.create(
            title="Cachecol Ponto Folha",
            short_description="Receita em PDF para um cachecol delicado.",
            description="Descrição longa.",
            price="29.90",
        )
        response = self.client.get(reverse("atelier:recipe_list"))
        self.assertContains(response, "Cachecol Ponto Folha")


class RecipeAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cliente", password="senha12345", email="cliente@example.com")
        self.recipe = Recipe.objects.create(
            title="Touca Tramada",
            short_description="Receita para touca em tricô.",
            description="Descrição longa.",
            price="19.90",
        )

    def test_download_requires_login(self):
        response = self.client.get(reverse("atelier:recipe_download", args=[self.recipe.slug]))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_shows_paid_order(self):
        PurchaseOrder.objects.create(
            user=self.user,
            recipe=self.recipe,
            status=PurchaseOrder.Status.PAID,
            total_amount="19.90",
        )
        client = Client()
        client.login(username="cliente", password="senha12345")
        response = client.get(reverse("atelier:dashboard"))
        self.assertContains(response, "Touca Tramada")
