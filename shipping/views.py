"""
API views for the shipping app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Box, Order, Product
from .serializers import (
    BoxSerializer,
    OrderReadSerializer,
    OrderWriteSerializer,
    ProductSerializer,
    RecommendationSerializer,
)
from .services import recommend_box


# ---------------------------------------------------------------------------
# Product ViewSet
# ---------------------------------------------------------------------------


class ProductViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for products.

    list:   GET  /api/products/
    create: POST /api/products/
    retrieve: GET /api/products/{id}/
    update: PUT  /api/products/{id}/
    partial_update: PATCH /api/products/{id}/
    destroy: DELETE /api/products/{id}/
    """

    queryset = Product.objects.all()
    serializer_class = ProductSerializer


# ---------------------------------------------------------------------------
# Box ViewSet
# ---------------------------------------------------------------------------


class BoxViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for shipping boxes.

    list:   GET  /api/boxes/
    create: POST /api/boxes/
    retrieve: GET /api/boxes/{id}/
    update: PUT  /api/boxes/{id}/
    partial_update: PATCH /api/boxes/{id}/
    destroy: DELETE /api/boxes/{id}/
    """

    queryset = Box.objects.all()
    serializer_class = BoxSerializer


# ---------------------------------------------------------------------------
# Order ViewSet
# ---------------------------------------------------------------------------


class OrderViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for orders plus a box recommendation endpoint.

    list:    GET  /api/orders/
    create:  POST /api/orders/
    retrieve: GET /api/orders/{id}/
    update:  PUT  /api/orders/{id}/
    partial_update: PATCH /api/orders/{id}/
    destroy: DELETE /api/orders/{id}/

    recommend: GET /api/orders/{id}/recommend/
        Returns the cheapest box that fits all items in this order.
    """

    queryset = Order.objects.prefetch_related("items__product").all()

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return OrderReadSerializer
        return OrderWriteSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        # Return the full representation using the read serializer
        read_serializer = OrderReadSerializer(order, context={"request": request})
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        read_serializer = OrderReadSerializer(order, context={"request": request})
        return Response(read_serializer.data)

    @action(detail=True, methods=["get"], url_path="recommend")
    def recommend(self, request, pk=None):
        """
        GET /api/orders/{id}/recommend/

        Runs the box-selection algorithm and returns the recommended box
        along with a human-readable explanation.
        """
        order = self.get_object()
        result = recommend_box(order)

        payload = {
            "order_id": order.pk,
            "success": result.success,
            "reason": result.reason,
            "total_weight_kg": result.total_weight,
            "total_volume_cm3": result.total_volume,
            "recommended_box": result.box,
        }

        serializer = RecommendationSerializer(payload)
        http_status = status.HTTP_200_OK if result.success else status.HTTP_422_UNPROCESSABLE_ENTITY
        return Response(serializer.data, status=http_status)
