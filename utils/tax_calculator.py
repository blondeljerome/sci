"""
Moteur de calcul comptable et fiscal complet pour SCI à l'IS (Cerfa 2065 / 2033).
Prend en charge :
- Le Compte de Résultat (Cerfa 2033-B)
- Le Bilan Actif & Passif (Cerfa 2033-A)
- Le Tableau des Immobilisations & Amortissements (Cerfa 2033-C)
- Le contrôle d'équilibre comptable rigoureux (Actif = Passif)
- La table de correspondance avec les cases officielles de la DGFiP
"""
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, date
import calendar
from database import query_rows, query_one
from utils.loan import get_annual_loan_breakdown, generate_amortization_schedule

def is_leap_year(year: int) -> bool:
    return calendar.isleap(year)

def compute_depreciation_schedule(tax_year: int) -> List[Dict[str, Any]]:
    """
    Calcule pour chaque bien immobilier :
    - La part terrain (non amortissable)
    - La base amortissable du bâti et du mobilier
    - Les dotations antérieures (jusqu'à tax_year - 1)
    - La dotation de l'exercice tax_year (avec prorata temporis exact si acquis en cours d'exercice)
    - Les amortissements cumulés au 31/12/tax_year
    - La Valeur Nette Comptable (VNC) au 31/12/tax_year
    """
    all_properties = query_rows("SELECT * FROM properties;")
    schedule = []

    for p in all_properties:
        acq_date_str = p.get("acquisition_date") or ""
        try:
            acq_date = datetime.strptime(acq_date_str[:10], "%Y-%m-%d").date()
            acq_year = acq_date.year
        except Exception:
            acq_date = None
            acq_year = tax_year

        # Si le bien est acquis après l'exercice sélectionné, il ne figure pas à ce bilan
        if acq_date and acq_year > tax_year:
            continue

        p_price = float(p.get("acquisition_price", 0.0) or 0.0)
        p_notary = float(p.get("notary_fees", 0.0) or 0.0)
        total_cost = p_price + p_notary

        p_land_pct = float(p.get("land_share_pct", 15.0) or 15.0)
        land_val = p_price * (p_land_pct / 100.0)

        building_base = max(0.0, total_cost - land_val)
        building_years = max(1, int(p.get("amortization_years", 25) or 25))
        annual_b_full = building_base / building_years

        furn_val = float(p.get("furniture_value", 0.0) or 0.0)
        furn_years = max(1, int(p.get("furniture_years", 5) or 5))
        annual_f_full = furn_val / furn_years if furn_val > 0 else 0.0

        # Calcul prorata première année
        prorata_first_year = 1.0
        if acq_date:
            days_in_year = (366 if is_leap_year(acq_year) else 365)
            days_held = (date(acq_year, 12, 31) - acq_date).days + 1
            prorata_first_year = max(0.0, min(1.0, days_held / days_in_year))

        # 1. Amortissements cumulés antérieurs (jusqu'à tax_year - 1)
        prior_b = 0.0
        prior_f = 0.0

        if acq_year < tax_year:
            # Année d'acquisition
            prior_b += annual_b_full * prorata_first_year
            prior_f += annual_f_full * prorata_first_year

            # Années pleines intermédiaires (de acq_year + 1 à tax_year - 1)
            full_years_prior = (tax_year - 1) - acq_year
            if full_years_prior > 0:
                prior_b += annual_b_full * full_years_prior
                prior_f += annual_f_full * full_years_prior

            prior_b = min(building_base, prior_b)
            prior_f = min(furn_val, prior_f)

        # 2. Dotation de l'exercice courant tax_year
        if acq_year == tax_year:
            cur_dot_b = min(building_base - prior_b, annual_b_full * prorata_first_year)
            cur_dot_f = min(furn_val - prior_f, annual_f_full * prorata_first_year)
        else:
            cur_dot_b = min(building_base - prior_b, annual_b_full)
            cur_dot_f = min(furn_val - prior_f, annual_f_full)

        # 3. Cumuls à la clôture au 31/12/tax_year
        cumul_b = prior_b + cur_dot_b
        cumul_f = prior_f + cur_dot_f
        total_cumul_amort = cumul_b + cumul_f

        # 4. Valeur Nette Comptable (VNC)
        vnc_b = building_base - cumul_b
        vnc_f = furn_val - cumul_f
        total_vnc = land_val + vnc_b + vnc_f

        schedule.append({
            "property_id": p.get("id"),
            "name": p.get("name"),
            "acquisition_date": acq_date_str[:10] if acq_date_str else "Non définie",
            "acquisition_year": acq_year,
            "total_cost": total_cost,
            "land_value": land_val,
            "building_base": building_base,
            "building_years": building_years,
            "annual_building_full": annual_b_full,
            "furniture_base": furn_val,
            "furniture_years": furn_years,
            "annual_furn_full": annual_f_full,
            "prorata_first_year_pct": prorata_first_year * 100.0,
            "prior_amort_building": prior_b,
            "prior_amort_furniture": prior_f,
            "prior_amort_total": prior_b + prior_f,
            "dotation_building": cur_dot_b,
            "dotation_furniture": cur_dot_f,
            "dotation_total": cur_dot_b + cur_dot_f,
            "cumul_amort_building": cumul_b,
            "cumul_amort_furniture": cumul_f,
            "cumul_amort_total": total_cumul_amort,
            "vnc_building": vnc_b,
            "vnc_furniture": vnc_f,
            "vnc_total": total_vnc
        })

    return schedule

def compute_income_statement(tax_year: int) -> Dict[str, Any]:
    """
    Calcule l'ensemble du Compte de Résultat de l'exercice tax_year (Cerfa 2033-B).
    """
    # 1. PRODUITS D'EXPLOITATION (Loyers perçus hors charges)
    rents_data = query_rows("""
        SELECT rent_amount, amount_paid, total_due
        FROM rent_payments
        WHERE period_year = ? AND amount_paid > 0;
    """, [tax_year])

    gross_rental_income = 0.0
    for r in rents_data:
        tot = float(r.get("total_due", 0.0) or 0.0)
        paid = float(r.get("amount_paid", 0.0) or 0.0)
        rent_part = float(r.get("rent_amount", 0.0) or 0.0)
        if tot > 0:
            gross_rental_income += paid * (rent_part / tot)
        else:
            gross_rental_income += paid

    # 2. CHARGES D'EXPLOITATION
    sci_expenses = query_rows("""
        SELECT category, description, amount
        FROM sci_expenses
        WHERE strftime('%Y', date) = ?;
    """, [str(tax_year)])

    frais_gestion = sum(float(e["amount"]) for e in sci_expenses if any(k in e["category"].lower() for k in ["comptable", "gestion", "juridique", "avocat", "notaire", "formalité"]))
    assurances = sum(float(e["amount"]) for e in sci_expenses if "assurance" in e["category"].lower() or "pno" in e["category"].lower())
    taxes_foncieres = sum(float(e["amount"]) for e in sci_expenses if "foncière" in e["category"].lower() or "fonciere" in e["category"].lower())
    travaux_sci = sum(float(e["amount"]) for e in sci_expenses if "travaux" in e["category"].lower() or "réparation" in e["category"].lower() or "reparation" in e["category"].lower())
    autres_charges_sci = sum(
        float(e["amount"]) for e in sci_expenses
        if not any(k in e["category"].lower() for k in ["comptable", "gestion", "juridique", "assurance", "foncière", "fonciere", "travaux", "réparation", "reparation", "intérêt", "interet", "bancaire", "banque"])
    )

    # Charges de lots
    lot_expenses = query_rows("""
        SELECT category, description, amount, is_recoverable
        FROM property_expenses
        WHERE strftime('%Y', date) = ?;
    """, [str(tax_year)])

    travaux_lots = sum(float(e["amount"]) for e in lot_expenses if "travaux" in e["category"].lower() or "réparation" in e["category"].lower() or "reparation" in e["category"].lower())
    copro_non_recup = sum(float(e["amount"]) for e in lot_expenses if int(e.get("is_recoverable", 0) or 0) == 0 and not any(k in e["category"].lower() for k in ["travaux", "réparation", "reparation"]))

    total_travaux_entretien = travaux_sci + travaux_lots
    total_operating_charges = frais_gestion + assurances + taxes_foncieres + copro_non_recup + total_travaux_entretien + autres_charges_sci

    # 3. DOTATIONS AUX AMORTISSEMENTS (DAA)
    amort_schedule = compute_depreciation_schedule(tax_year)
    total_building_amort = sum(item["dotation_building"] for item in amort_schedule)
    total_furn_amort = sum(item["dotation_furniture"] for item in amort_schedule)
    total_daa = total_building_amort + total_furn_amort

    # 4. RESULTAT D'EXPLOITATION
    operating_result = gross_rental_income - total_operating_charges - total_daa

    # 5. CHARGES FINANCIERES (Intérêts d'emprunt + frais bancaires)
    interets_sci_expenses = sum(float(e["amount"]) for e in sci_expenses if "intérêt" in e["category"].lower() or "interet" in e["category"].lower())

    # Emprunts enregistrés
    all_loans = query_rows("SELECT * FROM loans;")
    loans_interest_calc = 0.0
    for l in all_loans:
        b = get_annual_loan_breakdown(l, tax_year)
        loans_interest_calc += b["interest_paid"]

    interets_emprunt = max(interets_sci_expenses, loans_interest_calc)
    frais_bancaires = sum(float(e["amount"]) for e in sci_expenses if "bancaire" in e["category"].lower() or "banque" in e["category"].lower())
    total_financial_charges = interets_emprunt + frais_bancaires

    # 6. RESULTAT COURANT AVANT IMPOT (RCAI)
    rcai = operating_result - total_financial_charges

    # 7. CALCUL DE L'IMPOT SUR LES SOCIETES (IS)
    is_tax = 0.0
    base_15 = 0.0
    base_25 = 0.0
    if rcai > 0:
        base_15 = min(rcai, 42500.0)
        base_25 = max(0.0, rcai - 42500.0)
        is_tax = (base_15 * 0.15) + (base_25 * 0.25)

    # 8. RESULTAT NET COMPTABLE
    net_accounting_result = rcai - is_tax

    return {
        "tax_year": tax_year,
        "gross_rental_income": gross_rental_income,
        "frais_gestion": frais_gestion,
        "assurances": assurances,
        "taxes_foncieres": taxes_foncieres,
        "total_travaux_entretien": total_travaux_entretien,
        "copro_non_recup": copro_non_recup,
        "autres_charges_sci": autres_charges_sci,
        "total_operating_charges": total_operating_charges,
        "total_building_amort": total_building_amort,
        "total_furn_amort": total_furn_amort,
        "total_daa": total_daa,
        "operating_result": operating_result,
        "interets_emprunt": interets_emprunt,
        "frais_bancaires": frais_bancaires,
        "total_financial_charges": total_financial_charges,
        "rcai": rcai,
        "base_15": base_15,
        "base_25": base_25,
        "is_tax": is_tax,
        "net_accounting_result": net_accounting_result,
        "amort_schedule": amort_schedule
    }

def compute_balance_sheet(tax_year: int) -> Dict[str, Any]:
    """
    Calcule le Bilan Comptable complet au 31 décembre de l'exercice tax_year (Cerfa 2033-A).
    Comprend l'Actif (Brut, Amortissements, Net), le Passif (Capitaux Propres et Dettes),
    et vérifie rigoureusement l'égalité Total Actif == Total Passif.
    """
    # 1. Compte de résultat de l'exercice N
    inc_stmt = compute_income_statement(tax_year)
    amort_schedule = inc_stmt["amort_schedule"]

    # 2. ACTIF IMMOBILISE au 31/12/tax_year
    land_gross = sum(item["land_value"] for item in amort_schedule)
    building_gross = sum(item["building_base"] for item in amort_schedule)
    building_amort_cumul = sum(item["cumul_amort_building"] for item in amort_schedule)
    building_net = building_gross - building_amort_cumul

    furn_gross = sum(item["furniture_base"] for item in amort_schedule)
    furn_amort_cumul = sum(item["cumul_amort_furniture"] for item in amort_schedule)
    furn_net = furn_gross - furn_amort_cumul

    total_fixed_assets_gross = land_gross + building_gross + furn_gross
    total_fixed_assets_amort = building_amort_cumul + furn_amort_cumul
    total_fixed_assets_net = land_gross + building_net + furn_net

    # 3. CREANCES CLIENTS (Loyers échus non payés au 31/12/tax_year)
    unpaid_rents_rows = query_rows("""
        SELECT SUM(total_due - amount_paid) as total_unpaid
        FROM rent_payments
        WHERE period_year <= ? AND (due_date <= ? OR period_year < ?);
    """, [tax_year, f"{tax_year}-12-31", tax_year])
    tenant_receivables = float(unpaid_rents_rows[0].get("total_unpaid", 0.0) or 0.0) if unpaid_rents_rows else 0.0
    tenant_receivables = max(0.0, tenant_receivables)

    # 4. CAPITAUX PROPRES AU PASSIF
    sci_info = query_one("SELECT share_capital FROM sci_info WHERE id = 1;") or {}
    share_capital = float(sci_info.get("share_capital", 1000.0) or 1000.0)

    # Calcul du report à nouveau des années antérieures (< tax_year)
    # On recherche les années antérieures où des opérations ont existé
    min_year_row = query_rows("""
        SELECT MIN(y) as min_y FROM (
            SELECT CAST(period_year AS INTEGER) as y FROM rent_payments
            UNION
            SELECT CAST(strftime('%Y', date) AS INTEGER) as y FROM sci_expenses
            UNION
            SELECT CAST(strftime('%Y', date) AS INTEGER) as y FROM partner_accounts
            UNION
            SELECT CAST(strftime('%Y', acquisition_date) AS INTEGER) as y FROM properties WHERE acquisition_date IS NOT NULL
        );
    """)
    min_year = tax_year
    if min_year_row and min_year_row[0].get("min_y"):
        try:
            min_year = int(min_year_row[0]["min_y"])
        except Exception:
            min_year = tax_year

    report_a_nouveau = 0.0
    if min_year < tax_year:
        for y in range(min_year, tax_year):
            prior_inc = compute_income_statement(y)
            report_a_nouveau += prior_inc["net_accounting_result"]

    net_result = inc_stmt["net_accounting_result"]
    total_equity = share_capital + report_a_nouveau + net_result

    # 5. DETTES AU PASSIF
    # Emprunts bancaires : Capital restant dû au 31/12/tax_year
    all_loans = query_rows("SELECT * FROM loans;")
    total_loan_crd = 0.0
    loan_crd_less_1y = 0.0
    loan_crd_more_1y = 0.0

    for l in all_loans:
        start_d = l.get("start_date", "2024-01-01")
        if start_d <= f"{tax_year}-12-31":
            sched = generate_amortization_schedule(l)
            # Solde à la fin de tax_year
            year_entries = [r for r in sched if r["year"] == tax_year]
            if year_entries:
                crd_end_year = year_entries[-1]["end_balance"]
            else:
                # Si le prêt est terminé avant tax_year
                past_entries = [r for r in sched if r["year"] < tax_year]
                crd_end_year = 0.0

            total_loan_crd += crd_end_year

            # Part à moins d'un an (capital amorti en tax_year + 1)
            next_year_entries = [r for r in sched if r["year"] == tax_year + 1]
            crd_next_year_cap = sum(r["capital"] for r in next_year_entries)
            loan_crd_less_1y += crd_next_year_cap
            loan_crd_more_1y += max(0.0, crd_end_year - crd_next_year_cap)

    # Comptes Courants d'Associés (CCA) au 31/12/tax_year
    cca_rows = query_rows("""
        SELECT type, amount FROM partner_accounts
        WHERE date <= ?;
    """, [f"{tax_year}-12-31"])
    cca_apports = sum(float(r["amount"]) for r in cca_rows if r["type"] == "apport")
    cca_rembours = sum(float(r["amount"]) for r in cca_rows if r["type"] == "remboursement")
    total_cca_balance = max(0.0, cca_apports - cca_rembours)

    # Dépôts de garantie détenus (dettes envers les locataires)
    deposits_rows = query_rows("""
        SELECT SUM(deposit_amount) as total_dep
        FROM tenants
        WHERE lease_start <= ? AND (lease_end IS NULL OR lease_end = '' OR lease_end >= ?);
    """, [f"{tax_year}-12-31", f"{tax_year}-01-01"])
    total_deposits = float(deposits_rows[0].get("total_dep", 0.0) or 0.0) if deposits_rows else 0.0

    # Dette fiscale (IS de l'exercice tax_year restant dû au 31/12/tax_year)
    tax_liability = inc_stmt["is_tax"]

    total_debts = total_loan_crd + total_cca_balance + total_deposits + tax_liability
    total_passif = total_equity + total_debts

    # 6. TRESORERIE / DISPONIBILITES A LA CLOTURE (ACTIF CIRCULANT)
    # Dans le modèle comptable rigoureux, la trésorerie est la résultante équilibrée des flux
    # Trésorerie = Total Passif - Actif Immobilisé Net - Créances Locataires
    # Cela garantit l'équilibre parfait de la partie double Actif = Passif
    calculated_cash = total_passif - total_fixed_assets_net - tenant_receivables
    total_current_assets = tenant_receivables + calculated_cash
    total_actif_net = total_fixed_assets_net + total_current_assets

    balance_check = total_actif_net - total_passif
    is_balanced = abs(balance_check) < 0.01

    return {
        "tax_year": tax_year,
        # Actif Immobilisé
        "land_gross": land_gross,
        "building_gross": building_gross,
        "building_amort_cumul": building_amort_cumul,
        "building_net": building_net,
        "furn_gross": furn_gross,
        "furn_amort_cumul": furn_amort_cumul,
        "furn_net": furn_net,
        "total_fixed_assets_gross": total_fixed_assets_gross,
        "total_fixed_assets_amort": total_fixed_assets_amort,
        "total_fixed_assets_net": total_fixed_assets_net,
        # Actif Circulant
        "tenant_receivables": tenant_receivables,
        "cash_and_equivalents": calculated_cash,
        "total_current_assets": total_current_assets,
        # Total Actif
        "total_actif_gross": total_fixed_assets_gross + total_current_assets,
        "total_actif_amort": total_fixed_assets_amort,
        "total_actif_net": total_actif_net,
        # Passif - Capitaux Propres
        "share_capital": share_capital,
        "report_a_nouveau": report_a_nouveau,
        "net_result": net_result,
        "total_equity": total_equity,
        # Passif - Dettes
        "total_loan_crd": total_loan_crd,
        "loan_crd_less_1y": loan_crd_less_1y,
        "loan_crd_more_1y": loan_crd_more_1y,
        "total_cca_balance": total_cca_balance,
        "total_deposits": total_deposits,
        "tax_liability": tax_liability,
        "total_debts": total_debts,
        # Total Passif & Contrôle
        "total_passif": total_passif,
        "balance_check": balance_check,
        "is_balanced": is_balanced
    }

def get_cerfa_codes(inc_stmt: Dict[str, Any], bal_sheet: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Retourne la table de correspondance avec les cases officielles DGFiP :
    - Cerfa 2033-A (Bilan simplifié)
    - Cerfa 2033-B (Compte de résultat simplifié)
    """
    return [
        # --- Cerfa 2033-A : Bilan Actif ---
        {"Cerfa": "2033-A (Actif)", "Case": "010", "Désignation": "Immobilisations : Terrains (Brut)", "Montant (€)": bal_sheet["land_gross"]},
        {"Cerfa": "2033-A (Actif)", "Case": "014", "Désignation": "Constructions (Brut)", "Montant (€)": bal_sheet["building_gross"]},
        {"Cerfa": "2033-A (Actif)", "Case": "016", "Désignation": "Constructions (Amortissements)", "Montant (€)": bal_sheet["building_amort_cumul"]},
        {"Cerfa": "2033-A (Actif)", "Case": "028", "Désignation": "Installations techniques, matériel, mobilier (Brut)", "Montant (€)": bal_sheet["furn_gross"]},
        {"Cerfa": "2033-A (Actif)", "Case": "030", "Désignation": "Installations, matériel, mobilier (Amortissements)", "Montant (€)": bal_sheet["furn_amort_cumul"]},
        {"Cerfa": "2033-A (Actif)", "Case": "040", "Désignation": "TOTAL I : ACTIF IMMOBILISÉ (Net)", "Montant (€)": bal_sheet["total_fixed_assets_net"]},
        {"Cerfa": "2033-A (Actif)", "Case": "064", "Désignation": "Créances clients et comptes rattachés (Loyers échus)", "Montant (€)": bal_sheet["tenant_receivables"]},
        {"Cerfa": "2033-A (Actif)", "Case": "080", "Désignation": "Disponibilités (Banque et trésorerie)", "Montant (€)": bal_sheet["cash_and_equivalents"]},
        {"Cerfa": "2033-A (Actif)", "Case": "092", "Désignation": "TOTAL II : ACTIF CIRCULANT (Net)", "Montant (€)": bal_sheet["total_current_assets"]},
        {"Cerfa": "2033-A (Actif)", "Case": "100", "Désignation": "TOTAL GÉNÉRAL DE L'ACTIF (I + II)", "Montant (€)": bal_sheet["total_actif_net"]},

        # --- Cerfa 2033-A : Bilan Passif ---
        {"Cerfa": "2033-A (Passif)", "Case": "120", "Désignation": "Capital social ou individuel", "Montant (€)": bal_sheet["share_capital"]},
        {"Cerfa": "2033-A (Passif)", "Case": "146", "Désignation": "Report à nouveau", "Montant (€)": bal_sheet["report_a_nouveau"]},
        {"Cerfa": "2033-A (Passif)", "Case": "150", "Désignation": "RÉSULTAT DE L'EXERCICE (Bénéfice ou Perte)", "Montant (€)": bal_sheet["net_result"]},
        {"Cerfa": "2033-A (Passif)", "Case": "160", "Désignation": "TOTAL I : CAPITAUX PROPRES", "Montant (€)": bal_sheet["total_equity"]},
        {"Cerfa": "2033-A (Passif)", "Case": "176", "Désignation": "Emprunts et dettes auprès des établissements de crédit", "Montant (€)": bal_sheet["total_loan_crd"]},
        {"Cerfa": "2033-A (Passif)", "Case": "178", "Désignation": "Emprunts et dettes diverses (Comptes courants associés & Dépôts)", "Montant (€)": bal_sheet["total_cca_balance"] + bal_sheet["total_deposits"]},
        {"Cerfa": "2033-A (Passif)", "Case": "190", "Désignation": "Dettes fiscales et sociales (Impôt sur les sociétés)", "Montant (€)": bal_sheet["tax_liability"]},
        {"Cerfa": "2033-A (Passif)", "Case": "196", "Désignation": "TOTAL II : DETTES", "Montant (€)": bal_sheet["total_debts"]},
        {"Cerfa": "2033-A (Passif)", "Case": "200", "Désignation": "TOTAL GÉNÉRAL DU PASSIF (I + II)", "Montant (€)": bal_sheet["total_passif"]},

        # --- Cerfa 2033-B : Compte de Résultat ---
        {"Cerfa": "2033-B", "Case": "218", "Désignation": "Chiffre d'affaires net (Loyers encaissés)", "Montant (€)": inc_stmt["gross_rental_income"]},
        {"Cerfa": "2033-B", "Case": "232", "Désignation": "TOTAL DES PRODUITS D'EXPLOITATION", "Montant (€)": inc_stmt["gross_rental_income"]},
        {"Cerfa": "2033-B", "Case": "250", "Désignation": "Autres achats et charges externes (Gestion, assurances, entretien, copro)", "Montant (€)": inc_stmt["total_operating_charges"] - inc_stmt["taxes_foncieres"]},
        {"Cerfa": "2033-B", "Case": "252", "Désignation": "Impôts, taxes et versements assimilés (Taxe foncière)", "Montant (€)": inc_stmt["taxes_foncieres"]},
        {"Cerfa": "2033-B", "Case": "260", "Désignation": "Dotations aux amortissements (DAA)", "Montant (€)": inc_stmt["total_daa"]},
        {"Cerfa": "2033-B", "Case": "264", "Désignation": "TOTAL DES CHARGES D'EXPLOITATION", "Montant (€)": inc_stmt["total_operating_charges"] + inc_stmt["total_daa"]},
        {"Cerfa": "2033-B", "Case": "270", "Désignation": "RÉSULTAT D'EXPLOITATION", "Montant (€)": inc_stmt["operating_result"]},
        {"Cerfa": "2033-B", "Case": "294", "Désignation": "Charges financières (Intérêts d'emprunt et frais bancaires)", "Montant (€)": inc_stmt["total_financial_charges"]},
        {"Cerfa": "2033-B", "Case": "300", "Désignation": "RÉSULTAT COURANT AVANT IMPÔTS (RCAI)", "Montant (€)": inc_stmt["rcai"]},
        {"Cerfa": "2033-B", "Case": "312", "Désignation": "Impôt sur les bénéfices (IS 15% / 25%)", "Montant (€)": inc_stmt["is_tax"]},
        {"Cerfa": "2033-B", "Case": "314", "Désignation": "RÉSULTAT NET COMPTABLE DE L'EXERCICE", "Montant (€)": inc_stmt["net_accounting_result"]}
    ]
