from django.contrib import admin

from atelier.models import PurchaseOrder, Recipe, SiteContent, Video, VideoTheme


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("brand_name", "teacher_name", "contact_email", "updated_at")


@admin.register(VideoTheme)
class VideoThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "updated_at")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "theme", "published_at", "is_featured", "is_published")
    list_filter = ("theme", "is_featured", "is_published")
    search_fields = ("title", "description", "youtube_id")


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("title", "price", "is_active", "is_featured", "updated_at")
    list_filter = ("is_active", "is_featured")
    prepopulated_fields = {"slug": ("title",)}
    search_fields = ("title", "short_description", "description")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("recipe", "user", "status", "total_amount", "created_at", "paid_at")
    list_filter = ("status",)
    search_fields = ("recipe__title", "user__username", "user__email", "external_reference")
    readonly_fields = (
        "external_reference",
        "checkout_url",
        "mercadopago_preference_id",
        "mercadopago_payment_id",
        "provider_payload",
        "paid_at",
        "receipt_sent_at",
    )
