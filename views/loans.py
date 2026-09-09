"""
Vue Gestion des Emprunts Bancaires & Tableaux d'Amortissement.
Spécifique SCI à l'IS : ventilation rigoureuse capital / intérêts déductibles / assurance.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_one, execute_write
from utils.loan import calculate_monthly_payment, generate_amortization_schedule, get_annual_loan_breakdown

def render_loans():
    st.markdown("## 🏦 Emprunts Bancaires & Crédits Immobiliers")
    st.caption("Gérez les financements de votre SCI, visualisez les tableaux d'amortissement et ventilez automatiquement les intérêts déductibles de l'IS.")

    tab_list, tab_add = st.tabs(["📋 Liste des Prêts & Échéanciers", "➕ Ajouter un Emprunt"])

    # 1. LISTE DES PRETS
    with tab_list:
        loans = query_rows("""
            SELECT l.*, p.name as property_name
            FROM loans l
            LEFT JOIN properties p ON l.property_id = p.id
            ORDER BY l.start_date DESC;
        """)

        if not loans:
            st.info("Aucun emprunt enregistré pour la SCI. Utilisez l'onglet **'➕ Ajouter un Emprunt'** pour saisir votre premier crédit immobilier.")
        else:
            current_year = date.today().year

            total_borrowed = sum(l["amount"] for l in loans)
            total_monthly_installments = 0.0
            total_interests_this_year = 0.0
            total_remaining_balance = 0.0

            for l in loans:
                m_pay = calculate_monthly_payment(l["amount"], l["annual_interest_rate"], l["duration_months"])
                total_monthly_installments += (m_pay + float(l.get("monthly_insurance", 0.0)))
                breakdown = get_annual_loan_breakdown(l, current_year)
                total_interests_this_year += breakdown["interest_paid"]
                total_remaining_balance += breakdown["remaining_balance"]

            # Cartes de synthèse globale des emprunts
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Capital Total Emprunté", f"{total_borrowed:,.2f} €".replace(",", " "))
            c2.metric("Capital Restant Dû (estimé)", f"{total_remaining_balance:,.2f} €".replace(",", " "), help="Dette bancaire restante au passif du bilan")
            c3.metric("Mensualités Totales", f"{total_monthly_installments:,.2f} € / mois".replace(",", " "), help="Assurance comprise")
            c4.metric(
                f"Intérêts Déductibles IS ({current_year})",
                f"{total_interests_this_year:,.2f} €".replace(",", " "),
                help="Charges financières qui viennent réduire l'impôt sur les sociétés cette année"
            )

            st.markdown("---")

            for loan in loans:
                m_pay = calculate_monthly_payment(loan["amount"], loan["annual_interest_rate"], loan["duration_months"])
                ins = float(loan.get("monthly_insurance", 0.0))
                tot_m = m_pay + ins
                dur_years = loan["duration_months"] // 12

                with st.expander(f"🏦 {loan['bank_name']} — {loan.get('loan_reference') or 'Prêt immobilier'} ({tot_m:.2f} €/mois sur {dur_years} ans)", expanded=True):
                    lc1, lc2, lc3 = st.columns(3)
                    with lc1:
                        st.markdown(f"**Bien financé :** {loan.get('property_name') or 'Financement global SCI'}")
                        st.markdown(f"**Montant emprunté :** {loan['amount']:,.2f} €".replace(",", " "))
                        st.markdown(f"**Taux nominal :** {loan['annual_interest_rate']:.2f} %")
                    with lc2:
                        st.markdown(f"**Durée :** {loan['duration_months']} mois ({dur_years} ans)")
                        st.markdown(f"**Date 1ère échéance :** {loan['start_date']}")
                        st.markdown(f"**Assurance mensuelle :** {ins:.2f} €/mois")
                    with lc3:
                        st.markdown(f"**Mensualité hors assurance :** {m_pay:.2f} €")
                        st.markdown(f"**Mensualité totale prélevée :** **{tot_m:.2f} € CC**")
                        if loan.get("notes"):
                            st.caption(f"📝 {loan.get('notes')}")

                    st.markdown("##### 📅 Tableau d'Amortissement Complet")
                    sched = generate_amortization_schedule(loan)
                    df_sched = pd.DataFrame(sched)

                    # Option d'affichage : par année ou par mois
                    view_mode = st.radio("Affichage de l'échéancier", ["Synthèse par Année (Fiscalité IS)", "Détail mois par mois"], horizontal=True, key=f"view_mode_{loan['id']}")

                    if view_mode == "Synthèse par Année (Fiscalité IS)":
                        df_annual = df_sched.groupby("year").agg({
                            "capital": "sum",
                            "interest": "sum",
                            "insurance": "sum",
                            "total_monthly": "sum",
                            "end_balance": "last"
                        }).reset_index()
                        df_annual.columns = ["Année", "Capital remboursé (€)", "Intérêts déductibles IS (€)", "Assurance déductible (€)", "Total annuel prélevé (€)", "Capital restant fin d'année (€)"]
                        st.dataframe(df_annual.style.format({
                            "Capital remboursé (€)": "{:,.2f} €",
                            "Intérêts déductibles IS (€)": "{:,.2f} €",
                            "Assurance déductible (€)": "{:,.2f} €",
                            "Total annuel prélevé (€)": "{:,.2f} €",
                            "Capital restant fin d'année (€)": "{:,.2f} €"
                        }), use_container_width=True, hide_index=True)
                    else:
                        disp_cols = ["date", "month_num", "start_balance", "capital", "interest", "insurance", "total_monthly", "end_balance"]
                        df_m = df_sched[disp_cols].copy()
                        df_m.columns = ["Date", "Mois N°", "Capital Début (€)", "Capital (€)", "Intérêts (€)", "Assurance (€)", "Mensualité (€)", "Capital Restant (€)"]
                        st.dataframe(df_m.style.format({
                            "Capital Début (€)": "{:,.2f} €",
                            "Capital (€)": "{:,.2f} €",
                            "Intérêts (€)": "{:,.2f} €",
                            "Assurance (€)": "{:,.2f} €",
                            "Mensualité (€)": "{:,.2f} €",
                            "Capital Restant (€)": "{:,.2f} €"
                        }), height=300, use_container_width=True, hide_index=True)

                    # Suppression du prêt
                    if st.button(f"🗑️ Supprimer ce prêt #{loan['id']}", key=f"del_loan_{loan['id']}", type="secondary"):
                        execute_write("DELETE FROM loans WHERE id = ?;", [loan["id"]])
                        st.warning("Prêt supprimé avec succès.")
                        st.rerun()

    # 2. AJOUTER UN EMPRUNT
    with tab_add:
        st.markdown("#### Nouvel Emprunt Immobilier")
        all_props = query_rows("SELECT id, name FROM properties ORDER BY name ASC;")
        prop_opts = {None: "Aucun bien en particulier (Financement global SCI)"} | {p["id"]: p["name"] for p in all_props}

        with st.form("form_add_loan", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                bank_name = st.text_input("Établissement bancaire *", placeholder="ex: Crédit Agricole, BNP Paribas, CIC...")
                loan_ref = st.text_input("Numéro ou référence du prêt", placeholder="ex: PRET-IMMO-2024-8901")
                selected_prop = st.selectbox("Bien rattaché", options=list(prop_opts.keys()), format_func=lambda x: prop_opts[x])
                start_date = st.date_input("Date de la 1ère mensualité *", value=date.today()).strftime("%Y-%m-%d")

            with col2:
                amount = st.number_input("Capital initial emprunté (€) *", min_value=1000.0, value=100000.0, step=5000.0)
                rate = st.number_input("Taux d'intérêt annuel fixe (%) *", min_value=0.01, max_value=15.0, value=3.20, step=0.05)
                duration_years = st.number_input("Durée du prêt (en années) *", min_value=1, max_value=35, value=20, step=1)
                insurance = st.number_input("Cotisation mensuelle d'assurance (€)", min_value=0.0, value=25.0, step=5.0)

            notes = st.text_area("Conditions particulières / nantissement / hypothèque", placeholder="Hypothèque légale spéciale de prêteur de deniers...")

            # Aperçu en direct
            dur_m = int(duration_years * 12)
            monthly_est = calculate_monthly_payment(amount, rate, dur_m)
            st.info(f"💡 **Estimation de la mensualité :** **{monthly_est + insurance:.2f} € / mois** (hors assurance : {monthly_est:.2f} € + assurance : {insurance:.2f} €)")

            submitted = st.form_submit_button("💾 Enregistrer le prêt et générer le tableau d'amortissement", type="primary")
            if submitted:
                if not bank_name.strip():
                    st.error("Le nom de la banque est obligatoire.")
                else:
                    try:
                        execute_write("""
                            INSERT INTO loans (property_id, bank_name, loan_reference, start_date, amount, annual_interest_rate, duration_months, monthly_insurance, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """, [selected_prop, bank_name.strip(), loan_ref.strip(), start_date, amount, rate, dur_m, insurance, notes.strip()])
                        st.success(f"Emprunt de **{amount:,.2f} €** enregistré avec succès auprès de **{bank_name}** !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")
