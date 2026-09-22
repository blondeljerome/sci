"""
Vue Coffre-fort Numérique & Gestion Électronique des Documents (GED).
Stockage, classement et consultation des pièces justificatives de la SCI :
- Baux & états des lieux
- Diagnostics techniques (DPE, plomb, élec...)
- Attestations d'assurance habitation & PNO
- Factures de travaux, devis & taxes foncières
- Statuts & Kbis de la SCI
- Contrats de prêt bancaire

Les fichiers sont stockés sur Cloudinary (stockage cloud sécurisé et persistant).
Liaison intelligente aux Biens Immobiliers et aux Locataires de la SCI.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from database import query_rows, query_one, execute_write
from utils import storage

CATEGORIES_GED = [
    "Bail & État des lieux",
    "Attestation d'assurance habitation",
    "Diagnostic technique (DPE, plomb, élec...)",
    "Facture / Devis de travaux",
    "Taxe foncière / Avis d'imposition",
    "Appel de fonds de copropriété",
    "Statuts, Kbis & Documents SCI",
    "Offre de prêt & Contrat de crédit",
    "Quittance & Reçu de paiement",
    "Autre pièce justificative"
]

def format_file_size(size_bytes: int) -> str:
    size_kb = (size_bytes or 0) / 1024.0
    if size_kb < 1024:
        return f"{size_kb:.1f} Ko"
    return f"{size_kb / 1024.0:.2f} Mo"

def render_doc_button(file_url: str, filename: str, key: str, label: str = "⬇️ Ouvrir / Télécharger"):
    import os
    if file_url and file_url.startswith("http"):
        st.link_button(label, url=file_url, use_container_width=True)
    elif file_url:
        if os.path.exists(file_url):
            with open(file_url, "rb") as f:
                st.download_button(
                    label=label,
                    data=f.read(),
                    file_name=filename,
                    key=key,
                    use_container_width=True
                )
        else:
            st.caption("Fichier introuvable")
    else:
        st.caption("Fichier introuvable")

def render_documents():
    st.markdown("## 📎 Coffre-fort Numérique (GED)")
    st.caption("Conservez, classez et téléchargez tous les documents administratifs, baux signés, diagnostics et factures de votre SCI.")

    tab_vault, tab_by_entity, tab_upload = st.tabs([
        "📂 Tous les Documents",
        "🏢 Dossiers par Bien & Locataire",
        "📤 Téléverser un Document"
    ])

    # Chargement des référentiels
    all_props = query_rows("SELECT id, name, address, postal_code, city, status FROM properties ORDER BY name ASC;")
    all_tenants = query_rows("""
        SELECT t.id, t.first_name, t.last_name, t.property_id, t.is_active, p.name as prop_name, p.city as prop_city
        FROM tenants t
        LEFT JOIN properties p ON t.property_id = p.id
        ORDER BY t.is_active DESC, t.last_name ASC;
    """)
    all_loans = query_rows("""
        SELECT l.id, l.bank_name, l.loan_reference, l.property_id, p.name as prop_name
        FROM loans l
        LEFT JOIN properties p ON l.property_id = p.id
        ORDER BY l.id ASC;
    """)

    # 1. LISTE DE TOUS LES DOCUMENTS
    with tab_vault:
        # Requête complète avec jointures properties, tenants et loans
        docs = query_rows("""
            SELECT 
                d.*,
                p.id AS prop_id,
                p.name AS prop_name,
                p.city AS prop_city,
                t.id AS ten_id,
                t.first_name AS ten_first_name,
                t.last_name AS ten_last_name,
                l.bank_name AS loan_bank,
                l.loan_reference AS loan_ref
            FROM documents d
            LEFT JOIN properties p ON (d.property_id = p.id OR (d.entity_type = 'property' AND d.entity_id = p.id))
            LEFT JOIN tenants t ON (d.tenant_id = t.id OR (d.entity_type = 'tenant' AND d.entity_id = t.id))
            LEFT JOIN loans l ON (d.entity_type = 'loan' AND d.entity_id = l.id)
            ORDER BY d.uploaded_at DESC, d.id DESC;
        """)

        # Métriques du coffre-fort
        total_docs = len(docs)
        docs_with_prop = sum(1 for d in docs if d.get("prop_name"))
        docs_with_tenant = sum(1 for d in docs if d.get("ten_last_name"))
        total_size_bytes = sum(d.get("file_size", 0) for d in docs)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Documents", total_docs)
        m2.metric("Liés à un Bien", docs_with_prop)
        m3.metric("Liés à un Locataire", docs_with_tenant)
        m4.metric("Espace Utilisé", format_file_size(total_size_bytes))

        st.markdown("---")

        # Filtres
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            filter_cat = st.selectbox("Catégorie :", ["Toutes"] + CATEGORIES_GED, key="ged_f_cat")
        with f_col2:
            prop_filter_options = ["Tous les biens", "🏢 Documents liés à un bien (Tous)"] + [f"🏢 {p['name']}" for p in all_props] + ["— Documents sans bien —"]
            filter_prop = st.selectbox("Bien immobilier :", prop_filter_options, key="ged_f_prop")
        with f_col3:
            tenant_filter_options = ["Tous les locataires", "👤 Documents liés à un locataire (Tous)"] + [f"👤 {t['first_name']} {t['last_name']}" for t in all_tenants] + ["— Documents sans locataire —"]
            filter_tenant = st.selectbox("Locataire :", tenant_filter_options, key="ged_f_tenant")

        search_doc = st.text_input("🔍 Recherche rapide (nom, bien, locataire, notes)...", "", key="ged_f_search").strip().lower()

        # Filtrage en mémoire
        filtered = []
        for d in docs:
            # Filtre catégorie
            if filter_cat != "Toutes" and d.get("category") != filter_cat:
                continue

            # Filtre bien
            if filter_prop == "🏢 Documents liés à un bien (Tous)" and not d.get("prop_name"):
                continue
            elif filter_prop == "— Documents sans bien —" and d.get("prop_name"):
                continue
            elif filter_prop.startswith("🏢 "):
                selected_p_name = filter_prop.replace("🏢 ", "")
                if d.get("prop_name") != selected_p_name:
                    continue

            # Filtre locataire
            if filter_tenant == "👤 Documents liés à un locataire (Tous)" and not d.get("ten_last_name"):
                continue
            elif filter_tenant == "— Documents sans locataire —" and d.get("ten_last_name"):
                continue
            elif filter_tenant.startswith("👤 "):
                selected_t_name = filter_tenant.replace("👤 ", "").strip().lower()
                doc_t_name = f"{d.get('ten_first_name', '')} {d.get('ten_last_name', '')}".strip().lower()
                if doc_t_name != selected_t_name:
                    continue

            # Recherche textuelle
            if search_doc:
                haystack = f"{d.get('filename', '')} {d.get('notes', '')} {d.get('category', '')} {d.get('prop_name', '')} {d.get('ten_first_name', '')} {d.get('ten_last_name', '')}".lower()
                if search_doc not in haystack:
                    continue

            filtered.append(d)

        st.caption(f"**{len(filtered)}** document(s) affiché(s)")

        if not filtered:
            st.info("Aucun document ne correspond à vos critères de recherche.")
        else:
            for doc in filtered:
                size_str = format_file_size(doc.get("file_size", 0))
                file_url = doc.get("file_path", "")
                public_id = doc.get("cloudinary_public_id", "")

                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"📄 **{doc['filename']}**")
                        
                        # Badges d'association
                        badges = [f"📁 `{doc['category']}`"]
                        if doc.get("prop_name"):
                            badges.append(f"🏢 Bien : **{doc['prop_name']}**")
                        if doc.get("ten_last_name"):
                            badges.append(f"👤 Locataire : **{doc['ten_first_name']} {doc['ten_last_name']}**")
                        if doc.get("loan_bank"):
                            badges.append(f"🏦 Prêt : **{doc['loan_bank']}**")
                        if doc.get("entity_type") == "sci" and not doc.get("prop_name") and not doc.get("ten_last_name"):
                            badges.append("🏛️ **SCI générale**")

                        st.markdown(" • ".join(badges))
                        st.caption(f"Ajouté le : {str(doc.get('uploaded_at', ''))[:10]} • Taille : {size_str}")
                        if doc.get("notes"):
                            st.caption(f"📝 Notes : {doc['notes']}")

                    with c2:
                        st.write("")
                        render_doc_button(file_url, doc["filename"], key=f"dl_doc_{doc['id']}")

                    with c3:
                        st.write("")
                        if st.button("🗑️ Supprimer", key=f"del_doc_{doc['id']}", type="secondary", use_container_width=True):
                            if public_id:
                                storage.delete_file(public_id)
                            execute_write("DELETE FROM documents WHERE id = ?;", [doc["id"]])
                            st.success("Document supprimé.")
                            st.rerun()

                    st.divider()

    # 2. VUE DOSSIERS PAR BIEN & LOCATAIRE
    with tab_by_entity:
        st.markdown("#### 🗂️ Dossiers Numériques Classés")
        st.caption("Consultez l'ensemble des pièces rattachées à un bien immobilier précis ou à un dossier locataire.")

        view_type = st.radio("Classer par :", ["🏢 Par Bien Immobilier", "👤 Par Locataire"], horizontal=True, key="ged_view_type")

        if view_type == "🏢 Par Bien Immobilier":
            if not all_props:
                st.info("Aucun bien immobilier enregistré.")
            else:
                p_options = {p["id"]: f"{p['name']} ({p.get('city') or ''})" for p in all_props}
                selected_pid = st.selectbox("Sélectionnez le bien immobilier à inspecter :", options=list(p_options.keys()), format_func=lambda x: p_options[x], key="ged_inspect_p")
                p_obj = next((p for p in all_props if p["id"] == selected_pid), None)

                if p_obj:
                    # Documents rattachés directement au bien
                    prop_docs = [d for d in docs if (d.get("property_id") == selected_pid or (d.get("entity_type") == "property" and d.get("entity_id") == selected_pid))]

                    # Répartition : documents généraux du lot vs documents locataires
                    lot_docs = [d for d in prop_docs if not d.get("tenant_id") and d.get("entity_type") != "tenant"]
                    tenant_docs = [d for d in prop_docs if d.get("tenant_id") or d.get("entity_type") == "tenant"]

                    c_info1, c_info2 = st.columns(2)
                    c_info1.metric("Documents propres au bien", len(lot_docs), help="DPE, factures de travaux, PV de copropriété, taxe foncière...")
                    c_info2.metric("Documents des locataires du bien", len(tenant_docs), help="Baux, états des lieux, quittances, assurances habitation...")

                    st.markdown("##### 📁 Documents Techniques & Administratifs du Bien")
                    if not lot_docs:
                        st.info("Aucun document propre au bien téléversé (DPE, facture de travaux, taxe foncière...).")
                    else:
                        for d in lot_docs:
                            with st.container():
                                cd1, cd2 = st.columns([4, 1])
                                cd1.markdown(f"📄 **{d['filename']}** • `{d['category']}` • {format_file_size(d.get('file_size', 0))}")
                                if d.get("notes"):
                                    cd1.caption(f"📝 {d['notes']}")
                                with cd2:
                                    render_doc_button(d.get("file_path", ""), d["filename"], key=f"dl_lot_{d['id']}", label="⬇️ Voir")
                                st.divider()

                    st.markdown("##### 👥 Documents des Baux & Locataires de ce Bien")
                    if not tenant_docs:
                        st.info("Aucun document locatif enregistré pour ce bien (bail signé, état des lieux...).")
                    else:
                        for d in tenant_docs:
                            t_name = f"{d.get('ten_first_name', '')} {d.get('ten_last_name', '')}".strip() or "Locataire"
                            with st.container():
                                cd1, cd2 = st.columns([4, 1])
                                cd1.markdown(f"📄 **{d['filename']}** • 👤 **{t_name}** • `{d['category']}`")
                                if d.get("notes"):
                                    cd1.caption(f"📝 {d['notes']}")
                                with cd2:
                                    render_doc_button(d.get("file_path", ""), d["filename"], key=f"dl_tenprop_{d['id']}", label="⬇️ Voir")
                                st.divider()

        else: # Par Locataire
            if not all_tenants:
                st.info("Aucun locataire enregistré.")
            else:
                t_options = {t["id"]: f"👤 {t['first_name']} {t['last_name']} ({'Actuel' if t['is_active'] else 'Ancien'}) — {t['prop_name'] or 'Sans bien'}" for t in all_tenants}
                selected_tid = st.selectbox("Sélectionnez le dossier locataire à inspecter :", options=list(t_options.keys()), format_func=lambda x: t_options[x], key="ged_inspect_t")
                t_obj = next((t for t in all_tenants if t["id"] == selected_tid), None)

                if t_obj:
                    ten_docs = [d for d in docs if (d.get("tenant_id") == selected_tid or (d.get("entity_type") == "tenant" and d.get("entity_id") == selected_tid))]
                    st.write(f"Dossier de **{t_obj['first_name']} {t_obj['last_name']}** — Logement loué : **{t_obj.get('prop_name') or 'Non affecté'}**")
                    st.metric("Documents au dossier", len(ten_docs))

                    if not ten_docs:
                        st.info("Aucun document téléversé pour ce locataire. Utilisez l'onglet **'📤 Téléverser un Document'** pour joindre le bail, l'état des lieux ou l'attestation d'assurance.")
                    else:
                        for d in ten_docs:
                            with st.container():
                                cd1, cd2 = st.columns([4, 1])
                                cd1.markdown(f"📄 **{d['filename']}** • `{d['category']}` • {format_file_size(d.get('file_size', 0))}")
                                if d.get("notes"):
                                    cd1.caption(f"📝 {d['notes']}")
                                with cd2:
                                    render_doc_button(d.get("file_path", ""), d["filename"], key=f"dl_tendoc_{d['id']}", label="⬇️ Voir")
                                st.divider()

    # 3. TELEVERSER UN DOCUMENT
    with tab_upload:
        st.markdown("#### 📤 Téléversement & Classement d'un Nouveau Document")
        st.caption("Sélectionnez votre fichier et choisissez précisément le bien immobilier et/ou le locataire associé.")

        # Vérification Cloudinary
        from config import get_cloudinary_credentials
        cloud_name, _, _ = get_cloudinary_credentials()
        if not cloud_name:
            st.error(
                "⚠️ **Cloudinary n'est pas configuré.**\n\n"
                "Ajoutez `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` et `CLOUDINARY_API_SECRET` "
                "dans vos secrets Streamlit ou vos variables d'environnement."
            )
            return

        # Fichier
        uploaded_file = st.file_uploader(
            "Fichier à téléverser (PDF, image, document bureautique) *",
            type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "txt"],
            key="ged_upload_file"
        )

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            category = st.selectbox("Catégorie du document *", CATEGORIES_GED, key="ged_cat_select")
        with col_meta2:
            custom_name = st.text_input(
                "Nom personnalisé du document (optionnel)",
                placeholder="Laissez vide pour conserver le nom d'origine du fichier",
                key="ged_custom_name_input"
            )

        st.markdown("##### 🔗 Rattachement du Document")
        attach_mode = st.radio(
            "Lier ce document à :",
            ["🏢 Un Bien immobilier", "👤 Un Locataire", "🏛️ SCI générale", "🏦 Un Emprunt bancaire"],
            horizontal=True,
            key="ged_attach_mode"
        )

        target_property_id = None
        target_tenant_id = None
        target_entity_type = "sci"
        target_entity_id = None

        if attach_mode == "🏢 Un Bien immobilier":
            if not all_props:
                st.warning("⚠️ Aucun bien immobilier n'est encore enregistré dans la SCI.")
            else:
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    prop_map = {p["id"]: f"{p['name']} ({p.get('city') or ''})" for p in all_props}
                    selected_prop_id = st.selectbox(
                        "Sélectionnez le bien immobilier concerné * :",
                        options=list(prop_map.keys()),
                        format_func=lambda x: prop_map[x],
                        key="ged_upload_sel_prop"
                    )
                    target_property_id = selected_prop_id
                    target_entity_type = "property"
                    target_entity_id = selected_prop_id

                with col_p2:
                    # Recherche des locataires attachés à ce bien
                    prop_tenants = query_rows("""
                        SELECT id, first_name, last_name, is_active
                        FROM tenants
                        WHERE property_id = ?
                        ORDER BY is_active DESC, last_name ASC;
                    """, [selected_prop_id])

                    tenant_options_for_prop = {None: "— Aucun (document propre au bien : DPE, travaux, taxe...) —"}
                    for t in prop_tenants:
                        status_label = "Actuel" if t["is_active"] else "Ancien"
                        tenant_options_for_prop[t["id"]] = f"👤 {t['first_name']} {t['last_name']} ({status_label})"

                    selected_tenant_for_prop = st.selectbox(
                        "Préciser le locataire concerné (optionnel) :",
                        options=list(tenant_options_for_prop.keys()),
                        format_func=lambda x: tenant_options_for_prop[x],
                        key="ged_upload_sel_tenant_prop"
                    )
                    target_tenant_id = selected_tenant_for_prop
                    if target_tenant_id:
                        target_entity_type = "tenant"
                        target_entity_id = target_tenant_id

        elif attach_mode == "👤 Un Locataire":
            if not all_tenants:
                st.warning("⚠️ Aucun locataire n'est actuellement enregistré.")
            else:
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    tenant_map = {
                        t["id"]: f"👤 {t['first_name']} {t['last_name']} ({'Actif' if t['is_active'] else 'Sorti'})"
                        for t in all_tenants
                    }
                    selected_tenant_id = st.selectbox(
                        "Sélectionnez le locataire * :",
                        options=list(tenant_map.keys()),
                        format_func=lambda x: tenant_map[x],
                        key="ged_upload_sel_tenant_direct"
                    )
                    target_tenant_id = selected_tenant_id
                    target_entity_type = "tenant"
                    target_entity_id = selected_tenant_id

                with col_t2:
                    t_selected = next((t for t in all_tenants if t["id"] == selected_tenant_id), None)
                    if t_selected and t_selected.get("property_id"):
                        target_property_id = t_selected["property_id"]
                        st.success(f"🏢 **Bien immobilier rattaché automatiquement :** {t_selected['prop_name']} ({t_selected.get('prop_city') or ''})")
                    else:
                        target_property_id = None
                        st.info("ℹ️ Ce locataire n'a pas de logement assigné actuellement.")

        elif attach_mode == "🏦 Un Emprunt bancaire":
            if not all_loans:
                st.warning("⚠️ Aucun emprunt bancaire enregistré.")
            else:
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    loan_map = {l["id"]: f"🏦 {l['bank_name']} ({l.get('loan_reference') or 'Sans réf'})" for l in all_loans}
                    selected_loan_id = st.selectbox(
                        "Sélectionnez le prêt bancaire * :",
                        options=list(loan_map.keys()),
                        format_func=lambda x: loan_map[x],
                        key="ged_upload_sel_loan"
                    )
                    target_entity_type = "loan"
                    target_entity_id = selected_loan_id

                with col_l2:
                    l_selected = next((l for l in all_loans if l["id"] == selected_loan_id), None)
                    if l_selected and l_selected.get("property_id"):
                        target_property_id = l_selected["property_id"]
                        st.success(f"🏢 **Bien associé au prêt :** {l_selected['prop_name']}")
                    else:
                        target_property_id = None
                        st.info("ℹ️ Prêt global ou sans bien spécifique rattaché.")

        else: # SCI générale
            target_entity_type = "sci"
            target_entity_id = None
            target_property_id = None
            target_tenant_id = None
            st.info("🏛️ Le document sera classé dans les documents généraux de la SCI (Statuts, Kbis, AG, RIB de la SCI...).")

        notes = st.text_area(
            "Remarques / Références / Dates de validité (optionnel)",
            placeholder="ex: Diagnostic de performance énergétique (DPE) valable 10 ans jusqu'au 15/06/2034...",
            key="ged_upload_notes_input"
        )

        st.markdown("")
        if st.button("📤 Enregistrer et classer dans le coffre-fort", type="primary", use_container_width=True, key="ged_submit_button"):
            if not uploaded_file:
                st.error("Veuillez sélectionner un fichier à téléverser.")
            elif attach_mode == "🏢 Un Bien immobilier" and not target_property_id:
                st.error("Veuillez sélectionner un bien immobilier.")
            elif attach_mode == "👤 Un Locataire" and not target_tenant_id:
                st.error("Veuillez sélectionner un locataire.")
            elif attach_mode == "🏦 Un Emprunt bancaire" and not target_entity_id:
                st.error("Veuillez sélectionner un emprunt bancaire.")
            else:
                try:
                    final_filename = custom_name.strip() if custom_name.strip() else uploaded_file.name

                    with st.spinner("Téléversement sécurisé vers Cloudinary en cours…"):
                        file_bytes = uploaded_file.getvalue()
                        public_id, secure_url, file_size = storage.upload_file(
                            file_bytes,
                            uploaded_file.name
                        )

                    execute_write("""
                        INSERT INTO documents (
                            category, entity_type, entity_id, property_id, tenant_id,
                            filename, file_path, cloudinary_public_id, file_size, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """, [
                        category,
                        target_entity_type,
                        target_entity_id,
                        target_property_id,
                        target_tenant_id,
                        final_filename,
                        secure_url,
                        public_id,
                        file_size,
                        notes.strip()
                    ])

                    st.success(f"Document **'{final_filename}'** enregistré et classé avec succès dans le coffre-fort !")
                    for k in ["ged_upload_file", "ged_custom_name_input", "ged_upload_notes_input"]:
                        st.session_state.pop(k, None)
                    st.rerun()
                except RuntimeError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Erreur lors de l'enregistrement : {e}")
