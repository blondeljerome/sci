"""Service Métier : Gestion des Locataires, des Baux et de l'IRL.

Indépendant de l'interface Streamlit.
Conforme au Google Python Style Guide.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from database import execute_batch, execute_write, query_one, query_rows
from services.property_service import sync_property_status

logger = logging.getLogger("sci.services.tenant")


def get_irl_indices_data() -> Tuple[List[str], Dict[str, float]]:
    """Récupère les trimestres et valeurs officielles de l'IRL en base.

    Triés rigoureusement par année et trimestre décroissant.

    Returns:
        Un tuple (liste_des_trimestres, dict_trimestre_vers_valeur).
    """
    rows = query_rows(
        """
        SELECT quarter, value
        FROM irl_indices
        ORDER BY CAST(SUBSTR(quarter, 4, 4) AS INTEGER) DESC,
                 CAST(SUBSTR(quarter, 2, 1) AS INTEGER) DESC;
    """
    )
    if not rows:
        return ["T2 2026", "T1 2026", "T4 2025"], {
            "T2 2026": 148.37,
            "T1 2026": 146.60,
            "T4 2025": 145.78,
        }
    quarters = [r["quarter"] for r in rows]
    val_map = {r["quarter"]: float(r["value"]) for r in rows}
    return quarters, val_map


def delete_tenant_and_rents(
    tenant_id: int, delete_rents: bool = True
) -> Tuple[bool, int]:
    """Supprime un locataire et ses échéances de manière atomique.

    Détache également les liaisons dans property_expenses et documents,
    et synchronise le statut du lot associé (vacant si 0 locataires).

    Args:
        tenant_id: Identifiant du locataire à supprimer.
        delete_rents: Si True, supprime aussi l'ensemble de ses rent_payments.

    Returns:
        Un tuple (succes: bool, nombre_loyers_supprimes: int).
    """
    t_data = query_one("SELECT * FROM tenants WHERE id = ?;", [tenant_id])
    if not t_data:
        return False, 0

    prop_id = t_data.get("property_id")
    rents_count = 0
    stmts = []

    if delete_rents:
        r_rows = query_rows(
            "SELECT COUNT(*) as c FROM rent_payments WHERE tenant_id = ?;",
            [tenant_id],
        )
        rents_count = r_rows[0]["c"] if r_rows else 0
        stmts.append(
            ("DELETE FROM rent_payments WHERE tenant_id = ?;", [tenant_id])
        )

    # Détacher sans supprimer les charges et documents
    stmts.append(
        (
            "UPDATE property_expenses SET tenant_id = NULL "
            "WHERE tenant_id = ?;",
            [tenant_id],
        )
    )
    stmts.append(
        (
            "UPDATE documents SET tenant_id = NULL WHERE tenant_id = ?;",
            [tenant_id],
        )
    )

    # Supprimer le locataire
    stmts.append(("DELETE FROM tenants WHERE id = ?;", [tenant_id]))

    # Exécution atomique
    execute_batch(stmts)

    # Synchroniser le bien (devient vacant si 0 locataires actifs)
    if prop_id:
        sync_property_status(prop_id)

    logger.info(
        "Locataire ID %d supprimé avec succès (loyers purgés: %d)",
        tenant_id,
        rents_count,
    )
    return True, rents_count


def terminate_lease(tenant_id: int, departure_date: str) -> bool:
    """Clôture un bail actif, enregistre le départ et libère le logement.

    Args:
        tenant_id: Identifiant du locataire.
        departure_date: Date effective de départ (YYYY-MM-DD).

    Returns:
        True si l'opération a réussi, False si le locataire est introuvable.
    """
    t = query_one("SELECT property_id FROM tenants WHERE id = ?;", [tenant_id])
    if not t:
        return False

    execute_write(
        """
        UPDATE tenants SET is_active = 0, lease_end = ? WHERE id = ?;
    """,
        [departure_date, tenant_id],
    )

    if t.get("property_id"):
        sync_property_status(t["property_id"])

    logger.info(
        "Bail clôturé pour locataire ID %d au %s", tenant_id, departure_date
    )
    return True


def get_active_tenants_with_property() -> List[Dict[str, Any]]:
    """Retourne la liste des locataires actifs avec les détails de leur bien.

    Returns:
        Liste des locataires actifs ordonnés par nom de famille.
    """
    return query_rows(
        """
        SELECT t.*, p.name as property_name, p.address as prop_address,
               p.city as prop_city
        FROM tenants t
        LEFT JOIN properties p ON t.property_id = p.id
        WHERE t.is_active = 1
        ORDER BY t.last_name ASC;
    """
    )
