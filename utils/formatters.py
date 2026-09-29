"""Module centralisé de formatage et d'utilitaires transverses pour la SCI.

Respecte les principes du Google Python Style Guide et du Clean Code.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

# -----------------------------------------------------------------------------
# Constantes Calendaires
# -----------------------------------------------------------------------------
MONTH_NAMES_FR: list[str] = [
    "Janvier",
    "Février",
    "Mars",
    "Avril",
    "Mai",
    "Juin",
    "Juillet",
    "Août",
    "Septembre",
    "Octobre",
    "Novembre",
    "Décembre",
]


def get_month_name(month: int) -> str:
    """Retourne le nom français d'un mois (1 = Janvier, 12 = Décembre).

    Args:
        month: Numéro du mois (1 à 12).

    Returns:
        Nom du mois en français ou chaîne vide si invalide.
    """
    if 1 <= month <= 12:
        return MONTH_NAMES_FR[month - 1]
    return ""


# -----------------------------------------------------------------------------
# Formatage Monétaire & Nombres
# -----------------------------------------------------------------------------
def format_currency(
    amount: float | int | None,
    symbol: str = "€",
    include_sign: bool = False,
    decimals: int = 2,
) -> str:
    """Formate un montant numérique en devise lisible.

    Exemples:
        format_currency(1234.5) -> "1 234.50 €"
        format_currency(-500) -> "-500.00 €"
        format_currency(150, include_sign=True) -> "+150.00 €"
        format_currency(None) -> "0.00 €"

    Args:
        amount: Montant à formater (nombre ou None).
        symbol: Symbole monétaire à ajouter (par défaut "€").
        include_sign: Si True, force le préfixe '+' pour les positifs.
        decimals: Nombre de décimales (par défaut 2).

    Returns:
        Chaîne formatée avec séparateur de milliers.
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


def format_percentage(
    value: float | int | None, decimals: int = 1
) -> str:
    """Formate un pourcentage lisible.

    Exemple: format_percentage(15.25) -> "15.3%"

    Args:
        value: Valeur numérique du pourcentage.
        decimals: Nombre de décimales.

    Returns:
        Chaîne avec suffixe '%'.
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
def parse_date(date_val: Any) -> date | None:
    """Parse de manière sécurisée une chaîne ISO, un objet date ou datetime.

    Args:
        date_val: Valeur à parser (chaîne 'YYYY-MM-DD', date ou datetime).

    Returns:
        Objet datetime.date ou None si invalide ou vide.
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

    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(
                str_val[:10], fmt[: len(str_val[:10])]
            ).date()
        except (ValueError, TypeError):
            continue
    return None


def format_date_fr(date_val: Any, default: str = "-") -> str:
    """Formate une date au format français standard (JJ/MM/AAAA).

    Exemple: "2026-05-15" -> "15/05/2026"

    Args:
        date_val: Valeur date à formater.
        default: Valeur de remplacement si date manquante ou invalide.

    Returns:
        Chaîne au format JJ/MM/AAAA.
    """
    d = parse_date(date_val)
    if not d:
        return default
    return d.strftime("%d/%m/%Y")


# -----------------------------------------------------------------------------
# Formatage des Tailles de Fichiers (GED)
# -----------------------------------------------------------------------------
def format_file_size(size_bytes: int | None) -> str:
    """Formate une taille d'octets en Ko ou Mo lisible.

    Exemple: 153600 -> "150.0 Ko", 2500000 -> "2.38 Mo"

    Args:
        size_bytes: Taille en octets.

    Returns:
        Chaîne lisible avec unité Ko ou Mo.
    """
    if not size_bytes or size_bytes <= 0:
        return "0 Ko"
    size_kb = size_bytes / 1024.0
    if size_kb < 1024:
        return f"{size_kb:.1f} Ko"
    return f"{size_kb / 1024.0:.2f} Mo"
