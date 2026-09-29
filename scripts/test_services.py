"""Unit tests for services (property_service, tenant_service, rent_service).

Follows Google Python Style Guide conventions.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import execute_write, query_one
from services.property_service import (
    calculate_property_depreciation,
    sync_property_status,
)
from services.rent_service import generate_monthly_term
from services.tenant_service import (
    delete_tenant_and_rents,
    get_irl_indices_data,
    terminate_lease,
)


class TestPropertyService(unittest.TestCase):
    """Tests for business logic in property_service."""

    def test_calculate_property_depreciation_standard(self) -> None:
        """Tests depreciation calculation with standard values."""
        prop = {
            "acquisition_price": 200000.0,
            "notary_fees": 15000.0,
            "furniture_value": 10000.0,
            "land_share_pct": 15.0,
            "amortization_years": 25,
            "furniture_years": 10,
        }
        res = calculate_property_depreciation(prop)

        # total_cost = 200,000 + 15,000 = 215,000
        self.assertAlmostEqual(res["total_cost"], 215000.0)
        # land_value = 15% of 200,000 = 30,000
        self.assertAlmostEqual(res["land_value"], 30000.0)
        # building_amort_base = 215,000 - 30,000 = 185,000
        self.assertAlmostEqual(res["building_amort_base"], 185000.0)
        # annual_building_amort = 185,000 / 25 = 7,400
        self.assertAlmostEqual(res["annual_building_amort"], 7400.0)
        # annual_furn_amort = 10,000 / 10 = 1,000
        self.assertAlmostEqual(res["annual_furn_amort"], 1000.0)
        # total_annual_amort = 7,400 + 1,000 = 8,400
        self.assertAlmostEqual(res["total_annual_amort"], 8400.0)

    def test_calculate_property_depreciation_defaults(self) -> None:
        """Tests calculation fallback when fields are missing or empty."""
        prop = {
            "acquisition_price": 100000.0,
        }
        res = calculate_property_depreciation(prop)
        # Default land_share_pct = 15.0 => land_value = 15,000
        self.assertAlmostEqual(res["land_value"], 15000.0)
        # Default building base = 100,000 - 15,000 = 85,000
        self.assertAlmostEqual(res["building_amort_base"], 85000.0)
        # Default amortization_years = 25 => 85,000 / 25 = 3,400
        self.assertAlmostEqual(res["annual_building_amort"], 3400.0)
        self.assertEqual(res["annual_furn_amort"], 0.0)
        self.assertAlmostEqual(res["total_annual_amort"], 3400.0)


class TestTenantAndRentServices(unittest.TestCase):
    """Integration/unit tests for tenant and rent services."""

    def test_get_irl_indices(self) -> None:
        """Tests that IRL quarters and values are returned."""
        quarters, values = get_irl_indices_data()
        self.assertIsInstance(quarters, list)
        self.assertIsInstance(values, dict)
        if quarters:
            first_q = quarters[0]
            self.assertIn(first_q, values)
            self.assertGreater(values[first_q], 0.0)

    def test_tenant_lifecycle_and_property_sync(self) -> None:
        """Tests creating a test tenant, terminating lease, and deleting."""
        # 1. Create a dummy property
        prop_id = execute_write(
            """
            INSERT INTO properties (
                name, address, postal_code, city, acquisition_price, status
            ) VALUES (?, ?, ?, ?, ?, ?);
        """,
            [
                "Test Lot Service",
                "Rue du Test",
                "75001",
                "Paris",
                100000.0,
                "vacant",
            ],
        )

        try:
            # 2. Add an active tenant
            tenant_id = execute_write(
                """
                INSERT INTO tenants (
                    first_name, last_name, property_id, rent_amount,
                    charges_provision, is_active, lease_start
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
                ["Albert", "Testeur", prop_id, 800.0, 50.0, 1, "2026-01-01"],
            )

            # Sync property status: should become 'loue'
            sync_property_status(prop_id)
            prop = query_one(
                "SELECT status FROM properties WHERE id = ?;", [prop_id]
            )
            self.assertIsNotNone(prop)
            self.assertEqual(prop.get("status"), "loue")

            # 3. Test rent generation for active tenant
            created, total = generate_monthly_term(1, 2026)
            self.assertGreaterEqual(created, 1)

            # Check rent payment row
            payment = query_one(
                """
                SELECT id, rent_amount, charges_amount, total_due, status
                FROM rent_payments
                WHERE tenant_id = ? AND period_month = 1 AND period_year = 2026;
            """,
                [tenant_id],
            )
            self.assertIsNotNone(payment)
            self.assertEqual(payment.get("total_due"), 850.0)
            self.assertEqual(payment.get("status"), "en_attente")

            # 4. Terminate lease
            success = terminate_lease(tenant_id, "2026-06-30")
            self.assertTrue(success)

            # Property should be 'vacant' again
            prop_after_term = query_one(
                "SELECT status FROM properties WHERE id = ?;", [prop_id]
            )
            self.assertIsNotNone(prop_after_term)
            self.assertEqual(prop_after_term.get("status"), "vacant")

            # 5. Delete tenant and associated rents
            del_ok, del_count = delete_tenant_and_rents(
                tenant_id, delete_rents=True
            )
            self.assertTrue(del_ok)
            self.assertGreaterEqual(del_count, 1)

            # Verify tenant is gone
            tenant_check = query_one(
                "SELECT id FROM tenants WHERE id = ?;", [tenant_id]
            )
            self.assertIsNone(tenant_check)

        finally:
            # Cleanup test property and any remaining data
            execute_write(
                "DELETE FROM rent_payments WHERE property_id = ?;", [prop_id]
            )
            execute_write(
                "DELETE FROM tenants WHERE property_id = ?;", [prop_id]
            )
            execute_write("DELETE FROM properties WHERE id = ?;", [prop_id])


if __name__ == "__main__":
    unittest.main()
