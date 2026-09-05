"""
Vue Synthèse Fiscale & Compte de Résultat IS (Liasse Fiscale Cerfa 2065 / 2033).
Spécifique pour Société Civile Immobilière soumise à l'Impôt sur les Sociétés.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_df

def render_tax_report():
    st.markdown("## 📑 Liasse Fiscale & Compte de Résultat IS (Cerfa 2065)")
    st.caption("Synthèse comptable et fiscale pour SCI à l'IS : amortissements du bâti et des meubles, résultat d'exploitation, intérêts d'emprunt et calcul de l'IS (15% / 25%).")

    current_year = date.today().year
    col_y, _ = st.columns([1, 3])
    with col_y:
        tax_year = st.selectbox("Exercice comptable / Année fiscale", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_year), key="is_rep_yr")

    # 1. PRODUITS D'EXPLOITATION (Loyers nets perçus hors charges)
    rents_data = query_rows("""
        SELECT rent_amount, amount_paid, total_due
        FROM rent_payments
        WHERE period_year = ? AND amount_paid > 0;
    """, [tax_year])

    gross_rental_income = 0.0
    for r in rents_data:
        tot = r["total_due"]
        paid = r["amount_paid"]
        rent_part = r["rent_amount"]
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

    frais_gestion = sum(e["amount"] for e in sci_expenses if "comptable" in e["category"].lower() or "gestion" in e["category"].lower() or "juridique" in e["category"].lower())
    assurances = sum(e["amount"] for e in sci_expenses if "assurance" in e["category"].lower())
    taxes_foncieres = sum(e["amount"] for e in sci_expenses if "foncière" in e["category"].lower() or "fonciere" in e["category"].lower())
    travaux_sci = sum(e["amount"] for e in sci_expenses if "travaux" in e["category"].lower())
    
    # Charges de lots
    lot_expenses = query_rows("""
        SELECT category, description, amount, is_recoverable
        FROM property_expenses
        WHERE strftime('%Y', date) = ?;
    """, [str(tax_year)])

    travaux_lots = sum(e["amount"] for e in lot_expenses if "travaux" in e["category"].lower() or "réparation" in e["category"].lower() or "reparation" in e["category"].lower())
    copro_non_recup = sum(e["amount"] for e in lot_expenses if e["is_recoverable"] == 0 and "travaux" not in e["category"].lower())
    total_travaux_entretien = travaux_sci + travaux_lots

    total_operating_charges = frais_gestion + assurances + taxes_foncieres + copro_non_recup + total_travaux_entretien

    # 3. DOTATIONS AUX AMORTISSEMENTS (DAA)
    # Calcul dynamique à partir du parc de biens
    all_properties = query_rows("SELECT * FROM properties;")
    total_building_amort = 0.0
    total_furn_amort = 0.0
    amort_details = []

    for p in all_properties:
        p_price = float(p.get("acquisition_price", 0.0))
        p_notary = float(p.get("notary_fees", 0.0))
        total_p_cost = p_price + p_notary
        p_land_pct = float(p.get("land_share_pct", 15.0))
        p_years = max(1, int(p.get("amortization_years", 25)))

        land_val = p_price * (p_land_pct / 100.0)
        building_base = total_p_cost - land_val
        annual_b_amort = building_base / p_years

        p_furn_val = float(p.get("furniture_value", 0.0))
        p_furn_years = max(1, int(p.get("furniture_years", 5)))
        annual_f_amort = p_furn_val / p_furn_years if p_furn_val > 0 else 0.0

        total_p_amort = annual_b_amort + annual_f_amort
        total_building_amort += annual_b_amort
        total_furn_amort += annual_f_amort

        amort_details.append({
            "Bien": p.get("name"),
            "Coût total (€)": total_p_cost,
            "Part Terrain (€)": land_val,
            "Bâti amortissable (€)": building_base,
            "Annuité Bâti (€/an)": annual_b_amort,
            "Mobilier (€)": p_furn_val,
            "Annuité Meubles (€/an)": annual_f_amort,
            "Dotation Annuelle Totale (€)": total_p_amort
        })

    total_daa = total_building_amort + total_furn_amort

    # 4. RESULTAT D'EXPLOITATION
    operating_result = gross_rental_income - total_operating_charges - total_daa

    # 5. CHARGES FINANCIERES (Intérêts d'emprunt + frais bancaires)
    interets_emprunt = sum(e["amount"] for e in sci_expenses if "intérêt" in e["category"].lower() or "interet" in e["category"].lower())
    frais_bancaires = sum(e["amount"] for e in sci_expenses if "bancaire" in e["category"].lower())
    total_financial_charges = interets_emprunt + frais_bancaires

    # 6. RESULTAT COURANT AVANT IMPOT (RCAI)
    rcai = operating_result - total_financial_charges

    # 7. CALCUL DE L'IMPOT SUR LES SOCIETES (IS)
    is_tax = 0.0
    if rcai > 0:
        # Taux réduit PME à 15% jusqu'à 42 500 €
        base_15 = min(rcai, 42500.0)
        base_25 = max(0.0, rcai - 42500.0)
        is_tax = (base_15 * 0.15) + (base_25 * 0.25)

    # 8. RESULTAT NET COMPTABLE
    net_accounting_result = rcai - is_tax

    # METRIQUES PRINCIPALES
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Produits d'Exploitation", f"{gross_rental_income:,.2f} €".replace(",", " "), help="Loyers nus encaissés de l'exercice")
    kpi2.metric("Dotation Amortissements (DAA)", f"{total_daa:,.2f} €".replace(",", " "), delta="Déductible IS", delta_color="normal", help="Amortissement annuel du bâti et du mobilier")
    kpi3.metric(
        "Résultat Fiscal Imposable (RCAI)",
        f"{rcai:,.2f} €".replace(",", " "),
        delta="Bénéfice fiscal" if rcai >= 0 else "Déficit reportable",
        delta_color="normal" if rcai >= 0 else "off"
    )
    kpi4.metric(
        "Impôt sur les Sociétés (IS)",
        f"{is_tax:,.2f} €".replace(",", " "),
        delta="15% sous 42 500 € / 25% au-delà",
        delta_color="inverse"
    )

    st.markdown("---")

    # TABLEAU COMPTE DE RESULTAT 2065
    st.markdown("### 📊 Compte de Résultat Fiscal (Formulaire Cerfa 2065 / 2033)")

    income_statement = [
        {"Rubrique": "I. PRODUITS D'EXPLOITATION", "Détail": "Chiffre d'affaires (Loyers perçus hors charges)", "Montant (€)": gross_rental_income},
        {"Rubrique": "II. CHARGES D'EXPLOITATION", "Détail": "Total des charges déductibles ci-dessous", "Montant (€)": -total_operating_charges},
        {"Rubrique": "  • Frais de gestion & comptabilité", "Détail": "Honoraires expert-comptable, tenue de compte", "Montant (€)": -frais_gestion},
        {"Rubrique": "  • Primes d'assurance PNO", "Détail": "Assurances des logements et de la SCI", "Montant (€)": -assurances},
        {"Rubrique": "  • Entretien & petites réparations", "Détail": "Dépenses de maintenance courante", "Montant (€)": -total_travaux_entretien},
        {"Rubrique": "  • Charges copropriété non récupérées", "Détail": "Part propriétaire des charges d'immeuble", "Montant (€)": -copro_non_recup},
        {"Rubrique": "  • Impôts & taxes (Taxe foncière)", "Détail": "Taxe foncière acquittée hors TEOM", "Montant (€)": -taxes_foncieres},
        {"Rubrique": "III. DOTATIONS AUX AMORTISSEMENTS (DAA)", "Détail": "Amortissement comptable bâti + meubles", "Montant (€)": -total_daa},
        {"Rubrique": "  • Amortissement de l'immeuble (bâti)", "Détail": "Amortissement linéaire annuel sur 25-30 ans", "Montant (€)": -total_building_amort},
        {"Rubrique": "  • Amortissement du mobilier", "Détail": "Amortissement sur 5-7 ans", "Montant (€)": -total_furn_amort},
        {"Rubrique": "RÉSULTAT D'EXPLOITATION", "Détail": "Produits - Charges d'exploitation - Amortissements", "Montant (€)": operating_result},
        {"Rubrique": "IV. CHARGES FINANCIÈRES", "Détail": "Intérêts d'emprunts bancaires et frais financiers", "Montant (€)": -total_financial_charges},
        {"Rubrique": "RÉSULTAT COURANT AVANT IMPÔT (RCAI)", "Détail": "Assiette de calcul de l'Impôt sur les Sociétés", "Montant (€)": rcai},
        {"Rubrique": "V. IMPÔT SUR LES SOCIÉTÉS (IS)", "Détail": "Tranche 15% sous 42 500 € + 25% au-delà", "Montant (€)": -is_tax},
        {"Rubrique": "RÉSULTAT NET DE L'EXERCICE", "Détail": "Bénéfice distribuable ou mis en report à nouveau", "Montant (€)": net_accounting_result},
    ]

    df_is = pd.DataFrame(income_statement)
    st.table(df_is)

    # Export CSV Liasse Fiscale
    csv_data = df_is.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="📥 Exporter la Liasse Fiscale IS en CSV (pour Expert-Comptable)",
        data=csv_data,
        file_name=f"liasse_fiscale_is_2065_{tax_year}.csv",
        mime="text/csv"
    )

    # DETAIL DES AMORTISSEMENTS PAR LOT
    st.markdown("---")
    st.markdown("### 📉 Tableau d'Amortissement Détaillé par Bien")
    if amort_details:
        df_amort = pd.DataFrame(amort_details)
        st.dataframe(df_amort, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun bien enregistré dans le patrimoine pour calculer les amortissements.")
