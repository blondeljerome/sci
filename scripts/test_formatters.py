"""Tests unitaires pour le module centralisé utils/formatters.py."""

import unittest
from datetime import date, datetime

from utils.formatters import (
    MONTH_NAMES_FR,
    format_currency,
    format_date_fr,
    format_file_size,
    format_percentage,
    get_month_name,
    parse_date,
)


class TestFormatters(unittest.TestCase):
    """Banc de tests unitaires pour les formateurs d'affichage."""

    def test_format_currency(self) -> None:
        """Vérifie le formatage monétaire des devises."""
        self.assertEqual(format_currency(1234.5), "1 234.50 €")
        self.assertEqual(format_currency(0), "0.00 €")
        self.assertEqual(format_currency(None), "0.00 €")
        self.assertEqual(format_currency(-500.25), "-500.25 €")
        self.assertEqual(format_currency(150, include_sign=True), "+150.00 €")
        self.assertEqual(format_currency(1000, decimals=0), "1 000 €")

    def test_format_percentage(self) -> None:
        """Vérifie le formatage des pourcentages."""
        self.assertEqual(format_percentage(15.25), "15.2%")
        self.assertEqual(format_percentage(100, decimals=0), "100%")
        self.assertEqual(format_percentage(None), "0.0%")

    def test_parse_date(self) -> None:
        """Vérifie le parsing des dates et timestamps."""
        self.assertEqual(parse_date("2026-05-15"), date(2026, 5, 15))
        self.assertEqual(parse_date(date(2026, 5, 15)), date(2026, 5, 15))
        self.assertEqual(
            parse_date(datetime(2026, 5, 15, 10, 30)), date(2026, 5, 15)
        )
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date(None))
        self.assertIsNone(parse_date("invalid-date"))

    def test_format_date_fr(self) -> None:
        """Vérifie la mise en forme française des dates."""
        self.assertEqual(format_date_fr("2026-05-15"), "15/05/2026")
        self.assertEqual(format_date_fr(date(2026, 5, 15)), "15/05/2026")
        self.assertEqual(format_date_fr(None), "-")

    def test_format_file_size(self) -> None:
        """Vérifie le formatage de la taille des fichiers."""
        self.assertEqual(format_file_size(0), "0 Ko")
        self.assertEqual(format_file_size(None), "0 Ko")
        self.assertEqual(format_file_size(1024), "1.0 Ko")
        self.assertEqual(format_file_size(1048576), "1.00 Mo")

    def test_month_names(self) -> None:
        """Vérifie la correspondance des mois en français."""
        self.assertEqual(len(MONTH_NAMES_FR), 12)
        self.assertEqual(get_month_name(1), "Janvier")
        self.assertEqual(get_month_name(12), "Décembre")
        self.assertEqual(get_month_name(0), "")
        self.assertEqual(get_month_name(13), "")


if __name__ == "__main__":
    unittest.main()
