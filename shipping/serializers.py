"""
DRF Serializers for the shipping app.
"""

from rest_framework import serializers
from .models import Box, Order, OrderItem, Product


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------


class ProductSerializer(serializers.ModelSerializer):
    volume = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "length",
            "width",
            "height",
            "weight",
            "volume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "volume", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Box
# ---------------------------------------------------------------------------


class BoxSerializer(serializers.ModelSerializer):
    internal_volume = serializers.ReadOnlyField()

    class Meta:
        model = Box
        fields = [
            "id",
            "name",
            "internal_length",
            "internal_width",
            "internal_height",
            "max_weight",
            "cost",
            "internal_volume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "internal_volume", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# OrderItem (nested)
# ---------------------------------------------------------------------------


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")

    class Meta:
        model = OrderItem
        fields = ["id", "product", "product_name", "quantity"]


class OrderItemWriteSerializer(serializers.ModelSerializer):
    """Used when creating/updating items within an order."""

    class Meta:
        model = OrderItem
        fields = ["product", "quantity"]


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


class OrderReadSerializer(serializers.ModelSerializer):
    """Serializer for reading order data (includes nested items)."""

    items = OrderItemSerializer(many=True, read_only=True)
    total_weight = serializers.ReadOnlyField()
    total_volume = serializers.ReadOnlyField()

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "notes",
            "items",
            "total_weight",
            "total_volume",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class OrderWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating/updating an order with its items in one request.

    Expected payload::

        {
            "status": "pending",
            "notes": "fragile",
            "items": [
                {"product": 1, "quantity": 2},
                {"product": 3, "quantity": 1}
            ]
        }
    """

    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "status", "notes", "items"]
        read_only_fields = ["id"]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError(
                "An order must contain at least one item."
            )
        # Check for duplicate products in the same order
        product_ids = [item["product"].id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise serializers.ValidationError(
                "Duplicate products found. Increase the quantity instead."
            )
        return value

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        order = Order.objects.create(**validated_data)
        for item_data in items_data:
            OrderItem.objects.create(order=order, **item_data)
        return order

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        # Update order fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            # Replace all existing items
            instance.items.all().delete()
            for item_data in items_data:
                OrderItem.objects.create(order=instance, **item_data)

        return instance


# ---------------------------------------------------------------------------
# Recommendation response
# ---------------------------------------------------------------------------


class RecommendationSerializer(serializers.Serializer):
    """Read-only serializer representing a box recommendation response."""

    order_id = serializers.IntegerField()
    success = serializers.BooleanField()
    reason = serializers.CharField()
    total_weight_kg = serializers.FloatField()
    total_volume_cm3 = serializers.FloatField()
    recommended_box = BoxSerializer(allow_null=True)
