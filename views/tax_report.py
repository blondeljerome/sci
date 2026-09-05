"""
Vue Synthèse Fiscale & Aide Déclaration 2072 (Revenus Fonciers SCI à l'IR).
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_df

def render_tax_report():
    st.markdown("## 📑 Synthèse Fiscale & Aide Déclaration 2072")
    st.caption("Ce rapport synthétise vos recettes et charges déductibles au format de la liasse fiscale 2072 des SCI à l'Impôt sur le Revenu.")

    current_year = date.today().year
    col1, col2 = st.columns([1, 3])
    with col1:
        tax_year = st.selectbox("Année fiscale d'imposition", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_year), key="tax_rep_yr")

    # 1. Recettes brutes : loyers HC réellement perçus
    rents_data = query_rows("""
        SELECT rent_amount, amount_paid, total_due, charges_amount
        FROM rent_payments
        WHERE period_year = ? AND amount_paid > 0;
    """, [tax_year])

    # Proportion de loyer nu encaissé (hors charges)
    gross_rental_income = 0.0
    for r in rents_data:
        # Si le paiement est complet, le loyer nu perçu est rent_amount
        # Si le paiement est partiel, on applique la quote-part rent / total
        tot = r["total_due"]
        paid = r["amount_paid"]
        rent_part = r["rent_amount"]
        if tot > 0:
            gross_rental_income += paid * (rent_part / tot)
        else:
            gross_rental_income += paid

    # 2. Dépenses déductibles - Charges SCI
    sci_expenses = query_rows("""
        SELECT category, description, amount
        FROM sci_expenses
        WHERE strftime('%Y', date) = ? AND is_deductible_2072 = 1;
    """, [str(tax_year)])

    # Ventilation selon les rubriques 2072
    frais_gestion = sum(e["amount"] for e in sci_expenses if "comptable" in e["category"].lower() or "gestion" in e["category"].lower())
    assurances = sum(e["amount"] for e in sci_expenses if "assurance" in e["category"].lower())
    taxes_foncieres = sum(e["amount"] for e in sci_expenses if "foncière" in e["category"].lower() or "fonciere" in e["category"].lower())
    interets_emprunt = sum(e["amount"] for e in sci_expenses if "intérêt" in e["category"].lower() or "interet" in e["category"].lower())
    travaux_sci = sum(e["amount"] for e in sci_expenses if "travaux" in e["category"].lower())
    autres_sci = sum(e["amount"] for e in sci_expenses if e not in [frais_gestion, assurances, taxes_foncieres, interets_emprunt, travaux_sci])

    # 3. Dépenses déductibles - Charges des Lots
    lot_expenses = query_rows("""
        SELECT category, description, amount, is_recoverable
        FROM property_expenses
        WHERE strftime('%Y', date) = ?;
    """, [str(tax_year)])

    travaux_lots = sum(e["amount"] for e in lot_expenses if "travaux" in e["category"].lower() or "réparation" in e["category"].lower() or "reparation" in e["category"].lower())
    copro_non_recup = sum(e["amount"] for e in lot_expenses if e["is_recoverable"] == 0 and "travaux" not in e["category"].lower())

    total_travaux = travaux_sci + travaux_lots
    total_deductible_expenses = frais_gestion + assurances + taxes_foncieres + interets_emprunt + total_travaux + copro_non_recup

    net_tax_result = gross_rental_income - total_deductible_expenses

    # Affichage des KPIs fiscaux
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Recettes Brutes Imposables", f"{gross_rental_income:,.2f} €".replace(",", " "), help="Loyers nus perçus hors charges")
    kpi2.metric("Charges Fiscalement Déductibles", f"{total_deductible_expenses:,.2f} €".replace(",", " "), delta=f"-{total_deductible_expenses:,.2f} €", delta_color="inverse")
    kpi3.metric(
        "Résultat Net Foncier (2072)",
        f"{net_tax_result:,.2f} €".replace(",", " "),
        delta="Bénéfice imposable" if net_tax_result >= 0 else "Déficit foncier",
        delta_color="normal" if net_tax_result >= 0 else "off"
    )

    st.markdown("---")
    st.markdown("### 📋 Tableau de ventilation conforme Cerfa 2072")

    tax_table = [
        {"Ligne Cerfa": "Ligne 1 - Recettes brutes", "Description": "Loyers encaissés hors charges", "Montant (€)": gross_rental_income},
        {"Ligne Cerfa": "Ligne 4 - Frais de gestion & comptabilité", "Description": "Honoraires expert-comptable, tenue de compte, logiciels", "Montant (€)": frais_gestion},
        {"Ligne Cerfa": "Ligne 5 - Primes d'assurance", "Description": "Assurances Propriétaire Non Occupant (PNO), GLI", "Montant (€)": assurances},
        {"Ligne Cerfa": "Ligne 6 - Dépenses de réparation & entretien", "Description": "Travaux d'entretien, de réparation et d'amélioration", "Montant (€)": total_travaux},
        {"Ligne Cerfa": "Ligne 7 - Impositions (Taxe foncière)", "Description": "Taxe foncière acquittée par la SCI (hors taxe d'ordures ménagères)", "Montant (€)": taxes_foncieres},
        {"Ligne Cerfa": "Ligne 8 - Charges de copropriété déductibles", "Description": "Provisions et charges de copropriété déductibles part propriétaire", "Montant (€)": copro_non_recup},
        {"Ligne Cerfa": "Ligne 13 - Intérêts d'emprunt", "Description": "Intérêts des crédits immobiliers contractés pour l'acquisition", "Montant (€)": interets_emprunt},
        {"Ligne Cerfa": "TOTAL DÉDUCTIBLE", "Description": "Total des charges déductibles de l'exercice", "Montant (€)": total_deductible_expenses},
        {"Ligne Cerfa": "RÉSULTAT NET FONCIER", "Description": "Bénéfice imposable ou déficit foncier répartissable entre associés", "Montant (€)": net_tax_result},
    ]

    df_tax = pd.DataFrame(tax_table)
    st.table(df_tax)

    # Export CSV pour l'expert-comptable
    csv_data = df_tax.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        label="📥 Exporter le récapitulatif fiscal 2072 en CSV (Excel)",
        data=csv_data,
        file_name=f"declaration_2072_sci_{tax_year}.csv",
        mime="text/csv"
    )
