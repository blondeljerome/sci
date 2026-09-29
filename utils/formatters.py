"""
Module centralisé de formatage et d'utilitaires transverses pour la SCI.
Respecte les principes de Clean Code (DRY, robustesse, typage strict).
"""
from __future__ import annotations
from typing import Any, Optional, List, Union
from datetime import datetime, date

# -----------------------------------------------------------------------------
# Constantes Calendaires
# -----------------------------------------------------------------------------
MONTH_NAMES_FR: List[str] = [
    "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

def get_month_name(month: int) -> str:
    """Retourne le nom français d'un mois (1 = Janvier, 12 = Décembre)."""
    if 1 <= month <= 12:
        return MONTH_NAMES_FR[month - 1]
    return ""


# -----------------------------------------------------------------------------
# Formatage Monétaire & Nombres
# -----------------------------------------------------------------------------
def format_currency(
    amount: Optional[Union[float, int]],
    symbol: str = "€",
    include_sign: bool = False,
    decimals: int = 2
) -> str:
    """
    Formate un montant numérique en devise lisible avec séparateur de milliers.
    Exemples:
        format_currency(1234.5) -> "1 234.50 €"
        format_currency(-500) -> "-500.00 €"
        format_currency(150, include_sign=True) -> "+150.00 €"
        format_currency(None) -> "0.00 €"
    """
    if amount is None:
        val = 0.0
    else:
        try:
            val = float(amount)
        except (ValueError, TypeError):
            val = 0.0

    fmt = f"{{:{'+' if include_sign else ''},.{decimals}f}}"
    formatted = fmt.format(val).replace(",", " ")
    
    if symbol:
        return f"{formatted} {symbol}".strip()
    return formatted


def format_percentage(value: Optional[Union[float, int]], decimals: int = 1) -> str:
    """
    Formate un pourcentage.
    Exemple: format_percentage(15.25) -> "15.3%"
    """
    if value is None:
        return "0.0%"
    try:
        val = float(value)
        return f"{val:.{decimals}f}%"
    except (ValueError, TypeError):
        return "0.0%"


# -----------------------------------------------------------------------------
# Formatage & Parsing des Dates
# -----------------------------------------------------------------------------
def parse_date(date_val: Any) -> Optional[date]:
    """
    Parse de manière sécurisée une chaîne ISO (YYYY-MM-DD), un objet date ou datetime.
    Retourne None si la valeur est nulle ou invalide.
    """
    if not date_val:
        return None
    if isinstance(date_val, date) and not isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, datetime):
        return date_val.date()
    
    str_val = str(date_val).strip()
    if not str_val:
        return None
    
    # Prise en charge des formats YYYY-MM-DD ou YYYY-MM-DD HH:MM:SS
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(str_val[:10], fmt[: len(str_val[:10])]).date()
        except (ValueError, TypeError):
            continue
    try:
        return datetime.strptime(str_val[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def format_date_fr(date_val: Any, default: str = "-") -> str:
    """
    Formate une date au format français standard (JJ/MM/AAAA).
    Exemple: "2026-05-15" -> "15/05/2026"
    """
    d = parse_date(date_val)
    if not d:
        return default
    return d.strftime("%d/%m/%Y")


# -----------------------------------------------------------------------------
# Formatage des Tailles de Fichiers (GED)
# -----------------------------------------------------------------------------
def format_file_size(size_bytes: Optional[int]) -> str:
    """
    Formate une taille d'octets en Ko ou Mo lisible.
    Exemple: 153600 -> "150.0 Ko", 2500000 -> "2.38 Mo"
    """
    if not size_bytes or size_bytes <= 0:
        return "0 Ko"
    size_kb = size_bytes / 1024.0
    if size_kb < 1024:
        return f"{size_kb:.1f} Ko"
    return f"{size_kb / 1024.0:.2f} Mo"
