"""
Test suite for the AI-Assisted Box Selection System.

Coverage
--------
Unit tests:
  - Product.fits_in_box() — all orientations
  - Product.volume property
  - Box.internal_volume property
  - services.recommend_box() — all algorithm paths

Integration tests (via DRF APIClient):
  - ProductViewSet CRUD
  - BoxViewSet CRUD
  - OrderViewSet CRUD (with nested items)
  - GET /api/orders/{id}/recommend/ — happy path and all failure modes

Run with:
    python manage.py test shipping
"""

from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Box, Order, OrderItem, Product
from .services import recommend_box, PACKING_EFFICIENCY


# ===========================================================================
# Helpers
# ===========================================================================


def make_product(
    name="Widget",
    length="10.00",
    width="10.00",
    height="10.00",
    weight="1.000",
):
    return Product.objects.create(
        name=name,
        length=Decimal(length),
        width=Decimal(width),
        height=Decimal(height),
        weight=Decimal(weight),
    )


def make_box(
    name="Box S",
    il="20.00",
    iw="20.00",
    ih="20.00",
    max_weight="10.000",
    cost="5.00",
):
    return Box.objects.create(
        name=name,
        internal_length=Decimal(il),
        internal_width=Decimal(iw),
        internal_height=Decimal(ih),
        max_weight=Decimal(max_weight),
        cost=Decimal(cost),
    )


def make_order(*items):
    """
    Create an order with items specified as (product, qty) tuples.
    """
    order = Order.objects.create()
    for product, qty in items:
        OrderItem.objects.create(order=order, product=product, quantity=qty)
    return order


# ===========================================================================
# Unit Tests — Model properties
# ===========================================================================


class ProductModelTests(TestCase):

    def test_volume_calculation(self):
        """Product volume = length × width × height."""
        p = make_product(length="10.00", width="5.00", height="2.00")
        self.assertAlmostEqual(p.volume, 100.0)

    def test_fits_in_box_exact_size(self):
        """A product that exactly matches box dimensions should fit."""
        p = make_product(length="20.00", width="15.00", height="10.00")
        box = make_box(il="20.00", iw="15.00", ih="10.00")
        self.assertTrue(p.fits_in_box(box))

    def test_fits_in_box_with_rotation(self):
        """A product fits if any of its 6 rotations fits the box."""
        # Product: 30 × 5 × 5 — tall and thin
        p = make_product(length="30.00", width="5.00", height="5.00")
        # Box: 10 × 10 × 30 — needs rotation to fit the 30 cm side vertically
        box = make_box(il="10.00", iw="10.00", ih="30.00")
        self.assertTrue(p.fits_in_box(box))

    def test_does_not_fit_in_box(self):
        """A product larger than a box in all orientations should not fit."""
        p = make_product(length="50.00", width="50.00", height="50.00")
        box = make_box(il="20.00", iw="20.00", ih="20.00")
        self.assertFalse(p.fits_in_box(box))

    def test_product_fits_in_larger_box(self):
        """Product obviously fits in a much larger box."""
        p = make_product(length="5.00", width="5.00", height="5.00")
        box = make_box(il="100.00", iw="100.00", ih="100.00")
        self.assertTrue(p.fits_in_box(box))

    def test_product_barely_does_not_fit(self):
        """Product 1 cm too large should not fit."""
        p = make_product(length="21.00", width="20.00", height="20.00")
        box = make_box(il="20.00", iw="20.00", ih="20.00")
        self.assertFalse(p.fits_in_box(box))


class BoxModelTests(TestCase):

    def test_internal_volume(self):
        """Box internal volume = L × W × H."""
        box = make_box(il="30.00", iw="20.00", ih="10.00")
        self.assertAlmostEqual(box.internal_volume, 6000.0)


# ===========================================================================
# Unit Tests — services.recommend_box
# ===========================================================================


class RecommendBoxServiceTests(TestCase):

    # -----------------------------------------------------------------------
    # Edge / error cases
    # -----------------------------------------------------------------------

    def test_empty_order_returns_failure(self):
        """An order with no items should return success=False."""
        order = Order.objects.create()
        result = recommend_box(order)
        self.assertFalse(result.success)
        self.assertIsNone(result.box)
        self.assertIn("no items", result.reason.lower())

    def test_no_boxes_configured_returns_failure(self):
        """If no boxes exist in the database, return failure."""
        p = make_product()
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertFalse(result.success)
        self.assertIsNone(result.box)
        self.assertIn("no boxes", result.reason.lower())

    # -----------------------------------------------------------------------
    # Weight failures
    # -----------------------------------------------------------------------

    def test_weight_exceeds_all_boxes(self):
        """Total order weight > all box max_weights → failure."""
        p = make_product(weight="100.000")
        make_box(max_weight="50.000")
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertFalse(result.success)
        self.assertIn("weight", result.reason.lower())

    def test_weight_exactly_at_limit_passes(self):
        """Total weight == box.max_weight should pass the weight check."""
        p = make_product(weight="10.000")
        make_box(il="100.00", iw="100.00", ih="100.00", max_weight="10.000", cost="5.00")
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)

    # -----------------------------------------------------------------------
    # Dimensional failures
    # -----------------------------------------------------------------------

    def test_product_too_large_for_all_boxes(self):
        """Product won't fit in any box even with rotation → failure."""
        p = make_product(length="100.00", width="100.00", height="100.00")
        make_box(il="20.00", iw="20.00", ih="20.00", max_weight="9999.000")
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertFalse(result.success)
        self.assertIn("large enough", result.reason.lower())

    def test_rotated_product_fits(self):
        """Product fits only when rotated — should still succeed."""
        # Product: 5 × 5 × 40 — long and thin
        p = make_product(length="5.00", width="5.00", height="40.00")
        # Box: 50 × 10 × 10 — wide but shallow; needs product on its side
        box = make_box(il="50.00", iw="10.00", ih="10.00", max_weight="50.000", cost="5.00")
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertEqual(result.box.pk, box.pk)

    # -----------------------------------------------------------------------
    # Volume failures
    # -----------------------------------------------------------------------

    def test_volume_exceeds_packing_limit(self):
        """
        Products whose combined volume exceeds PACKING_EFFICIENCY × box volume
        should not be packed into that box.
        """
        # Box: 10 × 10 × 10 = 1000 cm³, usable = 800 cm³
        box = make_box(il="10.00", iw="10.00", ih="10.00", max_weight="9999.000", cost="5.00")
        # Product: 9 × 9 × 9 = 729 cm³ — fits dimensionally and individually
        # But 2 units = 1458 cm³ > 800 cm³ usable
        p = make_product(length="9.00", width="9.00", height="9.00", weight="0.100")
        order = make_order((p, 2))
        result = recommend_box(order)
        self.assertFalse(result.success)

    # -----------------------------------------------------------------------
    # Happy-path: single product
    # -----------------------------------------------------------------------

    def test_single_product_single_box(self):
        """Basic happy path: one product, one suitable box."""
        p = make_product(length="10.00", width="10.00", height="10.00", weight="1.000")
        box = make_box(il="20.00", iw="20.00", ih="20.00", max_weight="10.000", cost="5.00")
        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertEqual(result.box.pk, box.pk)
        self.assertAlmostEqual(result.total_weight, 1.0)
        self.assertAlmostEqual(result.total_volume, 1000.0)

    # -----------------------------------------------------------------------
    # Happy-path: cheapest box selected
    # -----------------------------------------------------------------------

    def test_cheapest_valid_box_is_selected(self):
        """
        When multiple boxes fit, the cheapest one must be recommended.
        """
        p = make_product(length="5.00", width="5.00", height="5.00", weight="0.500")

        expensive = make_box(
            name="Expensive Large",
            il="50.00", iw="50.00", ih="50.00",
            max_weight="50.000",
            cost="50.00",
        )
        cheap = make_box(
            name="Cheap Small",
            il="10.00", iw="10.00", ih="10.00",
            max_weight="5.000",
            cost="2.00",
        )

        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)
        # Cheapest that fits should win
        self.assertEqual(result.box.pk, cheap.pk)

    def test_expensive_box_selected_when_cheap_too_small(self):
        """
        If the cheap box is too small, the next valid (more expensive) box is chosen.
        """
        p = make_product(length="30.00", width="30.00", height="30.00", weight="1.000")

        make_box(name="Too Small", il="10.00", iw="10.00", ih="10.00",
                 max_weight="5.000", cost="1.00")
        right_box = make_box(name="Correct Size", il="40.00", iw="40.00", ih="40.00",
                             max_weight="5.000", cost="10.00")

        order = make_order((p, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertEqual(result.box.pk, right_box.pk)

    # -----------------------------------------------------------------------
    # Happy-path: multiple products
    # -----------------------------------------------------------------------

    def test_multiple_products_in_one_box(self):
        """Multiple products with combined weight/volume within box limits."""
        p1 = make_product(name="A", length="5.00", width="5.00", height="5.00", weight="0.500")
        p2 = make_product(name="B", length="8.00", width="8.00", height="8.00", weight="1.000")

        # Box big enough for both: 20×20×20 = 8000 cm³, usable = 6400 cm³
        # p1 vol = 125, p2 vol = 512, total = 637 cm³ — well within limit
        box = make_box(il="20.00", iw="20.00", ih="20.00", max_weight="5.000", cost="5.00")

        order = make_order((p1, 1), (p2, 1))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertEqual(result.box.pk, box.pk)
        self.assertAlmostEqual(result.total_weight, 1.5)

    def test_quantity_multiplied_correctly(self):
        """Ordering 5 units of a product should multiply weight and volume by 5."""
        p = make_product(length="5.00", width="5.00", height="5.00", weight="1.000")
        # 5 units: total weight = 5 kg, total volume = 625 cm³
        # Box: 20×20×20 = 8000 cm³ usable 6400, max weight 6 kg
        make_box(il="20.00", iw="20.00", ih="20.00", max_weight="6.000", cost="5.00")

        order = make_order((p, 5))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.total_weight, 5.0)
        self.assertAlmostEqual(result.total_volume, 625.0)

    def test_quantity_causes_weight_overflow(self):
        """Ordering too many units should fail the weight check."""
        p = make_product(length="5.00", width="5.00", height="5.00", weight="2.000")
        make_box(il="100.00", iw="100.00", ih="100.00", max_weight="5.000", cost="5.00")

        order = make_order((p, 3))  # 6 kg > 5 kg max
        result = recommend_box(order)
        self.assertFalse(result.success)
        self.assertIn("weight", result.reason.lower())

    # -----------------------------------------------------------------------
    # Result fields
    # -----------------------------------------------------------------------

    def test_result_contains_weight_and_volume(self):
        """Successful result must carry correct total_weight and total_volume."""
        p = make_product(length="10.00", width="10.00", height="10.00", weight="2.000")
        make_box(il="20.00", iw="20.00", ih="20.00", max_weight="10.000", cost="5.00")
        order = make_order((p, 2))
        result = recommend_box(order)
        self.assertTrue(result.success)
        self.assertAlmostEqual(result.total_weight, 4.0)
        self.assertAlmostEqual(result.total_volume, 2000.0)  # 2 × 1000 cm³

    def test_packing_efficiency_constant(self):
        """PACKING_EFFICIENCY must be between 0 and 1."""
        self.assertGreater(PACKING_EFFICIENCY, 0)
        self.assertLessEqual(PACKING_EFFICIENCY, 1)


# ===========================================================================
# Integration Tests — REST API
# ===========================================================================


class ProductAPITests(APITestCase):

    def test_create_product(self):
        url = reverse("product-list")
        data = {
            "name": "Laptop",
            "length": "35.00",
            "width": "25.00",
            "height": "2.50",
            "weight": "2.000",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Laptop")
        self.assertIn("volume", response.data)

    def test_list_products(self):
        make_product(name="P1")
        make_product(name="P2")
        url = reverse("product-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_retrieve_product(self):
        p = make_product(name="Headphones")
        url = reverse("product-detail", args=[p.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Headphones")

    def test_update_product(self):
        p = make_product(name="Old Name")
        url = reverse("product-detail", args=[p.pk])
        response = self.client.patch(url, {"name": "New Name"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "New Name")

    def test_delete_product(self):
        p = make_product()
        url = reverse("product-detail", args=[p.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=p.pk).exists())

    def test_create_product_missing_field(self):
        url = reverse("product-list")
        response = self.client.post(url, {"name": "Incomplete"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BoxAPITests(APITestCase):

    def test_create_box(self):
        url = reverse("box-list")
        data = {
            "name": "Medium Box",
            "internal_length": "30.00",
            "internal_width": "25.00",
            "internal_height": "20.00",
            "max_weight": "15.000",
            "cost": "8.50",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertAlmostEqual(float(response.data["internal_volume"]), 15000.0)

    def test_list_boxes_ordered_by_cost(self):
        make_box(name="Expensive", cost="20.00")
        make_box(name="Cheap", cost="2.00")
        url = reverse("box-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [b["name"] for b in response.data["results"]]
        self.assertEqual(names[0], "Cheap")

    def test_delete_box(self):
        box = make_box()
        url = reverse("box-detail", args=[box.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class OrderAPITests(APITestCase):

    def setUp(self):
        self.product1 = make_product(name="Book")
        self.product2 = make_product(name="Pen", length="2.00", width="2.00", height="15.00", weight="0.050")

    def _order_url(self):
        return reverse("order-list")

    def test_create_order_with_items(self):
        data = {
            "items": [
                {"product": self.product1.pk, "quantity": 2},
                {"product": self.product2.pk, "quantity": 5},
            ]
        }
        response = self.client.post(self._order_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["items"]), 2)

    def test_create_order_empty_items_fails(self):
        data = {"items": []}
        response = self.client.post(self._order_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_duplicate_products_fails(self):
        data = {
            "items": [
                {"product": self.product1.pk, "quantity": 1},
                {"product": self.product1.pk, "quantity": 3},
            ]
        }
        response = self.client.post(self._order_url(), data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_orders(self):
        make_order((self.product1, 1))
        make_order((self.product2, 2))
        response = self.client.get(self._order_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_retrieve_order_includes_items(self):
        order = make_order((self.product1, 3))
        url = reverse("order-detail", args=[order.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["quantity"], 3)

    def test_update_order_replaces_items(self):
        order = make_order((self.product1, 1))
        url = reverse("order-detail", args=[order.pk])
        data = {
            "items": [{"product": self.product2.pk, "quantity": 4}]
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["quantity"], 4)

    def test_delete_order(self):
        order = make_order((self.product1, 1))
        url = reverse("order-detail", args=[order.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class RecommendAPITests(APITestCase):
    """Integration tests for GET /api/orders/{id}/recommend/"""

    def setUp(self):
        self.product = make_product(
            length="10.00", width="10.00", height="10.00", weight="1.000"
        )

    def _recommend_url(self, order_pk):
        return reverse("order-recommend", args=[order_pk])

    def test_successful_recommendation(self):
        box = make_box(il="20.00", iw="20.00", ih="20.00", max_weight="5.000", cost="5.00")
        order = make_order((self.product, 1))
        response = self.client.get(self._recommend_url(order.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["recommended_box"]["id"], box.pk)
        self.assertIn("reason", response.data)

    def test_recommendation_no_box_found(self):
        """When no box fits, API returns 422 with success=False."""
        order = make_order((self.product, 1))
        # No boxes in DB
        response = self.client.get(self._recommend_url(order.pk))
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])
        self.assertIsNone(response.data["recommended_box"])

    def test_recommendation_weight_failure(self):
        make_box(il="50.00", iw="50.00", ih="50.00", max_weight="0.500", cost="5.00")
        order = make_order((self.product, 1))  # product weighs 1 kg > 0.5 kg max
        response = self.client.get(self._recommend_url(order.pk))
        self.assertEqual(response.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)
        self.assertFalse(response.data["success"])

    def test_recommendation_cheapest_box_selected(self):
        cheap = make_box(name="Cheap", il="20.00", iw="20.00", ih="20.00",
                         max_weight="5.000", cost="3.00")
        make_box(name="Expensive", il="30.00", iw="30.00", ih="30.00",
                 max_weight="10.000", cost="15.00")
        order = make_order((self.product, 1))
        response = self.client.get(self._recommend_url(order.pk))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recommended_box"]["id"], cheap.pk)

    def test_recommendation_total_weight_in_response(self):
        make_box(il="20.00", iw="20.00", ih="20.00", max_weight="5.000", cost="5.00")
        order = make_order((self.product, 2))
        response = self.client.get(self._recommend_url(order.pk))
        self.assertTrue(response.data["success"])
        self.assertAlmostEqual(response.data["total_weight_kg"], 2.0)

    def test_recommendation_404_for_unknown_order(self):
        response = self.client.get(self._recommend_url(99999))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
