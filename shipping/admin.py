"""Django admin configuration for shipping models."""

from django.contrib import admin

from .models import Box, Order, OrderItem, Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "length", "width", "height", "weight", "created_at"]
    search_fields = ["name"]
    ordering = ["name"]


@admin.register(Box)
class BoxAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "internal_length",
        "internal_width",
        "internal_height",
        "max_weight",
        "cost",
        "created_at",
    ]
    search_fields = ["name"]
    ordering = ["cost"]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ["product"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "status", "created_at", "updated_at"]
    list_filter = ["status"]
    inlines = [OrderItemInline]
    ordering = ["-created_at"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["id", "order", "product", "quantity"]
    list_select_related = ["order", "product"]
