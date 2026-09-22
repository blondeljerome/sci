"""
Vue Gestion des Loyers, Encaissements et Quittances de Loyer.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime
from database import query_rows, query_one, execute_write
from utils.quittance import generate_quittance_html, generate_quittance_pdf, save_quittance_to_ged
from utils.mailer import send_email

def render_rents():
    st.markdown("## 💳 Gestion des Loyers & Quittances")
    st.caption("Suivez les encaissements mensuels, validez les paiements et générez instantanément les quittances de loyer au format PDF archivées dans la GED.")

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

    # Récupérer les paiements du mois sélectionné avec lien vers GED (documents)
    payments = query_rows("""
        SELECT rp.*, 
               t.first_name, t.last_name, t.email,
               p.name as property_name, p.address as prop_address, p.city as prop_city, p.postal_code as prop_postal,
               d.file_path as doc_file_path, d.filename as doc_filename
        FROM rent_payments rp
        JOIN tenants t ON rp.tenant_id = t.id
        JOIN properties p ON rp.property_id = p.id
        LEFT JOIN documents d ON rp.document_id = d.id
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

        # Action groupée d'archivage GED
        paid_count = sum(1 for p in payments if (p.get("status") == "paye" or (p.get("amount_paid", 0) >= p.get("total_due", 0))))
        if paid_count > 0:
            c_bulk1, _ = st.columns([2, 1])
            with c_bulk1:
                if st.button(f"⚡ Générer & Archiver toutes les quittances PDF payées ({paid_count}) dans la GED", type="secondary"):
                    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    archived = 0
                    for p in payments:
                        is_p = p.get("status") == "paye" or (p.get("amount_paid", 0) >= p.get("total_due", 0))
                        if is_p:
                            t_info = {"id": p["tenant_id"], "first_name": p["first_name"], "last_name": p["last_name"], "email": p.get("email")}
                            pr_info = {"id": p["property_id"], "name": p["property_name"], "address": p["prop_address"], "city": p["prop_city"], "postal_code": p["prop_postal"]}
                            ok_s, _, _ = save_quittance_to_ged(p["id"], sci_info, t_info, pr_info, p)
                            if ok_s:
                                archived += 1
                    st.success(f"{archived} quittance(s) PDF archivée(s) dans la GED !")
                    st.rerun()

        st.markdown(f"### 📋 Détail des échéances ({month_names[selected_month-1]} {selected_year})")

        for p in payments:
            is_paid = p.get("status") == "paye" or (p.get("amount_paid", 0) >= p.get("total_due", 0))
            status_color = "🟢 Payé" if is_paid else ("🟠 Partiel" if p.get("amount_paid", 0) > 0 else "🔴 En attente")

            with st.container():
                st.markdown(f"#### 👤 {p['first_name']} {p['last_name'].upper()} — {p['property_name']} &nbsp; ({status_color})")
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                with c1:
                    st.write(f"**Loyer HC :** {p['rent_amount']:.2f} €")
                    st.write(f"**Charges :** {p['charges_amount']:.2f} €")
                    st.write(f"**Total Dû :** **{p['total_due']:.2f} €**")
                with c2:
                    st.write(f"**Encaissé :** {p['amount_paid']:.2f} €")
                    st.write(f"**Date encaissement :** {p['payment_date'] or 'Non réglé'}")
                    st.write(f"**Mode :** {p['payment_method']}")
                with c3:
                    # Action rapide d'encaissement avec archivage automatique GED
                    if not is_paid:
                        if st.button("💰 Encaisser en totalité", key=f"quick_pay_{p['id']}", type="primary"):
                            execute_write("""
                                UPDATE rent_payments 
                                SET amount_paid = total_due, payment_date = ?, status = 'paye'
                                WHERE id = ?;
                            """, [str(date.today()), p["id"]])
                            # Génération et archivage automatique dans la GED
                            sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                            tenant_info = {"id": p["tenant_id"], "first_name": p["first_name"], "last_name": p["last_name"], "email": p.get("email")}
                            prop_info = {"id": p["property_id"], "name": p["property_name"], "address": p["prop_address"], "city": p["prop_city"], "postal_code": p["prop_postal"]}
                            p_for_ged = dict(p)
                            p_for_ged["amount_paid"] = p["total_due"]
                            p_for_ged["payment_date"] = str(date.today())
                            p_for_ged["status"] = "paye"
                            ok_g, msg_g, _ = save_quittance_to_ged(p["id"], sci_info, tenant_info, prop_info, p_for_ged)
                            st.success(f"Paiement enregistré ! {msg_g}")
                            st.rerun()
                    else:
                        st.caption("✅ Paiement soldé")
                        if p.get("doc_file_path"):
                            if str(p["doc_file_path"]).startswith("http"):
                                st.caption(f"📎 [Quittance PDF dans la GED]({p['doc_file_path']})")
                            else:
                                st.caption("📎 Quittance archivée dans la GED")

                with c4:
                    # Action d'ouverture de la quittance
                    if st.button("📄 Quittance de Loyer", key=f"quittance_btn_{p['id']}"):
                        st.session_state[f"show_quittance_{p['id']}"] = not st.session_state.get(f"show_quittance_{p['id']}", False)

                with c5:
                    with st.popover("🗑️", help="Supprimer cette échéance de loyer"):
                        st.markdown(f"**Supprimer l'échéance #{p['id']}**")
                        st.write(f"{p['first_name']} {p['last_name']} ({month_names[selected_month-1]} {selected_year})")
                        st.write(f"Montant dû : **{p['total_due']:.2f} €**")
                        if p.get("amount_paid", 0) > 0:
                            st.warning(f"⚠️ {p['amount_paid']:.2f} € déjà encaissés !")
                        if st.button("🚨 Confirmer la suppression", type="secondary", key=f"del_single_rent_{p['id']}", use_container_width=True):
                            execute_write("DELETE FROM rent_payments WHERE id = ?;", [p["id"]])
                            st.success("Échéance supprimée avec succès !")
                            st.rerun()

                # Affichage de la quittance si demandée
                if st.session_state.get(f"show_quittance_{p['id']}", False):
                    sci_info = query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    tenant_info = {"id": p["tenant_id"], "first_name": p["first_name"], "last_name": p["last_name"], "email": p.get("email")}
                    prop_info = {"id": p["property_id"], "name": p["property_name"], "address": p["prop_address"], "city": p["prop_city"], "postal_code": p["prop_postal"]}
                    
                    html_content = generate_quittance_html(sci_info, tenant_info, prop_info, p)
                    pdf_bytes = generate_quittance_pdf(sci_info, tenant_info, prop_info, p)
                    pdf_filename = f"quittance_{p['last_name']}_{selected_year}_{selected_month:02d}.pdf"

                    st.markdown("---")
                    st.markdown(f"##### 🖨️ Quittance de Loyer PDF — {p['first_name']} {p['last_name']}")
                    
                    # Actions : Téléchargement PDF, Archivage GED, Envoi par email
                    q_col1, q_col2, q_col3 = st.columns(3)
                    with q_col1:
                        st.download_button(
                            label="📥 Télécharger la Quittance (PDF)",
                            data=pdf_bytes,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            key=f"dl_pdf_{p['id']}",
                            use_container_width=True
                        )
                    with q_col2:
                        ged_label = "✅ Quittance à jour dans la GED" if p.get("doc_file_path") else "📎 Archiver dans la GED"
                        if st.button(ged_label, key=f"btn_save_ged_{p['id']}", use_container_width=True):
                            ok_ged, msg_ged, doc_id = save_quittance_to_ged(p["id"], sci_info, tenant_info, prop_info, p)
                            if ok_ged:
                                st.success(msg_ged)
                                st.rerun()
                            else:
                                st.error(msg_ged)
                    with q_col3:
                        if p.get("email"):
                            if st.button(f"📧 Envoyer par email (PDF)", key=f"mail_quit_{p['id']}", use_container_width=True):
                                subj = f"Quittance de loyer - {month_names[selected_month-1]} {selected_year} - {sci_info.get('name', 'SCI')}"
                                ok, msg = send_email(p["email"], subj, html_content, pdf_filename, pdf_bytes)
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        else:
                            st.caption("⚠️ Locataire sans adresse email renseignée.")

                    # Affichage interactif avec iframe
                    components.html(html_content, height=600, scrolling=True)

                st.divider()

        # Outils d'administration / Suppression de loyers
        st.markdown("")
        with st.expander("🗑️ Supprimer des loyers / échéances en masse"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(f"##### Supprimer toutes les échéances de {month_names[selected_month-1]} {selected_year}")
                st.caption(f"Supprime l'ensemble des {len(payments)} échéances générées pour ce mois.")
                if st.button(f"🚨 Supprimer les {len(payments)} échéances du mois", type="secondary", key="del_all_month_rents_btn"):
                    execute_write("DELETE FROM rent_payments WHERE period_month = ? AND period_year = ?;", [selected_month, selected_year])
                    st.success(f"Échéances de {month_names[selected_month-1]} {selected_year} supprimées.")
                    st.rerun()

            with col_d2:
                st.markdown("##### Supprimer l'historique des loyers d'un locataire")
                tenants_with_rents = query_rows("""
                    SELECT t.id, t.first_name, t.last_name, COUNT(rp.id) as count_r, SUM(rp.amount_paid) as sum_paid
                    FROM tenants t
                    JOIN rent_payments rp ON t.id = rp.tenant_id
                    GROUP BY t.id
                    ORDER BY t.last_name ASC;
                """)
                if not tenants_with_rents:
                    st.info("Aucun locataire avec historique de loyer.")
                else:
                    t_rent_dict = {t["id"]: f"👤 {t['first_name']} {t['last_name']} ({t['count_r']} échéance(s) — {t['sum_paid'] or 0:.2f} € encaissés)" for t in tenants_with_rents}
                    sel_t_del = st.selectbox("Sélectionnez le locataire concerné :", options=list(t_rent_dict.keys()), format_func=lambda x: t_rent_dict[x], key="sb_del_t_rents")
                    t_to_del_obj = next((t for t in tenants_with_rents if t["id"] == sel_t_del), None)
                    if t_to_del_obj:
                        if st.button(f"🚨 Supprimer TOUS les loyers de {t_to_del_obj['first_name']} {t_to_del_obj['last_name']}", type="secondary", key=f"btn_del_rents_for_t_{sel_t_del}"):
                            execute_write("DELETE FROM rent_payments WHERE tenant_id = ?;", [sel_t_del])
                            st.success(f"L'historique de loyers de {t_to_del_obj['first_name']} {t_to_del_obj['last_name']} a été supprimé.")
                            st.rerun()
