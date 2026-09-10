"""
Models for the AI-Assisted Box Selection System.

Entities:
  - Product : a sellable item with physical dimensions and weight
  - Box     : a shipping container with internal dimensions, weight capacity, and cost
  - Order   : a customer order that groups one or more products
  - OrderItem : a line item connecting an Order to a Product with a quantity
"""

from django.db import models
from django.core.validators import MinValueValidator


class Product(models.Model):
    """A sellable product with physical characteristics."""

    name = models.CharField(max_length=255)
    # Dimensions in centimetres
    length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Length in cm",
    )
    width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Width in cm",
    )
    height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Height in cm",
    )
    # Weight in kilograms
    weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Weight in kg",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.length}×{self.width}×{self.height} cm, {self.weight} kg)"

    @property
    def volume(self):
        """Volume of the product in cubic centimetres."""
        return float(self.length) * float(self.width) * float(self.height)

    def fits_in_box(self, box):
        """
        Check whether this product can physically fit inside the given box,
        allowing rotation across all 6 orientations.

        A product with dimensions (a, b, c) fits in a box with internal
        dimensions (L, W, H) if some permutation of (a, b, c) is
        element-wise ≤ (L, W, H).
        """
        from itertools import permutations

        dims = (float(self.length), float(self.width), float(self.height))
        box_dims = (
            float(box.internal_length),
            float(box.internal_width),
            float(box.internal_height),
        )

        for perm in permutations(dims):
            if all(p <= b for p, b in zip(perm, box_dims)):
                return True
        return False


class Box(models.Model):
    """A shipping box with internal volume, weight capacity, and cost."""

    name = models.CharField(max_length=255)
    # Internal dimensions in centimetres
    internal_length = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Internal length in cm",
    )
    internal_width = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Internal width in cm",
    )
    internal_height = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Internal height in cm",
    )
    # Maximum payload weight in kilograms
    max_weight = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(0.001)],
        help_text="Maximum payload weight in kg",
    )
    # Packaging cost in currency units (e.g. INR / USD)
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Cost of this box",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["cost", "name"]

    def __str__(self):
        return (
            f"{self.name} "
            f"({self.internal_length}×{self.internal_width}×{self.internal_height} cm, "
            f"max {self.max_weight} kg, cost {self.cost})"
        )

    @property
    def internal_volume(self):
        """Internal volume of the box in cubic centimetres."""
        return (
            float(self.internal_length)
            * float(self.internal_width)
            * float(self.internal_height)
        )


class Order(models.Model):
    """A customer order composed of one or more order items."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SHIPPED = "shipped", "Shipped"
        CANCELLED = "cancelled", "Cancelled"

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} ({self.status})"

    @property
    def total_weight(self):
        """Sum of weight × quantity across all items."""
        return sum(
            float(item.product.weight) * item.quantity
            for item in self.items.select_related("product").all()
        )

    @property
    def total_volume(self):
        """Sum of product volume × quantity across all items."""
        return sum(
            item.product.volume * item.quantity
            for item in self.items.select_related("product").all()
        )


class OrderItem(models.Model):
    """A single line item in an order."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_items"
    )
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )

    class Meta:
        unique_together = [("order", "product")]

    def __str__(self):
        return f"{self.quantity}× {self.product.name} in Order #{self.order_id}"
