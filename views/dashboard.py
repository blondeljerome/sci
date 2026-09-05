"""
Vue Dashboard - Synthèse financière et indicateurs clés de la SCI.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import query_df, query_rows

def render_dashboard():
    st.markdown("## 📊 Tableau de Bord Financier & Locatif")
    st.caption("Vue d'ensemble en temps réel de votre patrimoine, de vos flux de loyers et de votre trésorerie.")

    current_year = datetime.now().year
    current_month = datetime.now().month

    # 1. Requêtes de calculs des KPIs
    # Biens & Occupation
    props_df = query_df("SELECT id, name, status, target_rent, target_charges FROM properties;")
    total_props = len(props_df)
    rented_props = len(props_df[props_df["status"] == "loue"]) if total_props > 0 else 0
    vacant_props = len(props_df[props_df["status"] == "vacant"]) if total_props > 0 else 0
    occ_rate = (rented_props / total_props * 100) if total_props > 0 else 0.0

    # Loyers de l'année en cours
    rents_year_df = query_df(
        "SELECT rent_amount, charges_amount, total_due, amount_paid, status, period_month, period_year "
        "FROM rent_payments WHERE period_year = ?;", [current_year]
    )
    total_collected_year = rents_year_df["amount_paid"].sum() if not rents_year_df.empty else 0.0
    
    # Loyers en retard ou en attente
    late_rents_df = query_df(
        """
        SELECT rp.id, p.name as prop_name, t.first_name || ' ' || t.last_name as tenant_name,
               rp.period_month, rp.period_year, rp.total_due, rp.amount_paid, (rp.total_due - rp.amount_paid) as balance,
               rp.status, rp.due_date
        FROM rent_payments rp
        JOIN tenants t ON rp.tenant_id = t.id
        JOIN properties p ON rp.property_id = p.id
        WHERE rp.status IN ('en_attente', 'retard', 'partiel')
        ORDER BY rp.due_date ASC;
        """
    )
    total_unpaid = late_rents_df["balance"].sum() if not late_rents_df.empty else 0.0

    # Dépenses de l'année en cours
    sci_exp_df = query_df("SELECT amount, category, date FROM sci_expenses WHERE strftime('%Y', date) = ?;", [str(current_year)])
    prop_exp_df = query_df("SELECT amount, category, date, is_recoverable FROM property_expenses WHERE strftime('%Y', date) = ?;", [str(current_year)])
    
    total_sci_exp = sci_exp_df["amount"].sum() if not sci_exp_df.empty else 0.0
    total_prop_exp = prop_exp_df["amount"].sum() if not prop_exp_df.empty else 0.0
    total_expenses = total_sci_exp + total_prop_exp
    net_cashflow = total_collected_year - total_expenses

    # 2. Affichage des Métriques Clés (Cartes)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label=f"Loyers Encaissés ({current_year})",
            value=f"{total_collected_year:,.2f} €".replace(",", " "),
            help="Total des loyers et charges effectivement perçus cette année."
        )
    with col2:
        st.metric(
            label="Total Dépenses de l'Exercice",
            value=f"{total_expenses:,.2f} €".replace(",", " "),
            delta=f"-{total_expenses:,.2f} €" if total_expenses > 0 else "0 €",
            delta_color="inverse",
            help="Somme des charges SCI (emprunts, assurances, gestion) et charges d'appartements."
        )
    with col3:
        st.metric(
            label="Cash-Flow Net Trésorerie",
            value=f"{net_cashflow:,.2f} €".replace(",", " "),
            delta=f"{net_cashflow:+,.2f} €".replace(",", " "),
            delta_color="normal" if net_cashflow >= 0 else "inverse",
            help="Loyers encaissés - Ensemble des dépenses réelles."
        )
    with col4:
        st.metric(
            label="Taux d'Occupation",
            value=f"{occ_rate:.1f} %",
            delta=f"{rented_props}/{total_props} biens loués",
            delta_color="off",
            help="Pourcentage de lots actuellement occupés par un locataire actif."
        )

    st.markdown("---")

    # 3. Alertes / Loyers en retard
    if not late_rents_df.empty:
        st.warning(f"⚠️ **{len(late_rents_df)} échéance(s) en attente ou impayée(s)** pour un montant total de **{total_unpaid:,.2f} €**.")
        with st.expander("Voir le détail des loyers non soldés", expanded=True):
            display_df = late_rents_df[["tenant_name", "prop_name", "period_month", "period_year", "total_due", "amount_paid", "balance", "status", "due_date"]].copy()
            display_df.columns = ["Locataire", "Bien", "Mois", "Année", "Total Dû (€)", "Payé (€)", "Solde Restant (€)", "Statut", "Échéance"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.success("🎉 Tous les loyers générés sont actuellement à jour !")

    st.markdown("### 📈 Analyse Visuelle des Flux")
    g_col1, g_col2 = st.columns([3, 2])

    with g_col1:
        st.markdown("#### Évolution Mensuelle des Flux")
        # Préparer le tableau des 12 mois
        months = list(range(1, 13))
        month_names = ["Jan", "Fév", "Mar", "Avr", "Mai", "Juin", "Juil", "Août", "Sep", "Oct", "Nov", "Déc"]
        
        income_by_month = [0.0] * 12
        if not rents_year_df.empty:
            for _, r in rents_year_df.iterrows():
                m = int(r["period_month"]) - 1
                if 0 <= m < 12:
                    income_by_month[m] += float(r["amount_paid"])

        expenses_by_month = [0.0] * 12
        # Charges SCI
        for _, r in sci_exp_df.iterrows():
            try:
                dt = datetime.strptime(str(r["date"])[:10], "%Y-%m-%d")
                expenses_by_month[dt.month - 1] += float(r["amount"])
            except Exception:
                pass
        # Charges Lots
        for _, r in prop_exp_df.iterrows():
            try:
                dt = datetime.strptime(str(r["date"])[:10], "%Y-%m-%d")
                expenses_by_month[dt.month - 1] += float(r["amount"])
            except Exception:
                pass

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=month_names,
            y=income_by_month,
            name="Recettes (Loyers perçus)",
            marker_color="#2563eb"
        ))
        fig_bar.add_trace(go.Bar(
            x=month_names,
            y=expenses_by_month,
            name="Dépenses (SCI + Lots)",
            marker_color="#ef4444"
        ))
        fig_bar.update_layout(
            barmode='group',
            margin=dict(l=20, r=20, t=30, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=320
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with g_col2:
        st.markdown("#### Répartition des Dépenses")
        # Fusionner les catégories de dépenses
        exp_list = []
        if not sci_exp_df.empty:
            for _, r in sci_exp_df.iterrows():
                exp_list.append({"Catégorie": r["category"], "Montant": float(r["amount"])})
        if not prop_exp_df.empty:
            for _, r in prop_exp_df.iterrows():
                exp_list.append({"Catégorie": f"Lot - {r['category']}", "Montant": float(r["amount"])})

        if exp_list:
            all_exp_df = pd.DataFrame(exp_list).groupby("Catégorie", as_index=False).sum()
            fig_pie = px.pie(
                all_exp_df,
                values="Montant",
                names="Catégorie",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_pie.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=320,
                showlegend=True
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Aucune dépense enregistrée sur cette année pour générer la ventilation.")
