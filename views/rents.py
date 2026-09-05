"""
Vue Gestion des Loyers, Encaissements et Quittances de Loyer.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
from database import query_rows, query_one, execute_write
from utils.quittance import generate_quittance_html

def render_rents():
    st.markdown("## 💳 Gestion des Loyers & Quittances")
    st.caption("Suivez les encaissements mensuels, validez les paiements et générez instantanément les quittances de loyer conformes.")

    current_date = date.today()
    col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
    with col_s1:
        selected_year = st.selectbox("Année", list(range(2023, 2031)), index=list(range(2023, 2031)).index(current_date.year))
    with col_s2:
        month_names = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
        selected_month = st.selectbox("Mois", list(range(1, 13)), index=current_date.month - 1, format_func=lambda m: month_names[m-1])
    with col_s3:
        st.write("")
        st.write("")
        # Bouton de génération automatique du terme
        if st.button("⚡ Générer les échéances du mois pour tous les locataires actifs", type="primary"):
            active_tenants = query_rows("SELECT * FROM tenants WHERE is_active = 1 AND property_id IS NOT NULL;")
            generated_count = 0
            for t in active_tenants:
                # Vérifier si l'échéance existe déjà
                existing = query_one(
                    "SELECT id FROM rent_payments WHERE tenant_id = ? AND period_month = ? AND period_year = ?;",
                    [t["id"], selected_month, selected_year]
                )
                if not existing:
                    rent = float(t.get("rent_amount", 0.0))
                    charges = float(t.get("charges_provision", 0.0))
                    total = rent + charges
                    due_date_str = f"{selected_year:04d}-{selected_month:02d}-05"
                    execute_write("""
                        INSERT INTO rent_payments (tenant_id, property_id, period_month, period_year, due_date, rent_amount, charges_amount, total_due, amount_paid, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 'en_attente');
                    """, [t["id"], t["property_id"], selected_month, selected_year, due_date_str, rent, charges, total])
                    generated_count += 1
            if generated_count > 0:
                st.success(f"{generated_count} échéance(s) générée(s) avec succès pour {month_names[selected_month-1]} {selected_year} !")
            else:
                st.info(f"Toutes les échéances pour {month_names[selected_month-1]} {selected_year} sont déjà créées.")
            st.rerun()

    st.markdown("---")

    # Récupérer les paiements du mois sélectionné
    payments = query_rows("""
        SELECT rp.*, 
               t.first_name, t.last_name, t.email,
               p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal
        FROM rent_payments rp
        JOIN tenants t ON rp.tenant_id = t.id
        JOIN properties p ON rp.property_id = p.id
        WHERE rp.period_month = ? AND rp.period_year = ?
        ORDER BY t.last_name ASC;
    """, [selected_month, selected_year])

    if not payments:
        st.info(f"Aucune échéance enregistrée pour **{month_names[selected_month-1]} {selected_year}**. Cliquez sur le bouton ci-dessus pour générer les loyers.")
    else:
        # Résumé du mois
        total_expected = sum(p["total_due"] for p in payments)
        total_collected = sum(p["amount_paid"] for p in payments)
        total_pending = total_expected - total_collected

        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Attendu", f"{total_expected:,.2f} €".replace(",", " "))
        m_col2.metric("Total Encaissé", f"{total_collected:,.2f} €".replace(",", " "), delta=f"{total_collected/total_expected*100:.1f}%" if total_expected > 0 else "0%")
        m_col3.metric("Reste à Percevoir", f"{total_pending:,.2f} €".replace(",", " "), delta_color="inverse")

        st.markdown(f"### 📋 Détail des échéances ({month_names[selected_month-1]} {selected_year})")

        for p in payments:
            is_paid = p.get("status") == "paye" or (p.get("amount_paid", 0) >= p.get("total_due", 0))
            status_color = "🟢 Payé" if is_paid else ("🟠 Partiel" if p.get("amount_paid", 0) > 0 else "🔴 En attente")

            with st.container():
                st.markdown(f"#### 👤 {p['first_name']} {p['last_name'].upper()} — {p['property_name']} &nbsp; ({status_color})")
                c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
                with c1:
                    st.write(f"**Loyer HC :** {p['rent_amount']:.2f} €")
                    st.write(f"**Charges :** {p['charges_amount']:.2f} €")
                    st.write(f"**Total Dû :** **{p['total_due']:.2f} €**")
                with c2:
                    st.write(f"**Encaissé :** {p['amount_paid']:.2f} €")
                    st.write(f"**Date encaissement :** {p['payment_date'] or 'Non réglé'}")
                    st.write(f"**Mode :** {p['payment_method']}")
                with c3:
                    # Action rapide d'encaissement
                    if not is_paid:
                        if st.button("💰 Encaisser en totalité", key=f"quick_pay_{p['id']}", type="primary"):
                            execute_write("""
                                UPDATE rent_payments 
                                SET amount_paid = total_due, payment_date = ?, status = 'paye'
                                WHERE id = ?;
                            """, [str(date.today()), p["id"]])
                            st.success("Paiement enregistré !")
                            st.rerun()
                    else:
                        st.caption("✅ Paiement soldé")

                with c4:
                    # Action d'ouverture de la quittance
                    if st.button("📄 Quittance de Loyer", key=f"quittance_btn_{p['id']}"):
                        st.session_state[f"show_quittance_{p['id']}"] = not st.session_state.get(f"show_quittance_{p['id']}", False)

                # Affichage de la quittance si demandée
                if st.session_state.get(f"show_quittance_{p['id']}", False):
                    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    tenant_info = {"first_name": p["first_name"], "last_name": p["last_name"], "email": p.get("email")}
                    prop_info = {"name": p["property_name"], "address": p["prop_address"], "city": p["prop_city"], "postal_code": p["prop_postal"]}
                    
                    html_content = generate_quittance_html(sci_info, tenant_info, prop_info, p)

                    st.markdown("---")
                    st.markdown(f"##### 🖨️ Prévisualisation de la Quittance — {p['first_name']} {p['last_name']}")
                    
                    # Bouton de téléchargement direct du fichier HTML
                    filename = f"quittance_{p['last_name']}_{selected_year}_{selected_month:02d}.html"
                    st.download_button(
                        label="💾 Télécharger le fichier Quittance (HTML imprimable)",
                        data=html_content,
                        file_name=filename,
                        mime="text/html",
                        key=f"dl_quit_{p['id']}"
                    )
                    
                    # Affichage interactif avec iframe
                    components.html(html_content, height=650, scrolling=True)

                st.divider()
