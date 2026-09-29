"""
Service Métier : Gestion des Loyers, Échéances et Quittances.
Indépendant de Streamlit (testable unitairement et réutilisable par cron/CLI).
"""
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import date
from database import query_rows, query_one, execute_write
from utils.quittance import save_quittance_to_ged
from utils.legal_docs import save_avis_echeance_to_ged

logger = logging.getLogger("sci.services.rent")

def generate_monthly_term(month: int, year: int) -> Tuple[int, int]:
    """
    Génère l'ensemble des échéances de loyers du terme pour les locataires actifs,
    et produit automatiquement les avis d'échéance PDF archivés dans la GED.

    Returns:
        (nombre_echeances_creees, nombre_total_locataires_actifs)
    """
    active_tenants = query_rows("SELECT * FROM tenants WHERE is_active = 1 AND property_id IS NOT NULL;")
    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
    generated_count = 0

    for t in active_tenants:
        # Vérifier si l'échéance existe déjà
        existing = query_one(
            "SELECT id FROM rent_payments WHERE tenant_id = ? AND period_month = ? AND period_year = ?;",
            [t["id"], month, year]
        )
        if not existing:
            rent = float(t.get("rent_amount", 0.0) or 0.0)
            charges = float(t.get("charges_provision", 0.0) or 0.0)
            total = rent + charges
            due_date = f"{year:04d}-{month:02d}-05"

            # 1. Enregistrement de l'échéance
            new_payment_id = execute_write("""
                INSERT INTO rent_payments (
                    tenant_id, property_id, period_month, period_year,
                    rent_amount, charges_amount, total_due, due_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'en_attente');
            """, [t["id"], t["property_id"], month, year, rent, charges, total, due_date])

            # 2. Génération et archivage de l'Avis d'échéance dans la GED
            p_info = query_one("SELECT * FROM properties WHERE id = ?;", [t["property_id"]]) or {}
            save_avis_echeance_to_ged(
                sci_info, t, p_info, month, year,
                due_date, rent, charges, new_payment_id
            )
            generated_count += 1
            logger.info("Échéance créée pour locataire %s (Mois: %02d/%04d, Montant: %.2f €)", t.get("last_name"), month, year, total)

    return generated_count, len(active_tenants)

def record_full_payment(payment_id: int, payment_date: Optional[str] = None) -> Tuple[bool, str]:
    """
    Enregistre l'encaissement intégral d'un loyer, met à jour le statut en 'paye',
    puis génère et archive automatiquement la quittance de loyer PDF dans la GED.
    """
    p = query_one("""
        SELECT rp.*, 
               t.first_name, t.last_name, t.email,
               p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal
        FROM rent_payments rp
        JOIN tenants t ON rp.tenant_id = t.id
        JOIN properties p ON rp.property_id = p.id
        WHERE rp.id = ?;
    """, [payment_id])

    if not p:
        return False, "Échéance introuvable."

    p_date = payment_date or str(date.today())
    total_due = p["total_due"]

    execute_write("""
        UPDATE rent_payments 
        SET amount_paid = total_due, payment_date = ?, status = 'paye'
        WHERE id = ?;
    """, [p_date, payment_id])

    # Archivage automatique de la quittance dans la GED
    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
    tenant_info = {"id": p["tenant_id"], "first_name": p["first_name"], "last_name": p["last_name"], "email": p.get("email")}
    prop_info = {"id": p["property_id"], "name": p["property_name"], "address": p["prop_address"], "city": p["prop_city"], "postal_code": p["prop_postal"]}
    
    p_updated = dict(p)
    p_updated["amount_paid"] = total_due
    p_updated["payment_date"] = p_date
    p_updated["status"] = "paye"

    ok_ged, msg_ged, _ = save_quittance_to_ged(payment_id, sci_info, tenant_info, prop_info, p_updated)
    logger.info("Paiement enregistré pour échéance ID %d : %s", payment_id, msg_ged)
    return True, msg_ged

def get_monthly_payments(month: int, year: int) -> List[Dict[str, Any]]:
    """
    Récupère l'ensemble des échéances de paiement d'un mois avec les liens vers la GED.
    """
    return query_rows("""
        SELECT rp.*, 
               t.first_name, t.last_name, t.email,
               p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal,
               d.file_path as doc_file_path, d.filename as doc_filename, d.cloudinary_public_id as doc_public_id,
               nd.file_path as notice_file_path, nd.filename as notice_filename, nd.cloudinary_public_id as notice_public_id
        FROM rent_payments rp
        JOIN tenants t ON rp.tenant_id = t.id
        JOIN properties p ON rp.property_id = p.id
        LEFT JOIN documents d ON rp.document_id = d.id
        LEFT JOIN documents nd ON rp.notice_document_id = nd.id
        WHERE rp.period_month = ? AND rp.period_year = ?
        ORDER BY t.last_name ASC;
    """, [month, year])
