"""
Vue Gestion des Charges Globales de la SCI (Structure, Emprunts, Assurances, Compta).
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_df, query_rows, execute_write

CATEGORIES_SCI = [
    "Assurance PNO (Propriétaire Non Occupant)",
    "Honoraires comptables & juridique",
    "Frais bancaires & tenue de compte",
    "Taxe foncière (part SCI)",
    "Intérêts d'emprunt bancaire",
    "Remboursement capital emprunt",
    "Gros travaux de structure / toiture",
    "Frais de gestion & correspondance",
    "Autre charge SCI"
]

def render_sci_expenses():
    st.markdown("## 🏛️ Charges de la SCI (Globales)")
    st.caption("Suivi des charges structurelles de la société : assurances PNO, comptabilité, échéances de crédit, taxes foncières.")

    tab_list, tab_add = st.tabs(["📋 Liste des Dépenses SCI", "➕ Enregistrer une Dépense"])

    # 1. LISTE DES DEPENSES
    with tab_list:
        current_year = date.today().year
        col_y, col_c = st.columns([1, 2])
        with col_y:
            selected_year = st.selectbox("Exercice / Année", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_year), key="sci_exp_yr")
        with col_c:
            selected_cat = st.selectbox("Filtrer par catégorie", ["Toutes"] + CATEGORIES_SCI, key="sci_exp_cat")

        query = "SELECT * FROM sci_expenses WHERE strftime('%Y', date) = ?"
        params = [str(selected_year)]
        if selected_cat != "Toutes":
            query += " AND category = ?"
            params.append(selected_cat)
        query += " ORDER BY date DESC;"

        expenses = query_rows(query, params)

        if not expenses:
            st.info(f"Aucune dépense SCI enregistrée pour l'année {selected_year}.")
        else:
            exp_df = pd.DataFrame(expenses)
            total_amt = exp_df["amount"].sum()
            deductible_amt = exp_df[exp_df["is_deductible_2072"] == 1]["amount"].sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("Total Dépenses SCI", f"{total_amt:,.2f} €".replace(",", " "))
            m2.metric("Déductible Fiscal (2072)", f"{deductible_amt:,.2f} €".replace(",", " "), help="Charges déductibles des revenus fonciers pour l'IR")
            m3.metric("Nombre de factures", f"{len(exp_df)}")

            st.markdown("---")
            display_df = exp_df[["date", "category", "description", "amount", "payment_method", "invoice_ref", "is_deductible_2072"]].copy()
            display_df["is_deductible_2072"] = display_df["is_deductible_2072"].apply(lambda x: "✅ Oui" if x == 1 else "❌ Non")
            display_df.columns = ["Date", "Catégorie", "Description", "Montant (€)", "Mode", "Réf. Facture", "Déductible 2072"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # 2. ENREGISTRER UNE DEPENSE
    with tab_add:
        st.markdown("#### Nouvelle Dépense au nom de la SCI")
        with st.form("form_add_sci_expense", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                exp_date = st.date_input("Date de la dépense *", value=date.today()).strftime("%Y-%m-%d")
                category = st.selectbox("Catégorie de charge *", CATEGORIES_SCI)
                amount = st.number_input("Montant (€) *", min_value=0.01, value=150.0, step=10.0)
            with c2:
                payment_method = st.selectbox("Mode de paiement", ["Virement", "Prélèvement automatique", "Carte bancaire", "Chèque", "Autre"])
                invoice_ref = st.text_input("Référence facture / pièce comptable", placeholder="ex: FAC-2026-089")
                is_deductible = st.checkbox("Charge déductible fiscalement (Formulaire 2072)", value=True)

            description = st.text_input("Libellé / Objet *", placeholder="ex: Cotisation annuelle assurance PNO AXA")
            notes = st.text_area("Notes complémentaires", placeholder="Détail du contrat, échéancier...")

            submitted = st.form_submit_button("💾 Enregistrer la dépense", type="primary")
            if submitted:
                if not description.strip():
                    st.error("Le libellé de la dépense est requis.")
                else:
                    try:
                        execute_write("""
                            INSERT INTO sci_expenses (date, category, description, amount, payment_method, invoice_ref, is_deductible_2072, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, [exp_date, category, description.strip(), amount, payment_method, invoice_ref.strip(), 1 if is_deductible else 0, notes.strip()])
                        st.success(f"Dépense de **{amount:.2f} €** enregistrée avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
