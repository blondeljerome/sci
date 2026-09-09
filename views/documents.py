"""
Vue Coffre-fort Numérique & Gestion Électronique des Documents (GED).
Stockage, classement et consultation des pièces justificatives de la SCI :
- Baux & états des lieux
- Diagnostics techniques (DPE, amiante...)
- Attestations d'assurance
- Factures de travaux & devis
- Statuts & Kbis de la SCI

Les fichiers sont stockés sur Cloudinary (stockage cloud persistant).
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
    "Statuts, Kbis & Documents SCI",
    "Offre de prêt & Contrat de crédit",
    "Appel de fonds de copropriété",
    "Autre pièce justificative"
]

def render_documents():
    st.markdown("## 📎 Coffre-fort Numérique (GED)")
    st.caption("Conservez, classez et téléchargez tous les documents administratifs, baux signés, diagnostics et factures de votre SCI.")

    tab_vault, tab_upload = st.tabs(["📂 Documents Enregistrés", "📤 Téléverser un Document"])

    # 1. LISTE DES DOCUMENTS
    with tab_vault:
        col_c, col_s = st.columns([1, 2])
        with col_c:
            filter_cat = st.selectbox("Filtrer par catégorie :", ["Toutes"] + CATEGORIES_GED, key="ged_f_cat")
        with col_s:
            search_doc = st.text_input("Rechercher un document par nom...", "", key="ged_f_search").lower()

        q = "SELECT * FROM documents"
        params = []
        if filter_cat != "Toutes":
            q += " WHERE category = ?"
            params.append(filter_cat)
        q += " ORDER BY uploaded_at DESC;"

        docs = query_rows(q, params)

        if not docs:
            st.info("Aucun document trouvé. Utilisez l'onglet **'📤 Téléverser un Document'** pour ajouter votre premier fichier.")
        else:
            filtered = []
            for d in docs:
                if search_doc and search_doc not in d["filename"].lower() and search_doc not in (d.get("notes") or "").lower():
                    continue
                filtered.append(d)

            st.write(f"**{len(filtered)}** document(s) trouvé(s) :")

            for doc in filtered:
                size_kb = doc.get("file_size", 0) / 1024.0
                size_str = f"{size_kb:.1f} Ko" if size_kb < 1024 else f"{size_kb/1024.0:.2f} Mo"
                file_url = doc.get("file_path", "")          # URL Cloudinary (ou chemin legacy)
                public_id = doc.get("cloudinary_public_id", "")

                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"📄 **{doc['filename']}**")
                        st.caption(f"📁 Catégorie : **{doc['category']}** • Entité : {doc['entity_type']} #{doc.get('entity_id') or '-'} • Ajouté le : {str(doc['uploaded_at'])[:10]}")
                        if doc.get("notes"):
                            st.caption(f"📝 Notes : {doc['notes']}")
                    with c2:
                        st.caption(f"Taille : {size_str}")
                        if file_url and file_url.startswith("http"):
                            # Fichier Cloudinary : lien de téléchargement direct
                            st.link_button("⬇️ Télécharger", url=file_url)
                        elif file_url:
                            # Legacy : fichier local (ancien enregistrement)
                            import os
                            if os.path.exists(file_url):
                                with open(file_url, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Télécharger",
                                        data=f.read(),
                                        file_name=doc["filename"],
                                        key=f"dl_doc_{doc['id']}"
                                    )
                            else:
                                st.warning("Fichier introuvable")
                        else:
                            st.warning("Fichier introuvable")
                    with c3:
                        st.write("")
                        if st.button("🗑️ Supprimer", key=f"del_doc_{doc['id']}", type="secondary"):
                            # Supprimer depuis Cloudinary si on a le public_id
                            if public_id:
                                storage.delete_file(public_id)
                            execute_write("DELETE FROM documents WHERE id = ?;", [doc["id"]])
                            st.warning("Document supprimé.")
                            st.rerun()

                    st.divider()

    # 2. TELEVERSER UN DOCUMENT
    with tab_upload:
        st.markdown("#### Téléversement de Pièce Justificative")

        # Vérification que Cloudinary est configuré
        from config import get_cloudinary_credentials
        cloud_name, _, _ = get_cloudinary_credentials()
        if not cloud_name:
            st.error(
                "⚠️ **Cloudinary n'est pas configuré.**\n\n"
                "Ajoutez `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY` et `CLOUDINARY_API_SECRET` "
                "dans vos secrets Streamlit ou vos variables d'environnement."
            )
            return

        # Entités pour liaison
        all_props = query_rows("SELECT id, name FROM properties ORDER BY name ASC;")
        all_tenants = query_rows("SELECT id, first_name, last_name FROM tenants WHERE is_active = 1;")
        all_loans = query_rows("SELECT id, bank_name, loan_reference FROM loans;")

        with st.form("form_upload_doc", clear_on_submit=True):
            uploaded_file = st.file_uploader(
                "Sélectionnez le fichier à téléverser (PDF, image, document)",
                type=["pdf", "png", "jpg", "jpeg", "docx", "xlsx", "txt"],
                key="doc_uploader"
            )

            col1, col2 = st.columns(2)
            with col1:
                category = st.selectbox("Catégorie du document *", CATEGORIES_GED)
                entity_choice = st.selectbox(
                    "Lier ce document à :",
                    ["SCI générale", "Un Bien immobilier", "Un Locataire", "Un Emprunt bancaire"]
                )

            with col2:
                entity_id = None
                if entity_choice == "Un Bien immobilier" and all_props:
                    p_opts = {p["id"]: p["name"] for p in all_props}
                    entity_id = st.selectbox("Sélectionnez le bien", options=list(p_opts.keys()), format_func=lambda x: p_opts[x])
                elif entity_choice == "Un Locataire" and all_tenants:
                    t_opts = {t["id"]: f"{t['first_name']} {t['last_name']}" for t in all_tenants}
                    entity_id = st.selectbox("Sélectionnez le locataire", options=list(t_opts.keys()), format_func=lambda x: t_opts[x])
                elif entity_choice == "Un Emprunt bancaire" and all_loans:
                    l_opts = {l["id"]: f"{l['bank_name']} ({l.get('loan_reference') or ''})" for l in all_loans}
                    entity_id = st.selectbox("Sélectionnez l'emprunt", options=list(l_opts.keys()), format_func=lambda x: l_opts[x])

                custom_name = st.text_input("Nom personnalisé (optionnel)", placeholder="Laissez vide pour conserver le nom original")

            notes = st.text_area("Remarques / Références", placeholder="ex: Attestation reçue le 15/01/2026, valable jusqu'au 31/12/2026...")

            submitted = st.form_submit_button("📤 Enregistrer dans le coffre-fort", type="primary")
            if submitted:
                if not uploaded_file:
                    st.error("Veuillez sélectionner un fichier à téléverser.")
                else:
                    try:
                        filename = custom_name.strip() if custom_name.strip() else uploaded_file.name

                        # Upload vers Cloudinary
                        with st.spinner("Téléversement vers Cloudinary en cours…"):
                            file_bytes = uploaded_file.getbuffer()
                            public_id, secure_url, file_size = storage.upload_file(
                                bytes(file_bytes),
                                uploaded_file.name,
                            )

                        ent_type_map = {
                            "SCI générale": "sci",
                            "Un Bien immobilier": "property",
                            "Un Locataire": "tenant",
                            "Un Emprunt bancaire": "loan"
                        }

                        execute_write("""
                            INSERT INTO documents (category, entity_type, entity_id, filename, file_path, cloudinary_public_id, file_size, notes)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """, [category, ent_type_map[entity_choice], entity_id, filename, secure_url, public_id, file_size, notes.strip()])

                        st.success(f"Document **'{filename}'** téléversé avec succès dans le coffre-fort !")
                        st.rerun()
                    except RuntimeError as e:
                        st.error(str(e))
                    except Exception as e:
                        st.error(f"Erreur lors du téléversement : {e}")

