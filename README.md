# AI-Assisted Box Selection System

A **Django REST API** that recommends the optimal shipping box for an ecommerce order, based on product dimensions, product weight, and available box specifications.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Box Selection Algorithm](#box-selection-algorithm)
- [Running Tests](#running-tests)

---

## Overview

When a customer places an order, the warehouse team needs to quickly know which shipping box to use.  
This system models **Products** (with dimensions & weight) and **Boxes** (with internal dimensions, weight capacity & cost), and exposes a `/recommend/` endpoint that returns the cheapest box that can physically and safely contain all items in an order.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Framework | Django 4.2 |
| API | Django REST Framework 3.14 |
| Database | SQLite (dev) |
| Testing | Django `TestCase` + DRF `APITestCase` |

---

## Project Structure

```
tradexo/
├── manage.py
├── requirements.txt
├── README.md
├── AI_USAGE.md
├── TEST_OUTPUT.md
├── .gitignore
├── box_selector/
│   ├── __init__.py
│   ├── settings.py
│   └── urls.py
└── shipping/
    ├── models.py       # Product, Box, Order, OrderItem
    ├── services.py     # Box selection algorithm
    ├── serializers.py  # DRF serializers
    ├── views.py        # API ViewSets
    ├── urls.py         # Router registration
    ├── admin.py        # Django Admin config
    └── tests.py        # Full test suite
```

---

## Getting Started

### 1. Clone & set up

```bash
git clone <your-repo-url>
cd tradexo

# Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run migrations

```bash
python manage.py migrate
```

### 3. (Optional) Create an admin user

```bash
python manage.py createsuperuser
```

### 4. Start the development server

```bash
python manage.py runserver
```

The browsable DRF API will be available at **http://127.0.0.1:8000/api/**  
Django Admin at **http://127.0.0.1:8000/admin/**

---

## API Reference

### Base URL: `/api/`

#### Products

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/products/` | List all products |
| `POST` | `/api/products/` | Create a product |
| `GET` | `/api/products/{id}/` | Get product detail |
| `PUT` | `/api/products/{id}/` | Update a product |
| `PATCH` | `/api/products/{id}/` | Partially update |
| `DELETE` | `/api/products/{id}/` | Delete a product |

**Product payload:**
```json
{
  "name": "Wireless Mouse",
  "length": "12.00",
  "width": "6.00",
  "height": "4.00",
  "weight": "0.120"
}
```

#### Boxes

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/boxes/` | List all boxes |
| `POST` | `/api/boxes/` | Create a box |
| `GET` | `/api/boxes/{id}/` | Get box detail |
| `PUT` | `/api/boxes/{id}/` | Update a box |
| `DELETE` | `/api/boxes/{id}/` | Delete a box |

**Box payload:**
```json
{
  "name": "Small Parcel",
  "internal_length": "25.00",
  "internal_width": "20.00",
  "internal_height": "15.00",
  "max_weight": "5.000",
  "cost": "12.50"
}
```

#### Orders

| Method | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/orders/` | List all orders |
| `POST` | `/api/orders/` | Create an order |
| `GET` | `/api/orders/{id}/` | Get order detail |
| `PUT` | `/api/orders/{id}/` | Replace order items |
| `DELETE` | `/api/orders/{id}/` | Delete an order |
| **`GET`** | **`/api/orders/{id}/recommend/`** | **Get box recommendation** |

**Order payload:**
```json
{
  "status": "pending",
  "notes": "Handle with care",
  "items": [
    {"product": 1, "quantity": 2},
    {"product": 3, "quantity": 1}
  ]
}
```

**Recommendation response (success):**
```json
{
  "order_id": 5,
  "success": true,
  "reason": "'Medium Box' is the cheapest box that fits all products (weight: 1.120 kg / 5.000 kg, volume: 1440.00 cm³ / 6000.00 cm³ usable).",
  "total_weight_kg": 1.12,
  "total_volume_cm3": 1440.0,
  "recommended_box": {
    "id": 2,
    "name": "Medium Box",
    "internal_length": "30.00",
    "internal_width": "25.00",
    "internal_height": "20.00",
    "max_weight": "5.000",
    "cost": "8.50",
    "internal_volume": 15000.0
  }
}
```

**Recommendation response (failure — HTTP 422):**
```json
{
  "order_id": 7,
  "success": false,
  "reason": "No box can carry the total order weight of 120.000 kg. The heaviest available box supports 50.000 kg.",
  "total_weight_kg": 120.0,
  "total_volume_cm3": 8000.0,
  "recommended_box": null
}
```

---

## Box Selection Algorithm

The selection logic lives in [`shipping/services.py`](shipping/services.py).

### Steps

1. **Expand line items** — Flatten `OrderItem(product, qty)` into a list of individual product units.

2. **Weight check** — `total_weight ≤ box.max_weight`. Fails fast if exceeded.

3. **Dimensional fit check** — Each product unit must fit inside the box in at least one of its 6 rotation orientations (permutations of L, W, H). This correctly handles products like a poster tube that needs to be placed on its side.

4. **Volume check** — `sum(product volumes) ≤ box.internal_volume × 0.80`.  
   The **80% packing efficiency** factor accounts for packing materials, irregular shapes, and air gaps.

5. **Select cheapest** — Boxes are pre-sorted by `cost ASC`, so the first box that passes all three checks is always the cheapest valid option.

### Why this approach?

Full 3-D bin packing is NP-hard. The volumetric heuristic with an efficiency factor is the industry-standard approximation used by shipping calculators (FedEx, UPS, etc.) and is both fast (O(products × boxes)) and accurate enough for warehouse use.

---

## Running Tests

```bash
python manage.py test shipping --verbosity=2
```

Test categories:
- **Model unit tests** — `volume`, `internal_volume`, `fits_in_box()` with rotation
- **Service unit tests** — All algorithm paths (empty order, weight fail, dimension fail, volume fail, happy path, cheapest selection)
- **API integration tests** — Full CRUD for Products/Boxes/Orders, and all recommendation scenarios
