# Test Output

Run `run_tests.bat` (Windows) or the command below to generate test output:

```bash
python manage.py test shipping --verbosity=2
```

Then paste the terminal output below.

---

## Sample Expected Output

```
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
test_internal_volume (shipping.tests.BoxModelTests) ... ok
test_does_not_fit_in_box (shipping.tests.ProductModelTests) ... ok
test_fits_in_box_exact_size (shipping.tests.ProductModelTests) ... ok
test_fits_in_box_with_rotation (shipping.tests.ProductModelTests) ... ok
test_product_barely_does_not_fit (shipping.tests.ProductModelTests) ... ok
test_product_fits_in_larger_box (shipping.tests.ProductModelTests) ... ok
test_volume_calculation (shipping.tests.ProductModelTests) ... ok
test_create_box (shipping.tests.BoxAPITests) ... ok
test_delete_box (shipping.tests.BoxAPITests) ... ok
test_list_boxes_ordered_by_cost (shipping.tests.BoxAPITests) ... ok
test_create_order_duplicate_products_fails (shipping.tests.OrderAPITests) ... ok
test_create_order_empty_items_fails (shipping.tests.OrderAPITests) ... ok
test_create_order_with_items (shipping.tests.OrderAPITests) ... ok
test_delete_order (shipping.tests.OrderAPITests) ... ok
test_list_orders (shipping.tests.OrderAPITests) ... ok
test_retrieve_order_includes_items (shipping.tests.OrderAPITests) ... ok
test_update_order_replaces_items (shipping.tests.OrderAPITests) ... ok
test_create_product (shipping.tests.ProductAPITests) ... ok
test_create_product_missing_field (shipping.tests.ProductAPITests) ... ok
test_delete_product (shipping.tests.ProductAPITests) ... ok
test_list_products (shipping.tests.ProductAPITests) ... ok
test_retrieve_product (shipping.tests.ProductAPITests) ... ok
test_update_product (shipping.tests.ProductAPITests) ... ok
test_recommendation_404_for_unknown_order (shipping.tests.RecommendAPITests) ... ok
test_recommendation_cheapest_box_selected (shipping.tests.RecommendAPITests) ... ok
test_recommendation_no_box_found (shipping.tests.RecommendAPITests) ... ok
test_recommendation_total_weight_in_response (shipping.tests.RecommendAPITests) ... ok
test_recommendation_weight_failure (shipping.tests.RecommendAPITests) ... ok
test_successful_recommendation (shipping.tests.RecommendAPITests) ... ok
test_cheapest_valid_box_is_selected (shipping.tests.RecommendBoxServiceTests) ... ok
test_empty_order_returns_failure (shipping.tests.RecommendBoxServiceTests) ... ok
test_expensive_box_selected_when_cheap_too_small (shipping.tests.RecommendBoxServiceTests) ... ok
test_multiple_products_in_one_box (shipping.tests.RecommendBoxServiceTests) ... ok
test_no_boxes_configured_returns_failure (shipping.tests.RecommendBoxServiceTests) ... ok
test_packing_efficiency_constant (shipping.tests.RecommendBoxServiceTests) ... ok
test_product_too_large_for_all_boxes (shipping.tests.RecommendBoxServiceTests) ... ok
test_quantity_causes_weight_overflow (shipping.tests.RecommendBoxServiceTests) ... ok
test_quantity_multiplied_correctly (shipping.tests.RecommendBoxServiceTests) ... ok
test_result_contains_weight_and_volume (shipping.tests.RecommendBoxServiceTests) ... ok
test_rotated_product_fits (shipping.tests.RecommendBoxServiceTests) ... ok
test_single_product_single_box (shipping.tests.RecommendBoxServiceTests) ... ok
test_volume_exceeds_packing_limit (shipping.tests.RecommendBoxServiceTests) ... ok
test_weight_exactly_at_limit_passes (shipping.tests.RecommendBoxServiceTests) ... ok
test_weight_exceeds_all_boxes (shipping.tests.RecommendBoxServiceTests) ... ok

----------------------------------------------------------------------
Ran 44 tests in X.XXXs

OK
Destroying test database for alias 'default'...
```

> **Note**: Replace the above with actual terminal output after running the tests.
