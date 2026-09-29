"""Générateur de quittance de loyer aux formats HTML et PDF (ReportLab).

Conforme aux dispositions de la loi n° 89-462 du 6 juillet 1989.
Permet la génération et l'archivage automatique dans la GED.
"""

import io
from datetime import date
from typing import Any, Dict, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from database import execute_write, query_one
from utils import storage
from utils.formatters import MONTH_NAMES_FR

MONTH_NAMES = [""] + MONTH_NAMES_FR


def generate_quittance_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment: Dict[str, Any],
) -> str:
    """Génère un document HTML élégant pour la prévisualisation dans Streamlit.

    Args:
        sci_info: Métadonnées de la société bailleresse.
        tenant: Informations du locataire.
        property_info: Détails du logement loué.
        payment: Données de paiement de l'échéance.

    Returns:
        Document HTML complet prêt pour affichage web ou impression.
    """
    p_month = int(payment.get("period_month", 1))
    p_year = int(payment.get("period_year", 2026))
    month_str = MONTH_NAMES[p_month] if 1 <= p_month <= 12 else str(p_month)
    period_str = f"{month_str} {p_year}"

    rent = float(payment.get("rent_amount", 0.0) or 0.0)
    charges = float(payment.get("charges_amount", 0.0) or 0.0)
    total = rent + charges
    paid = float(payment.get("amount_paid", total) or total)
    pay_date = str(
        payment.get("payment_date") or payment.get("due_date") or date.today()
    )[:10]
    pay_method = payment.get("payment_method", "Virement bancaire")

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Quittance de loyer - {period_str}</title>
<style>
    @media print {{
        body {{
            margin: 0; padding: 20px; font-size: 13pt;
            background: #fff !important; color: #000 !important;
        }}
        .no-print {{ display: none !important; }}
        .quittance-card {{
            box-shadow: none !important; border: 1px solid #ccc !important;
        }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                     Roboto, Helvetica, Arial, sans-serif;
        background-color: #f1f5f9;
        margin: 0;
        padding: 30px;
        color: #1e293b;
    }}
    .quittance-card {{
        max-width: 720px;
        margin: 0 auto;
        background: #ffffff;
        padding: 40px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        border-bottom: 2px solid #2563eb;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }}
    .header h1 {{
        margin: 0;
        color: #1e3a8a;
        font-size: 22px;
        letter-spacing: -0.5px;
    }}
    .header .subtitle {{
        color: #64748b;
        font-size: 14px;
        margin-top: 4px;
    }}
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 30px;
        margin-bottom: 30px;
    }}
    .box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 16px 20px;
        border-radius: 8px;
        font-size: 14px;
        line-height: 1.5;
    }}
    .box h3 {{
        margin-top: 0;
        margin-bottom: 8px;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #2563eb;
    }}
    .table-breakdown {{
        width: 100%;
        border-collapse: collapse;
        margin: 25px 0;
        font-size: 15px;
    }}
    .table-breakdown th, .table-breakdown td {{
        padding: 12px 16px;
        border-bottom: 1px solid #e2e8f0;
    }}
    .table-breakdown th {{
        background: #f1f5f9;
        text-align: left;
        color: #475569;
        font-weight: 600;
    }}
    .table-breakdown td.amount {{
        text-align: right;
        font-weight: 500;
    }}
    .table-breakdown tr.total td {{
        border-top: 2px solid #cbd5e1;
        border-bottom: 2px solid #2563eb;
        font-weight: 700;
        font-size: 16px;
        color: #1e3a8a;
    }}
    .declaration {{
        background: #eff6ff;
        border-left: 4px solid #2563eb;
        padding: 14px 18px;
        margin: 25px 0;
        font-size: 14px;
        line-height: 1.6;
        color: #1e40af;
        border-radius: 0 8px 8px 0;
    }}
    .footer-signatures {{
        display: flex;
        justify-content: space-between;
        margin-top: 40px;
        padding-top: 20px;
    }}
    .signature-box {{
        width: 250px;
        text-align: center;
        font-size: 13px;
        color: #64748b;
    }}
    .signature-space {{
        height: 70px;
        margin-top: 10px;
        border-bottom: 1px dashed #cbd5e1;
    }}
</style>
</head>
<body>

<div class="quittance-card">
    <div class="header">
        <div>
            <h1>QUITTANCE DE LOYER</h1>
            <div class="subtitle">
                Période concernée : <strong>{period_str}</strong>
            </div>
        </div>
        <div style="text-align: right; font-size: 13px; color: #64748b;">
            Date d'émission : {pay_date}<br>
            Quittance réf : #{payment.get("id", 0):05d}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h3>Bailleur</h3>
            <strong>{sci_info.get("name", "SCI")}</strong><br>
            {
                f"SIREN : {sci_info.get('siren')}<br>"
                if sci_info.get("siren") else ""
            }
            {sci_info.get("address", "")}<br>
            {sci_info.get("postal_code", "")} {sci_info.get("city", "")}<br>
            {
                f"Gérant : {sci_info.get('manager_name')}<br>"
                if sci_info.get("manager_name") else ""
            }
            {
                f"Contact : {sci_info.get('manager_email')}"
                if sci_info.get("manager_email") else ""
            }
        </div>

        <div class="box">
            <h3>Locataire</h3>
            <strong>
                {tenant.get("first_name", "")} {tenant.get("last_name", "")}
            </strong><br>
            Logement loué :<br>
            {property_info.get("name", "")}<br>
            {property_info.get("address", "")}<br>
            {property_info.get("postal_code", "")}
            {property_info.get("city", "")}
        </div>
    </div>

    <table class="table-breakdown">
        <thead>
            <tr>
                <th>Désignation</th>
                <th style="text-align: right;">Montant</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Loyer principal net (hors charges)</td>
                <td class="amount">{rent:.2f} €</td>
            </tr>
            <tr>
                <td>Provision mensuelle sur charges locatives</td>
                <td class="amount">{charges:.2f} €</td>
            </tr>
            <tr class="total">
                <td>Total quittancé pour la période</td>
                <td class="amount">{total:.2f} €</td>
            </tr>
        </tbody>
    </table>

    <div class="declaration">
        Je soussigné, représentant de la société
        <strong>{sci_info.get("name", "SCI")}</strong>,
        propriétaire et bailleur du logement désigné ci-dessus, atteste avoir
        reçu de Monsieur/Madame
        <strong>
            {tenant.get("first_name", "")} {tenant.get("last_name", "")}
        </strong>
        la somme de <strong>{paid:.2f} €</strong> (règlement par {pay_method}),
        pour loyer et charges du terme de <strong>{period_str}</strong> et lui
        en donne quittance, sous réserve de tous droits et décomptes ultérieurs.
    </div>

    <div class="footer-signatures">
        <div style="font-size: 12px; color: #94a3b8; max-width: 380px;">
            <em>Cette quittance annule tout reçu pour acompte versé au titre
            de la même période. À conserver sans limitation de durée.</em>
        </div>
        <div class="signature-box">
            Fait à {sci_info.get("city", "Paris")}, le {pay_date}<br>
            <strong>Le Bailleur / Le Gérant</strong>
            <div class="signature-space"></div>
        </div>
    </div>
</div>

</body>
</html>
"""
    return html


def generate_quittance_pdf(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment: Dict[str, Any],
) -> bytes:
    """Génère un document PDF binaire pour la quittance de loyer.

    Utilise ReportLab pour une mise en page vectorielle professionnelle.

    Args:
        sci_info: Dictionnaire avec les informations de la SCI.
        tenant: Dictionnaire avec les informations du locataire.
        property_info: Dictionnaire avec les informations du bien.
        payment: Dictionnaire avec les informations du paiement.

    Returns:
        bytes: Données binaires du fichier PDF généré.
    """
    p_month = int(payment.get("period_month", 1))
    p_year = int(payment.get("period_year", 2026))
    month_str = MONTH_NAMES[p_month] if 1 <= p_month <= 12 else str(p_month)
    period_str = f"{month_str} {p_year}"

    rent = float(payment.get("rent_amount", 0.0) or 0.0)
    charges = float(payment.get("charges_amount", 0.0) or 0.0)
    total = rent + charges
    paid = float(payment.get("amount_paid", total) or total)
    pay_date = str(
        payment.get("payment_date") or payment.get("due_date") or date.today()
    )[:10]
    pay_method = payment.get("payment_method", "Virement bancaire")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    primary_color = colors.HexColor("#1e3a8a")
    secondary_color = colors.HexColor("#2563eb")
    text_dark = colors.HexColor("#1e293b")
    text_muted = colors.HexColor("#64748b")
    bg_light = colors.HexColor("#f8fafc")
    border_color = colors.HexColor("#cbd5e1")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=primary_color,
        fontName="Helvetica-Bold",
    )
    ref_style = ParagraphStyle(
        "DocRef",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=text_muted,
        alignment=2,
    )
    box_header_style = ParagraphStyle(
        "BoxHeader",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=12,
        textColor=secondary_color,
        fontName="Helvetica-Bold",
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=text_dark,
        fontName="Helvetica",
    )
    body_bold = ParagraphStyle(
        "BodyBold",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark,
        fontName="Helvetica-Bold",
    )
    legal_style = ParagraphStyle(
        "Legal",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12.5,
        textColor=colors.HexColor("#1e40af"),
        fontName="Helvetica",
    )
    footer_style = ParagraphStyle(
        "FooterNote",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica-Oblique",
    )

    story = []

    # 1. En-tête
    title_html = (
        "<b>QUITTANCE DE LOYER</b><br/>"
        f"<font size='9.5' color='#64748b'>"
        f"Période concernée : <b>{period_str}</b></font>"
    )
    ref_id = int(payment.get("id") or 0)
    ref_html = (
        f"<b>Réf :</b> #{ref_id:05d}<br/>"
        f"<b>Date d'émission :</b> {pay_date}"
    )
    header_data = [
        [
            Paragraph(title_html, title_style),
            Paragraph(ref_html, ref_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[320, 203])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(header_table)
    story.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=secondary_color,
            spaceBefore=2,
            spaceAfter=14,
        )
    )

    # 2. Parties (Bailleur & Locataire)
    sci_name = sci_info.get("name", "Ma SCI Immobilière")
    siren = (
        f"SIREN : {sci_info.get('siren')}<br/>"
        if sci_info.get("siren")
        else ""
    )
    manager = (
        f"Gérant : {sci_info.get('manager_name')}<br/>"
        if sci_info.get("manager_name")
        else ""
    )
    contact = (
        f"Email : {sci_info.get('manager_email')}"
        if sci_info.get("manager_email")
        else ""
    )
    sci_addr = (
        f"{sci_info.get('address', '')}<br/>"
        f"{sci_info.get('postal_code', '')} {sci_info.get('city', '')}"
    )

    t_first = tenant.get("first_name", "")
    t_last = tenant.get("last_name", "")
    p_name = property_info.get("name", "")
    p_zip = property_info.get("postal_code", "")
    p_city = property_info.get("city", "")
    p_addr = (
        f"{property_info.get('address', '')}<br/>"
        f"{p_zip} {p_city}"
    )

    bailleur_html = (
        f"<b>{sci_name}</b><br/>{siren}{sci_addr}<br/>{manager}{contact}"
    )
    locataire_html = (
        f"<b>{t_first} {t_last}</b><br/>"
        f"<b>Logement loué :</b> {p_name}<br/>{p_addr}"
    )

    parties_data = [
        [
            Paragraph("BAILLEUR", box_header_style),
            Paragraph("LOCATAIRE", box_header_style),
        ],
        [
            Paragraph(bailleur_html, body_style),
            Paragraph(locataire_html, body_style),
        ],
    ]
    parties_table = Table(parties_data, colWidths=[255, 268])
    parties_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), bg_light),
                ("BOX", (0, 0), (0, 1), 1, border_color),
                ("BOX", (1, 0), (1, 1), 1, border_color),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(parties_table)
    story.append(Spacer(1, 14))

    # 3. Tableau de ventilation
    table_data = [
        [
            Paragraph("<b>Désignation</b>", body_style),
            Paragraph(
                "<b>Montant (€)</b>",
                ParagraphStyle("TR", parent=body_style, alignment=2),
            ),
        ],
        [
            Paragraph("Loyer principal net (hors charges)", body_style),
            Paragraph(
                f"{rent:,.2f} €",
                ParagraphStyle("TR", parent=body_style, alignment=2),
            ),
        ],
        [
            Paragraph("Provision mensuelle sur charges locatives", body_style),
            Paragraph(
                f"{charges:,.2f} €",
                ParagraphStyle("TR", parent=body_style, alignment=2),
            ),
        ],
        [
            Paragraph("<b>Total quittancé pour la période</b>", body_bold),
            Paragraph(
                f"<b>{total:,.2f} €</b>",
                ParagraphStyle("TRB", parent=body_bold, alignment=2),
            ),
        ],
        [
            Paragraph(
                f"<b>Montant acquitté (Règlement par {pay_method})</b>",
                body_bold,
            ),
            Paragraph(
                f"<b>{paid:,.2f} €</b>",
                ParagraphStyle(
                    "TRB2",
                    parent=body_bold,
                    alignment=2,
                    textColor=colors.HexColor("#15803d"),
                ),
            ),
        ],
    ]
    breakdown_table = Table(table_data, colWidths=[380, 143])
    breakdown_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, primary_color),
                ("LINEBELOW", (0, 1), (-1, -2), 0.5, border_color),
                ("LINEBELOW", (0, -2), (-1, -2), 1.5, primary_color),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0fdf4")),
                (
                    "LINEBELOW",
                    (0, -1),
                    (-1, -1),
                    1.5,
                    colors.HexColor("#15803d"),
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(breakdown_table)
    story.append(Spacer(1, 14))

    # 4. Attestation légale
    prop_addr_str = (
        f"{property_info.get('address', '')}, "
        f"{property_info.get('postal_code', '')} "
        f"{property_info.get('city', '')}"
    ).strip().rstrip(",")
    declaration_text = (
        "Je soussigné, gérant ou représentant de la société "
        f"<b>{sci_name}</b>, propriétaire et bailleur du logement situé au "
        f"<b>{prop_addr_str}</b>, atteste avoir reçu de Monsieur/Madame "
        f"<b>{t_first} {t_last}</b> la somme de <b>{paid:,.2f} €</b> "
        f"(règlement par {pay_method}), au titre du loyer et des charges "
        f"pour le terme de <b>{period_str}</b> et lui en donne quittance, "
        "sous réserve de tous mes droits et de tous décomptes ultérieurs."
    )
    dec_data = [[Paragraph(declaration_text, legal_style)]]
    dec_table = Table(dec_data, colWidths=[523])
    dec_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("LINELEFT", (0, 0), (0, 0), 3.5, secondary_color),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(dec_table)
    story.append(Spacer(1, 16))

    # 5. Signatures & Mentions légales
    sign_city = sci_info.get("city") or property_info.get("city") or "Paris"
    manager_str = sci_info.get("manager_name") or "Le Gérant"
    footer_text = (
        "<em>Cette quittance annule tout reçu qui aurait pu être donné "
        "pour acompte versé au titre de la même période. "
        "Elle ne constitue pas une renonciation aux loyers ou charges "
        "restant éventuellement dus au titre des termes antérieurs. "
        "Document conforme aux dispositions de la loi n° 89-462 "
        "du 6 juillet 1989. À conserver sans limitation de durée.</em>"
    )
    footer_data = [
        [
            Paragraph(footer_text, footer_style),
            Paragraph(
                f"Fait à {sign_city}, le {pay_date}<br/>"
                f"<b>Pour la SCI {sci_name}</b><br/>"
                f"<font color='#64748b'>{manager_str}</font><br/><br/><br/>"
                f"___________________________<br/>"
                f"<font size='8' color='#94a3b8'>Signature / Cachet</font>",
                ParagraphStyle("Sign", parent=body_style, alignment=1),
            ),
        ]
    ]
    footer_table = Table(footer_data, colWidths=[300, 223])
    footer_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(footer_table)

    doc.build(story)
    return buffer.getvalue()


def save_quittance_to_ged(
    payment_id: int,
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment: Dict[str, Any],
) -> Tuple[bool, str, Optional[int]]:
    """Génère la quittance de loyer PDF et l'enregistre dans la GED.

    Met à jour rent_payments.document_id.

    Args:
        payment_id: Identifiant de l'échéance de loyer.
        sci_info: Dictionnaire des informations de la SCI.
        tenant: Dictionnaire des informations du locataire.
        property_info: Dictionnaire des informations du bien.
        payment: Dictionnaire des informations du paiement.

    Returns:
        Tuple[bool, str, Optional[int]]: (succès, message, id document GED).
    """
    try:
        pdf_bytes = generate_quittance_pdf(
            sci_info, tenant, property_info, payment
        )
        file_size = len(pdf_bytes)

        p_month = int(payment.get("period_month", 1))
        p_year = int(payment.get("period_year", 2026))
        month_str = (
            MONTH_NAMES[p_month] if 1 <= p_month <= 12 else str(p_month)
        )
        t_last = (
            (tenant.get("last_name") or "Locataire").strip().replace(" ", "_")
        )
        filename = f"Quittance_{t_last}_{p_year}_{p_month:02d}.pdf"
        paid_amount = float(payment.get("amount_paid", 0.0) or 0.0)

        # Stockage dans le coffre-fort numérique GED (Cloudinary)
        public_id, secure_url, _ = storage.upload_file(pdf_bytes, filename)

        notes_str = (
            f"Quittance de loyer {month_str} {p_year} - "
            f"{paid_amount:.2f} € (Échéance #{payment_id})"
        )

        tenant_id = tenant.get("id") or payment.get("tenant_id")
        property_id = property_info.get("id") or payment.get("property_id")

        # Vérifier si un document pour cette échéance existe déjà
        existing_doc_id = payment.get("document_id")
        existing_row = None
        if existing_doc_id:
            existing_row = query_one(
                "SELECT id, cloudinary_public_id FROM documents WHERE id = ?;",
                [existing_doc_id],
            )

        if not existing_row:
            existing_row = query_one(
                """
                SELECT id, cloudinary_public_id FROM documents 
                WHERE category = 'Quittance & Reçu de paiement' 
                  AND tenant_id = ? 
                  AND notes LIKE ?;
            """,
                [tenant_id, f"%Échéance #{payment_id}%"],
            )

        if existing_row:
            final_doc_id = existing_row["id"]
            # Nettoyer l'ancien asset Cloudinary si remplacé
            old_pub = existing_row.get("cloudinary_public_id")
            if old_pub and old_pub != public_id:
                try:
                    storage.delete_file(old_pub)
                except Exception:
                    pass

            execute_write(
                """
                UPDATE documents
                SET filename = ?, file_path = ?, cloudinary_public_id = ?,
                    file_size = ?, notes = ?, uploaded_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """,
                [
                    filename,
                    secure_url,
                    public_id,
                    file_size,
                    notes_str,
                    final_doc_id,
                ],
            )
        else:
            final_doc_id = execute_write(
                """
                INSERT INTO documents (
                    category, entity_type, entity_id, property_id, tenant_id,
                    filename, file_path, cloudinary_public_id, file_size, notes
                ) VALUES (
                    'Quittance & Reçu de paiement', 'tenant', ?, ?, ?,
                    ?, ?, ?, ?, ?
                );
            """,
                [
                    tenant_id,
                    property_id,
                    tenant_id,
                    filename,
                    secure_url,
                    public_id,
                    file_size,
                    notes_str,
                ],
            )

        # Associer document_id sur rent_payments
        execute_write(
            "UPDATE rent_payments SET document_id = ? WHERE id = ?;",
            [final_doc_id, payment_id],
        )

        return (
            True,
            (
                "Quittance PDF enregistrée et classée dans la GED sous la "
                f"référence #{final_doc_id}."
            ),
            final_doc_id,
        )

    except Exception as e:
        return (
            False,
            (
                "Erreur lors de la génération / archivage de la quittance : "
                f"{str(e)}"
            ),
            None,
        )
