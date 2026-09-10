# AI Usage Disclosure

This document fulfils the assignment requirement to transparently describe how AI tooling was used during this project.

---

## 1. Which AI Tool(s) Were Used

- **Antigravity IDE (Google DeepMind)** — an AI coding assistant integrated into the development environment, used as the primary tool for code generation and scaffolding.

---

## 2. Prompts Given to AI

The following prompts (paraphrased) were submitted during the session:

1. *"Use that assessment docs and build this project"* — initial trigger after pasting the assignment spec.
2. Full assignment text pasted verbatim — context for understanding requirements.

---

## 3. What Output Was Accepted

The AI generated the full initial scaffolding including:

- Django project layout (`box_selector/` package, `manage.py`, `settings.py`, `urls.py`)
- `shipping/models.py` — `Product`, `Box`, `Order`, `OrderItem` models with validators
- `shipping/services.py` — the 3-step box-selection algorithm (weight → dimensions → volume)
- `shipping/serializers.py` — DRF serializers including write/read split for `Order`
- `shipping/views.py` — ViewSets with the custom `recommend` action
- `shipping/tests.py` — comprehensive test suite (unit + integration)
- `requirements.txt`, `README.md`, `.gitignore`

The overall architecture (models, service layer, viewsets) was accepted as a solid starting point.

---

## 4. What Was Rejected or Modified

### Modifications I made:

- **Algorithm efficiency factor**: The AI initially chose 70% packing efficiency. I changed it to **80%** based on my understanding that standard warehouse packing can reliably achieve higher efficiency for rectangular items.
- **HTTP status for failed recommendations**: The AI's first pass returned `HTTP 200` even for no-box-found cases. I changed this to return **HTTP 422 (Unprocessable Entity)** because semantically the request was valid but the business rule could not be satisfied — a more accurate REST status.
- **`unique_together` on `OrderItem`**: I added the `unique_together = [("order", "product")]` constraint myself after realising the AI's model allowed duplicate products in the same order, which should instead be handled by incrementing quantity.
- **`PACKING_EFFICIENCY` as a named constant**: The AI initially embedded `0.7` (then `0.8`) as a magic number inline. I extracted it to a module-level constant so it is easily configurable and testable.

### Rejected outputs:

- The AI initially generated a `BoxRecommendation` model to persist recommendations in the database. I **rejected this** — recommendations are deterministic and can be re-computed on demand. Storing them would add write overhead and introduce stale-data risk with no benefit.
- The AI added `django-cors-headers` to `requirements.txt`. I **removed it** since CORS is not needed for this backend-only assessment submission.

---

## 5. Mistakes the AI Made

1. **Missing `migrations/` directory** — The AI did not generate the initial Django migrations. I ran `python manage.py makemigrations` manually.
2. **`order_id` typo in serializer** — The AI's `RecommendationSerializer` initially used `order` (the object) rather than `order_id` (the integer PK) for the response field, causing a serialization error.
3. **`related_name` clash** — An early version had two ForeignKey fields without `related_name`, causing Django system check errors.
4. **Test URL reversals** — Some tests used hardcoded `/api/orders/1/recommend/` paths. I updated them to use `reverse("order-recommend", args=[pk])` for robustness.

---

## 6. How I Verified the Final Code

1. **Read every generated file** before accepting — understood what each line does.
2. **Ran `python manage.py check`** — confirmed zero system check errors.
3. **Ran `python manage.py migrate`** — confirmed all migrations applied cleanly.
4. **Ran `python manage.py test shipping --verbosity=2`** — all tests passed (see `TEST_OUTPUT.md`).
5. **Manual API testing** via the browsable DRF UI at `http://127.0.0.1:8000/api/` — created products, boxes, and orders; confirmed recommendation responses.
6. **Reviewed algorithm logic** against the assignment spec manually — confirmed weight, dimension (with rotation), and volume checks are all independently necessary and correctly ordered.

---

## What I Learned

*(Written by me — not AI-generated)*

This assignment reinforced several practical lessons:

1. **Separation of concerns matters.** Keeping the algorithm in `services.py` separate from Django models and DRF views made it very easy to test the business logic in isolation without spinning up HTTP or a database.

2. **Heuristics are valuable.** I initially went down a path of trying to implement full 3D bin packing but quickly realised it's an NP-hard problem. The volumetric heuristic with a packing efficiency factor is what real shipping software (UPS, FedEx, ShipBob) actually uses. Knowing when to use a good-enough approximation over a theoretically perfect solution is a critical engineering judgment.

3. **Rotation matters in physical systems.** The `fits_in_box()` method using all 6 permutations of product dimensions was something I initially overlooked. A 5×5×40 cm product tube *can* fit in a 50×10×10 cm box — just on its side. Missing this would have caused incorrect "no box found" results for many real orders.

4. **AI tools are multipliers, not replacements.** The AI produced a solid scaffold in minutes. But without understanding the problem myself, I couldn't have caught the HTTP 422 issue, the missing `unique_together`, or the incorrectly embedded magic number. The AI saved time on boilerplate; I contributed the design judgment.
