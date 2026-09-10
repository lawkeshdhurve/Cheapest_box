"""
Box Selection Service

This module contains the core business logic for recommending the most suitable
shipping box for a given order.

Algorithm
---------
Given an order with N line items (each with a product and quantity):

1. Expand line items → a flat list of all individual product units.
   e.g. 2× Product A becomes [ProductA, ProductA].

2. For each available Box (ordered by cost ASC, then volume ASC):

   a. Weight check
      total_weight ≤ box.max_weight
      If this fails → skip this box immediately.

   b. Individual dimensional fit check
      Every product unit must be able to physically fit inside the box.
      We test all 6 rotations (permutations of L, W, H) of the product
      against the box's internal dimensions.
      If any product unit cannot fit in any orientation → skip this box.

   c. Volume check with packing efficiency heuristic
      Real-world packing never achieves 100% volumetric efficiency.
      We apply an 80% packing efficiency factor:
        sum(product_volume × qty) ≤ box.internal_volume × PACKING_EFFICIENCY
      If the total volume exceeds this threshold → skip this box.

3. The first box that passes all three checks is returned as the recommendation
   (since boxes are pre-ordered by cost → we always get the cheapest valid box).

4. If no box passes all checks, return None with a descriptive reason.

Design rationale
----------------
Full 3-D bin packing (deciding *how* to arrange N items inside a container) is
NP-hard. For an ecommerce warehouse context the simplified heuristic above is
both fast and sufficiently accurate. The 80% efficiency factor provides a
practical safety margin for irregular shapes, padding, and packing materials.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import Box, Order


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Fraction of the box's internal volume that is assumed usable for products.
#: The remaining 20% accounts for packing material, irregular shapes, etc.
PACKING_EFFICIENCY = 0.80


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------


@dataclass
class RecommendationResult:
    """Result returned by :func:`recommend_box`."""

    success: bool
    box: Optional[Box]
    reason: str
    total_weight: float
    total_volume: float
    usable_volume: Optional[float] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def recommend_box(order: Order) -> RecommendationResult:
    """
    Recommend the cheapest suitable shipping box for *order*.

    Parameters
    ----------
    order:
        A fully saved :class:`~shipping.models.Order` instance whose
        ``items`` relation is populated.

    Returns
    -------
    RecommendationResult
        Indicates success/failure, the recommended box (if any), and a
        human-readable explanation.
    """
    # ------------------------------------------------------------------
    # 1. Collect all individual product units for this order
    # ------------------------------------------------------------------
    items = list(order.items.select_related("product").all())

    if not items:
        return RecommendationResult(
            success=False,
            box=None,
            reason="The order has no items.",
            total_weight=0.0,
            total_volume=0.0,
        )

    # Expand into a flat list: 2× ProductA → [ProductA, ProductA]
    all_units = []
    for item in items:
        all_units.extend([item.product] * item.quantity)

    total_weight = sum(float(p.weight) for p in all_units)
    total_volume = sum(p.volume for p in all_units)

    # ------------------------------------------------------------------
    # 2. Iterate over available boxes (cheapest first)
    # ------------------------------------------------------------------
    boxes = Box.objects.order_by("cost", "internal_length", "internal_width", "internal_height")

    if not boxes.exists():
        return RecommendationResult(
            success=False,
            box=None,
            reason="No boxes are configured in the system.",
            total_weight=total_weight,
            total_volume=total_volume,
        )

    # Track why no box was found (for a helpful error message)
    any_box_passed_weight = False
    any_box_passed_dims = False

    for box in boxes:
        # --- Check a: weight ------------------------------------------
        if total_weight > float(box.max_weight):
            continue
        any_box_passed_weight = True

        # --- Check b: individual dimensional fit ----------------------
        if not all(unit.fits_in_box(box) for unit in all_units):
            continue
        any_box_passed_dims = True

        # --- Check c: volume with packing efficiency ------------------
        usable_volume = box.internal_volume * PACKING_EFFICIENCY
        if total_volume > usable_volume:
            continue

        # All checks passed — this is the cheapest suitable box
        return RecommendationResult(
            success=True,
            box=box,
            reason=(
                f"'{box.name}' is the cheapest box that fits all products "
                f"(weight: {total_weight:.3f} kg / {box.max_weight} kg, "
                f"volume: {total_volume:.2f} cm³ / {usable_volume:.2f} cm³ usable)."
            ),
            total_weight=total_weight,
            total_volume=total_volume,
            usable_volume=usable_volume,
        )

    # ------------------------------------------------------------------
    # 3. No box found — build a descriptive reason
    # ------------------------------------------------------------------
    if not any_box_passed_weight:
        reason = (
            f"No box can carry the total order weight of {total_weight:.3f} kg. "
            f"The heaviest available box supports "
            f"{max(float(b.max_weight) for b in boxes):.3f} kg."
        )
    elif not any_box_passed_dims:
        reason = (
            "No box is large enough to physically contain one or more products "
            "(even when rotated in all orientations)."
        )
    else:
        reason = (
            f"No box has sufficient usable volume for the total product volume "
            f"of {total_volume:.2f} cm³ "
            f"(applying {int(PACKING_EFFICIENCY * 100)}% packing efficiency)."
        )

    return RecommendationResult(
        success=False,
        box=None,
        reason=reason,
        total_weight=total_weight,
        total_volume=total_volume,
    )
