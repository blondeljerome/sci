"""
Vue Gestion des Charges Spécifiques des Lots et Régularisation Annuelle des Charges.
"""
import streamlit as st
import pandas as pd
from datetime import date
from database import query_rows, query_one, execute_write

CATEGORIES_LOT = [
    "Charges de copropriété (Appel de fonds)",
    "Taxe d'enlèvement des ordures ménagères (TEOM)",
    "Eau froide / chaude collective",
    "Chauffage collectif",
    "Petites réparations locatives",
    "Travaux privatifs propriétaire",
    "Autre charge de lot"
]

def render_property_expenses():
    st.markdown("## 🏠 Charges des Lots & Régularisations")
    st.caption("Gérez les charges d'immeuble ou de copropriété spécifiques à chaque lot et calculez les régularisations annuelles de charges locatives.")

    tab_list, tab_add, tab_regu = st.tabs(["📋 Dépenses par Bien", "➕ Enregistrer une Dépense", "⚖️ Régularisation Annuelle"])

    # 1. LISTE DES DEPENSES DE LOTS
    with tab_list:
        all_props = query_rows("SELECT id, name FROM properties ORDER BY name ASC;")
        if not all_props:
            st.info("Aucun bien enregistré.")
        else:
            col_p, col_y = st.columns([2, 1])
            with col_p:
                prop_map = {0: "Tous les biens"} | {p["id"]: p["name"] for p in all_props}
                filter_prop_id = st.selectbox("Sélectionnez le bien", options=list(prop_map.keys()), format_func=lambda x: prop_map[x], key="pe_filter_prop")
            with col_y:
                current_year = date.today().year
                filter_year = st.selectbox("Année", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_year), key="pe_filter_year")

            query = """
                SELECT pe.*, p.name as property_name,
                       t.first_name || ' ' || t.last_name as tenant_name
                FROM property_expenses pe
                JOIN properties p ON pe.property_id = p.id
                LEFT JOIN tenants t ON pe.tenant_id = t.id
                WHERE strftime('%Y', pe.date) = ?
            """
            params = [str(filter_year)]
            if filter_prop_id != 0:
                query += " AND pe.property_id = ?"
                params.append(filter_prop_id)
            query += " ORDER BY pe.date DESC;"

            expenses = query_rows(query, params)

            if not expenses:
                st.info("Aucune charge enregistrée pour cette sélection.")
            else:
                exp_df = pd.DataFrame(expenses)
                tot_amt = exp_df["amount"].sum()
                recov_amt = exp_df[exp_df["is_recoverable"] == 1]["amount"].sum()
                non_recov = tot_amt - recov_amt

                c1, c2, c3 = st.columns(3)
                c1.metric("Total Dépenses Lots", f"{tot_amt:,.2f} €".replace(",", " "))
                c2.metric("Récupérable (Locataire)", f"{recov_amt:,.2f} €".replace(",", " "), help="Charges incombant légalement au locataire (TEOM, eau, ascenseur...)")
                c3.metric("Non Récupérable (Bailleur)", f"{non_recov:,.2f} €".replace(",", " "), help="Charges restant à la charge du propriétaire (gros travaux, syndic...)")

                st.markdown("---")
                disp = exp_df[["date", "property_name", "category", "description", "amount", "is_recoverable", "tenant_name"]].copy()
                disp["is_recoverable"] = disp["is_recoverable"].apply(lambda x: "🟢 Oui" if x == 1 else "⚪ Non")
                disp.columns = ["Date", "Bien", "Catégorie", "Description", "Montant (€)", "Récupérable ?", "Locataire imputé"]
                st.dataframe(disp, use_container_width=True, hide_index=True)

    # 2. ENREGISTRER UNE DEPENSE DE LOT
    with tab_add:
        all_props = query_rows("SELECT id, name FROM properties ORDER BY name ASC;")
        if not all_props:
            st.info("Veuillez d'abord créer au moins un bien dans l'onglet 'Patrimoine'.")
        else:
            st.markdown("#### Saisir une Charge relative à un Lot")
            with st.form("form_add_prop_exp", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    prop_choices = {p["id"]: p["name"] for p in all_props}
                    selected_prop = st.selectbox("Bien concerné *", options=list(prop_choices.keys()), format_func=lambda x: prop_choices[x])
                    exp_date = st.date_input("Date de la dépense *", value=date.today()).strftime("%Y-%m-%d")
                    category = st.selectbox("Catégorie de dépense *", CATEGORIES_LOT)
                    amount = st.number_input("Montant (€) *", min_value=0.01, value=65.0, step=5.0)

                with c2:
                    is_recoverable = st.checkbox("Charge Récupérable sur le locataire", value=True, help="Cocher s'il s'agit de TEOM, d'eau, de charges locatives de copropriété...")
                    # Locataires rattachés à ce bien
                    tenants_prop = query_rows("SELECT id, first_name, last_name, is_active FROM tenants WHERE property_id = ? ORDER BY is_active DESC;", [selected_prop])
                    tenant_choices = {None: "Aucun (charge globale au lot)"} | {t["id"]: f"{t['first_name']} {t['last_name']} ({'Actuel' if t['is_active'] else 'Ancien'})" for t in tenants_prop}
                    selected_tenant = st.selectbox("Locataire associé pour régularisation", options=list(tenant_choices.keys()), format_func=lambda x: tenant_choices[x])
                    invoice_ref = st.text_input("Référence facture / appel de fonds syndic")

                description = st.text_input("Description / Libellé de la dépense *", placeholder="ex: Appel de charges copropriété T3 2026 - part locative")
                notes = st.text_area("Notes", placeholder="Détail du décompte...")

                submitted = st.form_submit_button("💾 Enregistrer la charge", type="primary")
                if submitted:
                    if not description.strip():
                        st.error("La description est obligatoire.")
                    else:
                        try:
                            execute_write("""
                                INSERT INTO property_expenses (property_id, date, category, description, amount, is_recoverable, tenant_id, invoice_ref, notes)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """, [selected_prop, exp_date, category, description.strip(), amount, 1 if is_recoverable else 0, selected_tenant, invoice_ref.strip(), notes.strip()])
                            st.success(f"Dépense de **{amount:.2f} €** enregistrée !")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erreur : {e}")

    # 3. REGULARISATION ANNUELLE DES CHARGES
    with tab_regu:
        st.markdown("#### ⚖️ Décompte & Régularisation des Charges Locatives")
        st.caption("Ce module compare les provisions mensuelles pour charges encaissées et les dépenses réelles récupérables payées pour un locataire.")

        all_tenants = query_rows("""
            SELECT t.id, t.first_name, t.last_name, t.property_id, p.name as property_name
            FROM tenants t
            JOIN properties p ON t.property_id = p.id
            ORDER BY t.last_name ASC;
        """)

        if not all_tenants:
            st.info("Aucun locataire enregistré pour effectuer une régularisation.")
        else:
            col_t, col_yr = st.columns([2, 1])
            with col_t:
                tenant_map = {t["id"]: f"{t['first_name']} {t['last_name']} — {t['property_name']}" for t in all_tenants}
                sel_tenant_id = st.selectbox("Locataire à régulariser :", options=list(tenant_map.keys()), format_func=lambda x: tenant_map[x])
            with col_yr:
                current_year = date.today().year
                regu_year = st.selectbox("Année d'exercice", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_year), key="regu_yr")

            selected_t = next((t for t in all_tenants if t["id"] == sel_tenant_id), None)
            
            if selected_t:
                # 1. Somme des provisions de charges perçues pour cette année
                provisions_rows = query_rows("""
                    SELECT period_month, charges_amount, amount_paid, total_due, status
                    FROM rent_payments
                    WHERE tenant_id = ? AND period_year = ? AND status IN ('paye', 'partiel');
                """, [sel_tenant_id, regu_year])

                total_provisions_collected = sum(r["charges_amount"] for r in provisions_rows)

                # 2. Somme des charges réelles récupérables enregistrées pour ce lot / locataire sur cette année
                real_expenses = query_rows("""
                    SELECT date, category, description, amount
                    FROM property_expenses
                    WHERE (tenant_id = ? OR (property_id = ? AND tenant_id IS NULL))
                      AND is_recoverable = 1
                      AND strftime('%Y', date) = ?;
                """, [sel_tenant_id, selected_t["property_id"], str(regu_year)])

                total_real_recoverable = sum(r["amount"] for r in real_expenses)

                # Calcul du solde
                diff_balance = total_real_recoverable - total_provisions_collected

                st.markdown("---")
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric(
                    f"Provisions Perçues ({regu_year})",
                    f"{total_provisions_collected:,.2f} €".replace(",", " "),
                    help=f"Total des avances de charges versées par le locataire sur {len(provisions_rows)} mois."
                )
                rc2.metric(
                    f"Charges Réelles Récupérables",
                    f"{total_real_recoverable:,.2f} €".replace(",", " "),
                    help="Dépenses réelles justifiées par des factures (eau, TEOM, charges locatives)."
                )

                if diff_balance > 0:
                    rc3.metric(
                        "Solde : Complément Dû",
                        f"+{diff_balance:,.2f} €".replace(",", " "),
                        delta=f"À réclamer au locataire",
                        delta_color="normal"
                    )
                    st.warning(f"👉 **Régularisation défavorable au locataire** : Les charges réelles dépassent les provisions versées de **{diff_balance:,.2f} €**. Vous pouvez lui envoyer un appel de complément.")
                elif diff_balance < 0:
                    rc3.metric(
                        "Solde : Trop-Perçu",
                        f"{diff_balance:,.2f} €".replace(",", " "),
                        delta=f"À rembourser au locataire",
                        delta_color="inverse"
                    )
                    st.info(f"👉 **Trop-perçu en faveur du locataire** : Les provisions perçues ont dépassé les dépenses réelles de **{abs(diff_balance):,.2f} €**. Vous devez lui rembourser ou déduire ce montant du prochain terme.")
                else:
                    rc3.metric("Solde : Équilibré", "0.00 €")
                    st.success("Les provisions correspondent exactement aux dépenses réelles !")

                # Détail des dépenses réelles récupérables
                if real_expenses:
                    with st.expander("Détail des pièces comptables récupérables prises en compte", expanded=True):
                        st.dataframe(pd.DataFrame(real_expenses), use_container_width=True, hide_index=True)
                else:
                    st.info("Aucune dépense récupérable enregistrée pour ce lot sur cette année.")
