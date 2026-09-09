"""
Module d'indexation annuelle des loyers selon l'Indice de Référence des Loyers (IRL) de l'INSEE.
Conforme à l'article 17-1 de la loi du 6 juillet 1989.
"""
from typing import Dict, Any

def calculate_irl_revision(old_rent: float, old_irl: float, new_irl: float) -> float:
    """
    Calcule le nouveau loyer selon la formule légale INSEE :
    Nouveau Loyer = Ancien Loyer * (Nouvel IRL / Ancien IRL)
    Arrondi à 2 décimales.
    """
    if old_irl <= 0 or new_irl <= 0 or old_rent <= 0:
        return old_rent
    return round(old_rent * (new_irl / old_irl), 2)

def generate_irl_letter_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    old_rent: float,
    new_rent: float,
    old_quarter: str,
    old_val: float,
    new_quarter: str,
    new_val: float,
    effective_date: str
) -> str:
    """
    Génère la lettre formelle de révision annuelle de loyer au format HTML imprimable.
    """
    diff = new_rent - old_rent
    pct = ((new_val - old_val) / old_val * 100.0) if old_val > 0 else 0.0

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Notification de révision de loyer - {tenant.get('first_name')} {tenant.get('last_name')}</title>
<style>
    @media print {{
        body {{ margin: 0; padding: 20px; font-size: 12pt; background: #fff !important; color: #000 !important; }}
        .no-print {{ display: none !important; }}
        .letter-card {{ box-shadow: none !important; border: none !important; padding: 0 !important; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #f1f5f9;
        margin: 0;
        padding: 30px;
        color: #1e293b;
        line-height: 1.6;
    }}
    .letter-card {{
        max-width: 720px;
        margin: 0 auto;
        background: #ffffff;
        padding: 50px;
        border-radius: 12px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
    }}
    .header-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 30px;
        margin-bottom: 40px;
    }}
    .sender {{
        font-size: 14px;
    }}
    .recipient {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 8px;
        font-size: 14px;
    }}
    .object {{
        font-weight: 700;
        color: #1e3a8a;
        margin-bottom: 25px;
        border-left: 4px solid #2563eb;
        padding-left: 12px;
        font-size: 15px;
    }}
    .formula-box {{
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        padding: 18px 22px;
        margin: 25px 0;
        font-size: 14px;
    }}
    .formula-box table {{
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
    }}
    .formula-box td {{
        padding: 6px 0;
    }}
    .formula-box td.val {{
        font-weight: 700;
        text-align: right;
        color: #1e3a8a;
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
    .btn-print:hover {{ background-color: #1d4ed8; }}
</style>
</head>
<body>

<div class="no-print" style="max-width: 720px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer / Télécharger en PDF</button>
</div>

<div class="letter-card">
    <div class="header-grid">
        <div class="sender">
            <strong>{sci_info.get('name', 'SCI')}</strong><br>
            {sci_info.get('address', '')}<br>
            {sci_info.get('postal_code', '')} {sci_info.get('city', '')}<br>
            Tél : {sci_info.get('manager_phone', '')}<br>
            Email : {sci_info.get('manager_email', '')}
        </div>
        <div class="recipient">
            <strong>{tenant.get('first_name')} {tenant.get('last_name').upper()}</strong><br>
            {property_info.get('address', '')}<br>
            {property_info.get('postal_code', '')} {property_info.get('city', '')}
        </div>
    </div>

    <div style="text-align: right; font-size: 13px; color: #64748b; margin-bottom: 25px;">
        Fait à {sci_info.get('city', 'Nancy')}, le {effective_date}
    </div>

    <div class="object">
        Objet : Révision annuelle du loyer en application de la clause d'indexation
    </div>

    <p>Madame, Monsieur,</p>

    <p>
        Conformément aux stipulations de votre contrat de bail signé le <strong>{tenant.get('lease_start')}</strong>
        concernant le logement situé au <strong>{property_info.get('address')}, {property_info.get('postal_code')} {property_info.get('city')}</strong>,
        le loyer fait l'objet d'une révision annuelle basée sur la variation de l'Indice de Référence des Loyers (IRL) publié par l'INSEE.
    </p>

    <div class="formula-box">
        <strong>Détail du calcul de révision légale :</strong>
        <table>
            <tr>
                <td>Loyer mensuel actuel hors charges :</td>
                <td class="val">{old_rent:.2f} €</td>
            </tr>
            <tr>
                <td>Indice IRL d'origine ({old_quarter}) :</td>
                <td class="val">{old_val:.2f}</td>
            </tr>
            <tr>
                <td>Nouvel indice IRL applicable ({new_quarter}) :</td>
                <td class="val">{new_val:.2f} (+{pct:.2f} %)</td>
            </tr>
            <tr style="border-top: 1px solid #cbd5e1;">
                <td style="padding-top: 10px; font-weight: 600;">Nouveau loyer mensuel hors charges :</td>
                <td class="val" style="padding-top: 10px; font-size: 16px;">{new_rent:.2f} € (+{diff:.2f} €/mois)</td>
            </tr>
        </table>
    </div>

    <p>
        À ce loyer principal s'ajoute votre provision mensuelle sur charges de <strong>{float(tenant.get('charges_provision', 0.0)):.2f} €</strong>,
        portant le montant total à régler chaque mois à <strong>{new_rent + float(tenant.get('charges_provision', 0.0)):.2f} € charges comprises</strong>.
    </p>

    <p>
        Ce nouveau montant prend effet à compter du terme de <strong>{effective_date}</strong>.
        Nous vous remercions de bien vouloir mettre à jour le montant de votre virement automatique à cette date.
    </p>

    <p>Restant à votre disposition pour tout renseignement complémentaire, nous vous prions d'agréer, Madame, Monsieur, l'expression de nos salutations distinguées.</p>

    <div style="margin-top: 50px; text-align: right;">
        <strong>Pour la société {sci_info.get('name', 'SCI')}</strong><br>
        Le Gérant
    </div>
</div>

</body>
</html>
"""
    return html
