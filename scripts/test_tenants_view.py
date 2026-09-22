"""
Test d'édition et de modification de locataire
"""
from unittest.mock import patch, MagicMock
from database import query_rows, query_one, execute_write
from views.tenants import render_tenants, sync_property_status

def test_tenant_flow():
    print("--- 1. Récupération des biens disponibles ---")
    props = query_rows("SELECT id, name, status FROM properties;")
    print(f"Biens existants : {len(props)}")
    prop_id = props[0]["id"] if props else None

    initial_status = props[0]["status"] if props else None

    print("\n--- 2. Création d'un locataire test ---")
    test_id = execute_write("""
        INSERT INTO tenants (property_id, first_name, last_name, email, phone, lease_start, rent_amount, charges_provision, deposit_amount, is_active, guarantor_info, irl_reference_quarter, irl_reference_value, notes)
        VALUES (?, 'Marc', 'Dupont', 'marc.dupont@test.com', '0601020304', '2026-09-01', 400.0, 40.0, 400.0, 1, 'Parent caution', 'T3 2024', 144.51, 'Bail initial');
    """, [prop_id])
    if prop_id:
        sync_property_status(prop_id)

    inserted = query_one("SELECT * FROM tenants WHERE id = ?;", [test_id])
    print(f"Locataire créé : #{inserted['id']} {inserted['first_name']} {inserted['last_name']} (Loyer: {inserted['rent_amount']} €)")
    if prop_id:
        p_check = query_one("SELECT status FROM properties WHERE id = ?;", [prop_id])
        print(f"Statut du bien après affectation : {p_check['status']}")
        assert p_check['status'] == 'loue'

    print("\n--- 3. Modification du locataire ---")
    # Modification : loyer passe à 420 €, nouveau téléphone, ajout date de révision
    execute_write("""
        UPDATE tenants
        SET first_name = 'Marc-Antoine',
            last_name = 'Dupont-Moretti',
            email = 'marc.antoine@test.com',
            phone = '0699887766',
            rent_amount = 420.0,
            charges_provision = 45.0,
            deposit_amount = 420.0,
            notes = 'Bail modifié et révisé'
        WHERE id = ?;
    """, [test_id])

    updated = query_one("SELECT * FROM tenants WHERE id = ?;", [test_id])
    print(f"Locataire modifié : #{updated['id']} {updated['first_name']} {updated['last_name']}")
    print(f"Nouveau loyer : {updated['rent_amount']} € | Tél : {updated['phone']}")
    assert updated['first_name'] == 'Marc-Antoine'
    assert updated['rent_amount'] == 420.0

    print("\n--- 4. Test d'exécution de render_tenants() ---")
    with patch("streamlit.tabs") as mock_tabs, \
         patch("streamlit.selectbox") as mock_sb:
        mock_tabs.return_value = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        mock_sb.return_value = test_id
        render_tenants()
        print("render_tenants() s'est exécuté sans erreur avec le locataire présent !")

    print("\n--- 5. Nettoyage du locataire test via delete_tenant_and_rents ---")
    from views.tenants import delete_tenant_and_rents
    delete_tenant_and_rents(test_id, delete_rents=True)
    if prop_id:
        p_final = query_one("SELECT status FROM properties WHERE id = ?;", [prop_id])
        print(f"Statut du bien après suppression : {p_final['status']}")
        assert p_final['status'] == initial_status

    print("\n✅ TOUS LES TESTS LOCATAIRES SONT PASSÉS AVEC SUCCÈS !")

if __name__ == "__main__":
    test_tenant_flow()
