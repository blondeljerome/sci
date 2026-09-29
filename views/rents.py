"""
Vue Gestion des Loyers, Encaissements et Quittances de Loyer.
"""

from datetime import date

import streamlit as st
import streamlit.components.v1 as components

from database import execute_write, query_one, query_rows
from services.rent_service import (
    generate_monthly_term,
    get_monthly_payments,
    record_full_payment,
)
from utils import storage
from utils.formatters import (
    format_currency,
    format_percentage,
    get_month_name,
)
from utils.legal_docs import (
    generate_avis_echeance_html,
    generate_avis_echeance_pdf,
    save_avis_echeance_to_ged,
)
from utils.mailer import send_email
from utils.quittance import (
    generate_quittance_html,
    generate_quittance_pdf,
    save_quittance_to_ged,
)


def render_rents() -> None:
    """Affiche la vue de gestion des loyers, appels et quittances."""
    st.markdown("## 💳 Gestion des Loyers, Appels & Quittances")
    st.caption(
        "Suivez les encaissements mensuels, émettez les appels de loyer et "
        "quittances au format PDF archivés dans la GED par locataire."
    )

    current_date = date.today()
    col_s1, col_s2, col_s3 = st.columns([1, 1, 2])
    with col_s1:
        selected_year = st.selectbox(
            "Année",
            list(range(2023, 2031)),
            index=list(range(2023, 2031)).index(current_date.year),
        )
    with col_s2:
        selected_month = st.selectbox(
            "Mois",
            list(range(1, 13)),
            index=current_date.month - 1,
            format_func=get_month_name,
        )
    with col_s3:
        st.write("")
        st.write("")
        # Bouton de génération automatique du terme avec archivage GED
        if st.button(
            "⚡ Générer les échéances & Appels de loyer (GED) pour "
            "les locataires actifs",
            type="primary",
        ):
            generated_count, _ = generate_monthly_term(
                selected_month, selected_year
            )
            m_name = get_month_name(selected_month)
            if generated_count > 0:
                st.success(
                    f"{generated_count} échéance(s) et appel(s) de loyer "
                    f"PDF archivé(s) dans la GED pour {m_name} "
                    f"{selected_year} !"
                )
            else:
                st.info(
                    f"Toutes les échéances pour {m_name} {selected_year} "
                    "sont déjà créées."
                )
            st.rerun()

    st.markdown("---")

    # Récupérer les paiements du mois sélectionné avec liens GED
    payments = get_monthly_payments(selected_month, selected_year)

    if not payments:
        m_name = get_month_name(selected_month)
        st.info(
            f"Aucune échéance enregistrée pour **{m_name} {selected_year}**. "
            "Cliquez sur le bouton ci-dessus pour générer les loyers."
        )
    else:
        # Résumé du mois
        total_expected = sum(p["total_due"] for p in payments)
        total_collected = sum(p["amount_paid"] for p in payments)
        total_pending = total_expected - total_collected

        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("Total Attendu", format_currency(total_expected))
        pct_str = (
            format_percentage(total_collected / total_expected * 100)
            if total_expected > 0
            else "0%"
        )
        m_col2.metric(
            "Total Encaissé", format_currency(total_collected), delta=pct_str
        )
        m_col3.metric(
            "Reste à Percevoir",
            format_currency(total_pending),
            delta_color="inverse",
        )

        # Actions groupées d'archivage GED (Appels et Quittances)
        c_bulk1, c_bulk2 = st.columns(2)
        with c_bulk1:
            btn_appels_lbl = (
                f"📤 Archiver tous les appels de loyer PDF "
                f"({len(payments)}) dans la GED"
            )
            if st.button(
                btn_appels_lbl,
                type="secondary",
                key="bulk_save_appels_ged",
                use_container_width=True,
            ):
                sci_info = (
                    query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                )
                archived_notices = 0
                for p in payments:
                    t_info = {
                        "id": p["tenant_id"],
                        "first_name": p["first_name"],
                        "last_name": p["last_name"],
                        "email": p.get("email"),
                    }
                    pr_info = {
                        "id": p["property_id"],
                        "name": p["property_name"],
                        "address": p["prop_address"],
                        "city": p["prop_city"],
                        "postal_code": p["prop_postal"],
                    }
                    ok_n, _, _ = save_avis_echeance_to_ged(
                        sci_info,
                        t_info,
                        pr_info,
                        selected_month,
                        selected_year,
                        p["due_date"],
                        p["rent_amount"],
                        p["charges_amount"],
                        p["id"],
                    )
                    if ok_n:
                        archived_notices += 1
                st.success(
                    f"{archived_notices} appel(s) de loyer PDF archivé(s) "
                    "dans la GED !"
                )
                st.rerun()

        with c_bulk2:
            paid_count = sum(
                1
                for p in payments
                if (
                    p.get("status") == "paye"
                    or (p.get("amount_paid", 0) >= p.get("total_due", 0))
                )
            )
            if paid_count > 0:
                btn_quittances_lbl = (
                    f"⚡ Archiver toutes les quittances PDF payées "
                    f"({paid_count}) dans la GED"
                )
                if st.button(
                    btn_quittances_lbl,
                    type="secondary",
                    key="bulk_save_quittances_ged",
                    use_container_width=True,
                ):
                    sci_info = (
                        query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    )
                    archived = 0
                    for p in payments:
                        is_p = p.get("status") == "paye" or (
                            p.get("amount_paid", 0) >= p.get("total_due", 0)
                        )
                        if is_p:
                            t_info = {
                                "id": p["tenant_id"],
                                "first_name": p["first_name"],
                                "last_name": p["last_name"],
                                "email": p.get("email"),
                            }
                            pr_info = {
                                "id": p["property_id"],
                                "name": p["property_name"],
                                "address": p["prop_address"],
                                "city": p["prop_city"],
                                "postal_code": p["prop_postal"],
                            }
                            ok_s, _, _ = save_quittance_to_ged(
                                p["id"], sci_info, t_info, pr_info, p
                            )
                            if ok_s:
                                archived += 1
                    st.success(
                        f"{archived} quittance(s) PDF archivée(s) dans la GED !"
                    )
                    st.rerun()

        m_name = get_month_name(selected_month)
        st.markdown(
            f"### 📋 Détail des échéances ({m_name} {selected_year})"
        )

        for p in payments:
            is_paid = p.get("status") == "paye" or (
                p.get("amount_paid", 0) >= p.get("total_due", 0)
            )
            status_color = (
                "🟢 Payé"
                if is_paid
                else (
                    "🟠 Partiel"
                    if p.get("amount_paid", 0) > 0
                    else "🔴 En attente"
                )
            )

            with st.container():
                t_nom = f"{p['first_name']} {p['last_name'].upper()}"
                st.markdown(
                    f"#### 👤 {t_nom} — {p['property_name']} &nbsp; "
                    f"({status_color})"
                )
                c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 1])
                with c1:
                    st.write(
                        f"**Loyer HC :** {format_currency(p['rent_amount'])}"
                    )
                    st.write(
                        f"**Charges :** {format_currency(p['charges_amount'])}"
                    )
                    st.write(
                        f"**Total Dû :** **{format_currency(p['total_due'])}**"
                    )
                with c2:
                    p_date = p["payment_date"] or "Non réglé"
                    st.write(
                        f"**Encaissé :** {format_currency(p['amount_paid'])}"
                    )
                    st.write(f"**Date encaissement :** {p_date}")
                    st.write(f"**Mode :** {p['payment_method']}")
                with c3:
                    # Action rapide d'encaissement avec archivage GED auto
                    if not is_paid:
                        if st.button(
                            "💰 Encaisser en totalité",
                            key=f"quick_pay_{p['id']}",
                            type="primary",
                        ):
                            ok_g, msg_g = record_full_payment(p["id"])
                            if ok_g:
                                st.success(f"Paiement enregistré ! {msg_g}")
                            else:
                                st.error(f"Erreur d'encaissement : {msg_g}")
                            st.rerun()
                    else:
                        st.caption("✅ Paiement soldé")

                    # Référencement et liens directs GED (Cloudinary)
                    if p.get("notice_public_id") or p.get("notice_file_path"):
                        notice_preview = storage.get_preview_url(
                            p.get("notice_public_id"), p.get("notice_file_path")
                        )
                        st.markdown(
                            f"📄 [**Voir Appel GED**]({notice_preview})"
                        )
                    if p.get("doc_public_id") or p.get("doc_file_path"):
                        doc_preview = storage.get_preview_url(
                            p.get("doc_public_id"), p.get("doc_file_path")
                        )
                        st.markdown(
                            f"📑 [**Voir Quittance GED**]({doc_preview})"
                        )

                with c4:
                    col_b1, col_b2 = st.columns(2)
                    with col_b1:
                        btn_appel_label = "📤 Appel"
                        if st.button(
                            btn_appel_label,
                            key=f"btn_appel_{p['id']}",
                            help="Afficher / Télécharger l'Appel de Loyer",
                        ):
                            st.session_state[
                                f"show_appel_{p['id']}"
                            ] = not st.session_state.get(
                                f"show_appel_{p['id']}", False
                            )
                            st.session_state[f"show_quittance_{p['id']}"] = (
                                False
                            )
                    with col_b2:
                        btn_quit_label = "📄 Quittance"
                        if st.button(
                            btn_quit_label,
                            key=f"quittance_btn_{p['id']}",
                            help="Afficher / Télécharger la Quittance",
                        ):
                            st.session_state[
                                f"show_quittance_{p['id']}"
                            ] = not st.session_state.get(
                                f"show_quittance_{p['id']}", False
                            )
                            st.session_state[f"show_appel_{p['id']}"] = False

                with c5:
                    with st.popover(
                        "🗑️", help="Supprimer cette échéance de loyer"
                    ):
                        st.markdown(f"**Supprimer l'échéance #{p['id']}**")
                        m_nm = get_month_name(selected_month)
                        st.write(
                            f"{p['first_name']} {p['last_name']} "
                            f"({m_nm} {selected_year})"
                        )
                        st.write(
                            f"Montant dû : "
                            f"**{format_currency(p['total_due'])}**"
                        )
                        if p.get("amount_paid", 0) > 0:
                            paid_f = format_currency(p['amount_paid'])
                            st.warning(f"⚠️ {paid_f} déjà encaissés !")
                        if st.button(
                            "🚨 Confirmer la suppression",
                            type="secondary",
                            key=f"del_single_rent_{p['id']}",
                            use_container_width=True,
                        ):
                            execute_write(
                                "DELETE FROM rent_payments WHERE id = ?;",
                                [p["id"]],
                            )
                            st.success("Échéance supprimée avec succès !")
                            st.rerun()

                # Affichage de l'Appel de Loyer si demandé
                if st.session_state.get(f"show_appel_{p['id']}", False):
                    sci_info = (
                        query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    )
                    tenant_info = {
                        "id": p["tenant_id"],
                        "first_name": p["first_name"],
                        "last_name": p["last_name"],
                        "email": p.get("email"),
                    }
                    prop_info = {
                        "id": p["property_id"],
                        "name": p["property_name"],
                        "address": p["prop_address"],
                        "city": p["prop_city"],
                        "postal_code": p["prop_postal"],
                    }

                    html_notice = generate_avis_echeance_html(
                        sci_info,
                        tenant_info,
                        prop_info,
                        selected_month,
                        selected_year,
                        p["due_date"],
                        p["rent_amount"],
                        p["charges_amount"],
                    )
                    pdf_notice = generate_avis_echeance_pdf(
                        sci_info,
                        tenant_info,
                        prop_info,
                        selected_month,
                        selected_year,
                        p["due_date"],
                        p["rent_amount"],
                        p["charges_amount"],
                        p["id"],
                    )
                    t_ln = p["last_name"]
                    pdf_notice_filename = (
                        f"appel_loyer_{t_ln}_{selected_year}_"
                        f"{selected_month:02d}.pdf"
                    )

                    st.markdown("---")
                    st.markdown(
                        f"##### 📤 Avis d'Échéance / Appel de Loyer (PDF) — "
                        f"{p['first_name']} {p['last_name']}"
                    )

                    an_col1, an_col2, an_col3 = st.columns(3)
                    with an_col1:
                        # Téléchargement direct depuis GED Cloudinary si archivé
                        ged_notice_bytes = None
                        if p.get("notice_public_id"):
                            ged_notice_bytes = storage.download_file_bytes(
                                p["notice_public_id"]
                            )
                        dl_notice_data = (
                            ged_notice_bytes if ged_notice_bytes else pdf_notice
                        )
                        st.download_button(
                            label="📥 Télécharger l'Appel (GED)"
                            if ged_notice_bytes
                            else "📥 Télécharger l'Appel (PDF)",
                            data=dl_notice_data,
                            file_name=pdf_notice_filename,
                            mime="application/pdf",
                            key=f"dl_notice_pdf_{p['id']}",
                            use_container_width=True,
                        )
                    with an_col2:
                        ged_notice_label = (
                            "✅ Appel à jour dans la GED"
                            if p.get("notice_file_path")
                            else "📎 Archiver l'appel dans la GED"
                        )
                        if st.button(
                            ged_notice_label,
                            key=f"btn_save_notice_ged_{p['id']}",
                            use_container_width=True,
                        ):
                            ok_n, msg_n, _ = save_avis_echeance_to_ged(
                                sci_info,
                                tenant_info,
                                prop_info,
                                selected_month,
                                selected_year,
                                p["due_date"],
                                p["rent_amount"],
                                p["charges_amount"],
                                p["id"],
                            )
                            if ok_n:
                                st.success(msg_n)
                                st.rerun()
                            else:
                                st.error(msg_n)
                    with an_col3:
                        if p.get("email"):
                            if st.button(
                                "📧 Envoyer l'appel par email (PDF)",
                                key=f"mail_notice_{p['id']}",
                                use_container_width=True,
                            ):
                                sci_nom = sci_info.get("name", "SCI")
                                subj = (
                                    f"Avis d'échéance - Loyer {m_nm} "
                                    f"{selected_year} - {sci_nom}"
                                )
                                ok, msg = send_email(
                                    p["email"],
                                    subj,
                                    html_notice,
                                    pdf_notice_filename,
                                    pdf_notice,
                                )
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        else:
                            st.caption(
                                "⚠️ Locataire sans adresse email renseignée."
                            )

                    components.html(html_notice, height=520, scrolling=True)

                # Affichage de la quittance si demandée
                if st.session_state.get(f"show_quittance_{p['id']}", False):
                    sci_info = (
                        query_one("SELECT * FROM sci_info WHERE id = 1;") or {}
                    )
                    tenant_info = {
                        "id": p["tenant_id"],
                        "first_name": p["first_name"],
                        "last_name": p["last_name"],
                        "email": p.get("email"),
                    }
                    prop_info = {
                        "id": p["property_id"],
                        "name": p["property_name"],
                        "address": p["prop_address"],
                        "city": p["prop_city"],
                        "postal_code": p["prop_postal"],
                    }

                    html_content = generate_quittance_html(
                        sci_info, tenant_info, prop_info, p
                    )
                    pdf_bytes = generate_quittance_pdf(html_content)
                    t_ln = p["last_name"]
                    pdf_filename = (
                        f"quittance_{t_ln}_{selected_year}_"
                        f"{selected_month:02d}.pdf"
                    )

                    st.markdown("---")
                    st.markdown(
                        f"##### 🖨️ Quittance de Loyer PDF — "
                        f"{p['first_name']} {p['last_name']}"
                    )

                    # Actions : Téléchargement PDF, Archivage GED, Envoi email
                    q_col1, q_col2, q_col3 = st.columns(3)
                    with q_col1:
                        # Téléchargement direct depuis GED Cloudinary si archivé
                        ged_quit_bytes = None
                        if p.get("doc_public_id"):
                            ged_quit_bytes = storage.download_file_bytes(
                                p["doc_public_id"]
                            )
                        dl_quit_data = (
                            ged_quit_bytes if ged_quit_bytes else pdf_bytes
                        )
                        st.download_button(
                            label="📥 Télécharger Quittance (GED)"
                            if ged_quit_bytes
                            else "📥 Télécharger la Quittance (PDF)",
                            data=dl_quit_data,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            key=f"dl_pdf_{p['id']}",
                            use_container_width=True,
                        )
                    with q_col2:
                        ged_label = (
                            "✅ Quittance à jour dans la GED"
                            if p.get("doc_file_path")
                            else "📎 Archiver dans la GED"
                        )
                        if st.button(
                            ged_label,
                            key=f"btn_save_ged_{p['id']}",
                            use_container_width=True,
                        ):
                            ok_ged, msg_ged, doc_id = save_quittance_to_ged(
                                p["id"], sci_info, tenant_info, prop_info, p
                            )
                            if ok_ged:
                                st.success(msg_ged)
                                st.rerun()
                            else:
                                st.error(msg_ged)
                    with q_col3:
                        if p.get("email"):
                            if st.button(
                                "📧 Envoyer par email (PDF)",
                                key=f"mail_quit_{p['id']}",
                                use_container_width=True,
                            ):
                                sci_nom = sci_info.get("name", "SCI")
                                subj = (
                                    f"Quittance de loyer - {m_nm} "
                                    f"{selected_year} - {sci_nom}"
                                )
                                ok, msg = send_email(
                                    p["email"],
                                    subj,
                                    html_content,
                                    pdf_filename,
                                    pdf_bytes,
                                )
                                if ok:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        else:
                            st.caption(
                                "⚠️ Locataire sans adresse email renseignée."
                            )

                    # Affichage interactif avec iframe
                    components.html(html_content, height=600, scrolling=True)

                st.divider()

        # Outils d'administration / Suppression de loyers
        st.markdown("")
        with st.expander("🗑️ Supprimer des loyers / échéances en masse"):
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                st.markdown(
                    f"##### Supprimer toutes les échéances de "
                    f"{m_nm} {selected_year}"
                )
                nb_p = len(payments)
                st.caption(
                    f"Supprime l'ensemble des {nb_p} échéances "
                    "générées pour ce mois."
                )
                if st.button(
                    f"🚨 Supprimer les {nb_p} échéances du mois",
                    type="secondary",
                    key="del_all_month_rents_btn",
                ):
                    execute_write(
                        """
                        DELETE FROM rent_payments
                        WHERE period_month = ? AND period_year = ?;
                        """,
                        [selected_month, selected_year],
                    )
                    st.success(
                        f"Échéances de {m_nm} {selected_year} supprimées."
                    )
                    st.rerun()

            with col_d2:
                st.markdown(
                    "##### Supprimer l'historique des loyers d'un locataire"
                )
                tenants_with_rents = query_rows("""
                    SELECT t.id, t.first_name, t.last_name,
                           COUNT(rp.id) as count_r,
                           SUM(rp.amount_paid) as sum_paid
                    FROM tenants t
                    JOIN rent_payments rp ON t.id = rp.tenant_id
                    GROUP BY t.id
                    ORDER BY t.last_name ASC;
                """)
                if not tenants_with_rents:
                    st.info("Aucun locataire avec historique de loyer.")
                else:
                    t_rent_dict = {}
                    for t in tenants_with_rents:
                        s_paid = format_currency(t["sum_paid"])
                        lbl = (
                            f"👤 {t['first_name']} {t['last_name']} "
                            f"({t['count_r']} échéance(s) — {s_paid} encaissés)"
                        )
                        t_rent_dict[t["id"]] = lbl
                    sel_t_del = st.selectbox(
                        "Sélectionnez le locataire concerné :",
                        options=list(t_rent_dict.keys()),
                        format_func=lambda x: t_rent_dict[x],
                        key="sb_del_t_rents",
                    )
                    t_to_del_obj = next(
                        (t for t in tenants_with_rents if t["id"] == sel_t_del),
                        None,
                    )
                    if t_to_del_obj:
                        t_nom_del = (
                            f"{t_to_del_obj['first_name']} "
                            f"{t_to_del_obj['last_name']}"
                        )
                        if st.button(
                            f"🚨 Supprimer TOUS les loyers de {t_nom_del}",
                            type="secondary",
                            key=f"btn_del_rents_for_t_{sel_t_del}",
                        ):
                            execute_write(
                                """
                                DELETE FROM rent_payments
                                WHERE tenant_id = ?;
                                """,
                                [sel_t_del],
                            )
                            st.success(
                                f"L'historique de loyers de {t_nom_del} "
                                "a été supprimé."
                            )
                            st.rerun()
