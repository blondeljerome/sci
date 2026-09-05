"""
Générateur de quittance de loyer au format HTML imprimable.
Conforme aux dispositions de la loi n° 89-462 du 6 juillet 1989.
"""
from typing import Dict, Any

def generate_quittance_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment: Dict[str, Any]
) -> str:
    """
    Génère un document HTML élégant et imprimable pour la quittance de loyer.
    """
    month_names = [
        "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]
    period_str = f"{month_names[payment.get('period_month', 1)]} {payment.get('period_year', 2026)}"
    
    rent = float(payment.get("rent_amount", 0.0))
    charges = float(payment.get("charges_amount", 0.0))
    total = rent + charges
    paid = float(payment.get("amount_paid", total))
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Quittance de loyer - {period_str}</title>
<style>
    @media print {{
        body {{ margin: 0; padding: 20px; font-size: 13pt; background: #fff !important; color: #000 !important; }}
        .no-print {{ display: none !important; }}
        .quittance-card {{ box-shadow: none !important; border: 1px solid #ccc !important; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
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
    .btn-print {{
        background-color: #2563eb;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 600;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 20px;
    }}
    .btn-print:hover {{
        background-color: #1d4ed8;
    }}
</style>
</head>
<body>

<div class="no-print" style="max-width: 720px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer / Télécharger en PDF</button>
</div>

<div class="quittance-card">
    <div class="header">
        <div>
            <h1>QUITTANCE DE LOYER</h1>
            <div class="subtitle">Période concernée : <strong>{period_str}</strong></div>
        </div>
        <div style="text-align: right; font-size: 13px; color: #64748b;">
            Date d'émission : {payment.get('payment_date') or payment.get('due_date')}<br>
            Quittance réf : #{payment.get('id', 0):05d}
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h3>Bailleur</h3>
            <strong>{sci_info.get('name', 'SCI')}</strong><br>
            {f"SIREN : {sci_info.get('siren')}<br>" if sci_info.get('siren') else ""}
            {sci_info.get('address', '')}<br>
            {sci_info.get('postal_code', '')} {sci_info.get('city', '')}<br>
            {f"Gérant : {sci_info.get('manager_name')}<br>" if sci_info.get('manager_name') else ""}
            {f"Contact : {sci_info.get('manager_email')}" if sci_info.get('manager_email') else ""}
        </div>

        <div class="box">
            <h3>Locataire</h3>
            <strong>{tenant.get('first_name', '')} {tenant.get('last_name', '')}</strong><br>
            Logement loué :<br>
            {property_info.get('name', '')}<br>
            {property_info.get('address', '')}<br>
            {property_info.get('postal_code', '')} {property_info.get('city', '')}
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
        Je soussigné, gérant ou représentant de la société <strong>{sci_info.get('name', 'SCI')}</strong>,
        propriétaire et bailleur du logement désigné ci-dessus, atteste avoir reçu de Monsieur/Madame
        <strong>{tenant.get('first_name', '')} {tenant.get('last_name', '')}</strong>
        la somme de <strong>{paid:.2f} €</strong> (règlement par {payment.get('payment_method', 'Virement')}),
        pour loyer et charges du terme de <strong>{period_str}</strong> et lui en donne quittance,
        sous réserve de tous mes droits et de tous décomptes ultérieurs.
    </div>

    <div class="footer-signatures">
        <div style="font-size: 12px; color: #94a3b8; max-width: 380px;">
            <em>Cette quittance annule tout reçu qui aurait pu être donné pour acompte versé au titre de la même période. À conserver sans limitation de durée.</em>
        </div>
        <div class="signature-box">
            Fait à {sci_info.get('city', 'Paris')}, le {payment.get('payment_date') or payment.get('due_date')}<br>
            <strong>Le Bailleur / Le Gérant</strong>
            <div class="signature-space"></div>
        </div>
    </div>
</div>

</body>
</html>
"""
    return html
