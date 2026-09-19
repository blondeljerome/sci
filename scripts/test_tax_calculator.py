"""
Script de test automatisé pour le moteur comptable et fiscal utils/tax_calculator.py
"""
import sys
from utils.tax_calculator import compute_income_statement, compute_balance_sheet, compute_depreciation_schedule, get_cerfa_codes

def test_calculations():
    print("--- Test 1 : Calcul des Amortissements 2026 ---")
    sched_2026 = compute_depreciation_schedule(2026)
    print(f"Nombre de biens analysés : {len(sched_2026)}")
    for s in sched_2026:
        print(f"Bien : {s['name']}")
        print(f"  Coût total : {s['total_cost']:,.2f} € | Part terrain : {s['land_value']:,.2f} €")
        print(f"  Base bâti : {s['building_base']:,.2f} € | Annuité pleine : {s['annual_building_full']:,.2f} €")
        print(f"  Dotation 2026 : {s['dotation_total']:,.2f} € (Prorata: {s['prorata_first_year_pct']:.1f}%)")
        print(f"  Cumul amortissements : {s['cumul_amort_total']:,.2f} € | VNC : {s['vnc_total']:,.2f} €")

    print("\n--- Test 2 : Compte de Résultat 2026 ---")
    inc_2026 = compute_income_statement(2026)
    print(f"Produits bruts : {inc_2026['gross_rental_income']:,.2f} €")
    print(f"Charges d'exploitation : {inc_2026['total_operating_charges']:,.2f} €")
    print(f"DAA : {inc_2026['total_daa']:,.2f} €")
    print(f"Résultat d'exploitation : {inc_2026['operating_result']:,.2f} €")
    print(f"Charges financières : {inc_2026['total_financial_charges']:,.2f} €")
    print(f"RCAI : {inc_2026['rcai']:,.2f} €")
    print(f"IS calculé : {inc_2026['is_tax']:,.2f} €")
    print(f"Résultat net comptable : {inc_2026['net_accounting_result']:,.2f} €")

    print("\n--- Test 3 : Bilan Comptable 2026 ---")
    bal_2026 = compute_balance_sheet(2026)
    print(f"Actif Immobilisé Net : {bal_2026['total_fixed_assets_net']:,.2f} €")
    print(f"Actif Circulant (Créances + Tréso) : {bal_2026['total_current_assets']:,.2f} €")
    print(f"TOTAL ACTIF NET : {bal_2026['total_actif_net']:,.2f} €")
    print(f"Capitaux Propres : {bal_2026['total_equity']:,.2f} €")
    print(f"Total Dettes : {bal_2026['total_debts']:,.2f} €")
    print(f"TOTAL PASSIF : {bal_2026['total_passif']:,.2f} €")
    print(f"Écart (Actif - Passif) : {bal_2026['balance_check']:,.4f} €")
    print(f"Équilibre parfait : {bal_2026['is_balanced']}")

    assert bal_2026['is_balanced'], f"Le bilan n'est pas équilibré ! Écart = {bal_2026['balance_check']}"

    print("\n--- Test 4 : Table des Cases Cerfa ---")
    codes = get_cerfa_codes(inc_2026, bal_2026)
    print(f"Nombre de rubriques Cerfa générées : {len(codes)}")
    for c in codes[:5]:
        print(f"  [{c['Cerfa']}] Case {c['Case']} : {c['Désignation']} = {c['Montant (€)']:,.2f} €")

    print("\n✅ TOUS LES TESTS SONT PASSÉS AVEC SUCCÈS !")

if __name__ == "__main__":
    test_calculations()
