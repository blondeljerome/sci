"""
Tests unitaires pour le module centralisé utils/formatters.py
"""
from datetime import date, datetime
from utils.formatters import (
    format_currency,
    format_percentage,
    parse_date,
    format_date_fr,
    format_file_size,
    get_month_name,
    MONTH_NAMES_FR
)

def test_format_currency():
    assert format_currency(1234.5) == "1 234.50 €"
    assert format_currency(0) == "0.00 €"
    assert format_currency(None) == "0.00 €"
    assert format_currency(-500.25) == "-500.25 €"
    assert format_currency(150, include_sign=True) == "+150.00 €"
    assert format_currency(1000, decimals=0) == "1 000 €"
    print("✅ test_format_currency passé !")

def test_format_percentage():
    assert format_percentage(15.25) == "15.2%"
    assert format_percentage(100, decimals=0) == "100%"
    assert format_percentage(None) == "0.0%"
    print("✅ test_format_percentage passé !")

def test_parse_date():
    assert parse_date("2026-05-15") == date(2026, 5, 15)
    assert parse_date(date(2026, 5, 15)) == date(2026, 5, 15)
    assert parse_date(datetime(2026, 5, 15, 10, 30)) == date(2026, 5, 15)
    assert parse_date("") is None
    assert parse_date(None) is None
    assert parse_date("invalid-date") is None
    print("✅ test_parse_date passé !")

def test_format_date_fr():
    assert format_date_fr("2026-05-15") == "15/05/2026"
    assert format_date_fr(date(2026, 5, 15)) == "15/05/2026"
    assert format_date_fr(None) == "-"
    print("✅ test_format_date_fr passé !")

def test_format_file_size():
    assert format_file_size(0) == "0 Ko"
    assert format_file_size(None) == "0 Ko"
    assert format_file_size(1024) == "1.0 Ko"
    assert format_file_size(1048576) == "1.00 Mo"
    print("✅ test_format_file_size passé !")

def test_month_names():
    assert len(MONTH_NAMES_FR) == 12
    assert get_month_name(1) == "Janvier"
    assert get_month_name(12) == "Décembre"
    assert get_month_name(0) == ""
    assert get_month_name(13) == ""
    print("✅ test_month_names passé !")

if __name__ == "__main__":
    test_format_currency()
    test_format_percentage()
    test_parse_date()
    test_format_date_fr()
    test_format_file_size()
    test_month_names()
    print("\n🎉 TOUS LES TESTS DE FORMATTERS SONT VALIDÉS !")
