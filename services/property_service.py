"""
Service Métier : Gestion du Patrimoine Immobilier et des Amortissements IS.
Indépendant de l'interface Streamlit (testable unitairement).
"""
import logging
from typing import Dict, Any, Optional, List
from database import query_rows, query_one, execute_write

logger = logging.getLogger("sci.services.property")

def calculate_property_depreciation(prop: Dict[str, Any]) -> Dict[str, float]:
    """
    Calcule les bases et annuités d'amortissement fiscal pour un bien selon les règles de l'IS.
    - Terrain : quote-part non amortissable (généralement 15-20%)
    - Bâti amortissable : (Prix d'acquisition + frais de notaire) - part terrain
    - Annuité bâti : base bâti / années d'amortissement (ex: 25 ans)
    - Mobilier amortissable : valeur meubles / années (ex: 5 ans)
    """
    acq_price = float(prop.get("acquisition_price", 0.0) or 0.0)
    notary = float(prop.get("notary_fees", 0.0) or 0.0)
    total_cost = acq_price + notary
    land_pct = float(prop.get("land_share_pct", 15.0) or 15.0)
    amort_years = max(1, int(prop.get("amortization_years", 25) or 25))

    # Part terrain non amortissable
    land_value = acq_price * (land_pct / 100.0)

    # Base bâti amortissable
    building_amort_base = max(0.0, total_cost - land_value)
    annual_building_amort = building_amort_base / amort_years

    # Mobilier
    furn_val = float(prop.get("furniture_value", 0.0) or 0.0)
    furn_years = max(1, int(prop.get("furniture_years", 5) or 5))
    annual_furn_amort = furn_val / furn_years if furn_val > 0 else 0.0

    total_annual_amort = annual_building_amort + annual_furn_amort

    return {
        "acq_price": acq_price,
        "notary_fees": notary,
        "total_cost": total_cost,
        "land_share_pct": land_pct,
        "land_value": land_value,
        "building_amort_base": building_amort_base,
        "amortization_years": amort_years,
        "annual_building_amort": annual_building_amort,
        "furniture_value": furn_val,
        "furniture_years": furn_years,
        "annual_furn_amort": annual_furn_amort,
        "total_annual_amort": total_annual_amort
    }

def sync_property_status(property_id: Optional[int]) -> str:
    """
    Met à jour automatiquement le statut d'un bien ("loue" ou "vacant")
    en fonction du nombre de ses locataires actifs.
    """
    if not property_id:
        return "vacant"

    active_count_row = query_one(
        "SELECT COUNT(*) as c FROM tenants WHERE property_id = ? AND is_active = 1;",
        [property_id]
    )
    active_count = active_count_row["c"] if active_count_row else 0
    new_status = "loue" if active_count > 0 else "vacant"
    
    execute_write("UPDATE properties SET status = ? WHERE id = ?;", [new_status, property_id])
    logger.info("Statut du bien ID %s synchronisé : %s (locataires actifs: %d)", property_id, new_status, active_count)
    return new_status

def get_properties_with_tenants() -> List[Dict[str, Any]]:
    """
    Retourne l'ensemble des biens avec les informations du locataire actif rattaché.
    """
    return query_rows("""
        SELECT p.*, 
               t.first_name || ' ' || t.last_name as current_tenant,
               t.rent_amount as current_rent,
               t.charges_provision as current_charges
        FROM properties p
        LEFT JOIN tenants t ON p.id = t.property_id AND t.is_active = 1
        ORDER BY p.id ASC;
    """)
