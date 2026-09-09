"""
Générateur de documents juridiques et administratifs pour la gestion de SCI.
- Avis d'échéance (Appel de loyer)
- Relance d'impayé amiable (J+7)
- Mise en demeure de payer (J+21 - Clause résolutoire)
- Procès-Verbal d'Assemblée Générale Ordinaire (PV d'AGO annuelle d'approbation des comptes)
"""
from typing import Dict, Any

MONTH_NAMES = [
    "", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
    "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
]

# 1. AVIS D'ECHEANCE / APPEL DE LOYER
def generate_avis_echeance_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    month: int,
    year: int,
    due_date: str
) -> str:
    period_str = f"{MONTH_NAMES[month]} {year}"
    rent = float(tenant.get("rent_amount", 0.0))
    charges = float(tenant.get("charges_provision", 0.0))
    total = rent + charges

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Avis d'échéance - {period_str} - {tenant.get('last_name')}</title>
<style>
    @media print {{
        body {{ margin: 0; padding: 20px; font-size: 12pt; background: #fff !important; color: #000 !important; }}
        .no-print {{ display: none !important; }}
        .card {{ box-shadow: none !important; border: 1px solid #ccc !important; }}
    }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        background-color: #f1f5f9;
        margin: 0;
        padding: 30px;
        color: #1e293b;
    }}
    .card {{
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
        padding-bottom: 15px;
        margin-bottom: 25px;
    }}
    .header h1 {{ margin: 0; color: #1e3a8a; font-size: 22px; }}
    .grid-2 {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 25px;
        margin-bottom: 25px;
    }}
    .box {{
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        padding: 16px;
        border-radius: 8px;
        font-size: 14px;
        line-height: 1.5;
    }}
    .box h3 {{ margin: 0 0 8px 0; font-size: 13px; text-transform: uppercase; color: #2563eb; }}
    table.breakdown {{
        width: 100%;
        border-collapse: collapse;
        margin: 25px 0;
    }}
    table.breakdown th, table.breakdown td {{
        padding: 12px 14px;
        border-bottom: 1px solid #e2e8f0;
    }}
    table.breakdown th {{ background: #f1f5f9; text-align: left; font-size: 14px; }}
    table.breakdown tr.total td {{ font-weight: 700; font-size: 16px; color: #1e3a8a; border-top: 2px solid #2563eb; }}
    .bank-details {{
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        padding: 16px;
        border-radius: 8px;
        margin-top: 25px;
        font-size: 14px;
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
    }}
</style>
</head>
<body>

<div class="no-print" style="max-width: 720px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer / Télécharger en PDF</button>
</div>

<div class="card">
    <div class="header">
        <div>
            <h1>AVIS D'ÉCHÉANCE / APPEL DE LOYER</h1>
            <div style="color: #64748b; font-size: 14px; margin-top: 4px;">Période : <strong>{period_str}</strong></div>
        </div>
        <div style="text-align: right; font-size: 13px; color: #64748b;">
            Date d'échéance : <strong>{due_date}</strong>
        </div>
    </div>

    <div class="grid-2">
        <div class="box">
            <h3>Bailleur</h3>
            <strong>{sci_info.get('name', 'SCI')}</strong><br>
            {sci_info.get('address', '')}<br>
            {sci_info.get('postal_code', '')} {sci_info.get('city', '')}<br>
            Email : {sci_info.get('manager_email', '')}
        </div>
        <div class="box">
            <h3>Locataire</h3>
            <strong>{tenant.get('first_name')} {tenant.get('last_name').upper()}</strong><br>
            {property_info.get('address', '')}<br>
            {property_info.get('postal_code', '')} {property_info.get('city', '')}
        </div>
    </div>

    <table class="breakdown">
        <thead>
            <tr>
                <th>Désignation</th>
                <th style="text-align: right;">Montant</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Loyer mensuel principal ({period_str})</td>
                <td style="text-align: right;">{rent:.2f} €</td>
            </tr>
            <tr>
                <td>Provision mensuelle sur charges locatives</td>
                <td style="text-align: right;">{charges:.2f} €</td>
            </tr>
            <tr class="total">
                <td>TOTAL À RÉGLER AVANT LE {due_date}</td>
                <td style="text-align: right; color: #2563eb;">{total:.2f} €</td>
            </tr>
        </tbody>
    </table>

    <div class="bank-details">
        <strong>Coordonnées bancaires pour le règlement par virement :</strong><br>
        Bénéficiaire : <strong>{sci_info.get('name', 'SCI')}</strong><br>
        IBAN : <code>{sci_info.get('iban') or 'À renseigner dans les Paramètres'}</code><br>
        BIC : <code>{sci_info.get('bic') or ''}</code><br>
        Motif : <em>Loyer {period_str} - {tenant.get('last_name')}</em>
    </div>

    <p style="font-size: 12px; color: #94a3b8; margin-top: 30px;">
        <em>Ce document constitue un appel de loyer et ne vaut pas quittance. La quittance vous sera délivrée dès réception de votre règlement.</em>
    </p>
</div>
</body>
</html>
"""
    return html

# 2. RELANCE AMIABLE D'IMPAYE (J+7)
def generate_relance_amiable_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment_record: Dict[str, Any]
) -> str:
    period_str = f"{MONTH_NAMES[payment_record.get('period_month', 1)]} {payment_record.get('period_year', 2026)}"
    balance = float(payment_record.get("total_due", 0.0)) - float(payment_record.get("amount_paid", 0.0))

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Relance loyer impayé - {tenant.get('last_name')}</title>
<style>
    body {{ font-family: -apple-system, sans-serif; padding: 40px; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
    .card {{ max-width: 700px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; border: 1px solid #e2e8f0; }}
    .alert-banner {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; color: #92400e; font-weight: 600; }}
    .btn-print {{ background-color: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }}
</style>
</head>
<body>
<div style="max-width: 700px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer</button>
</div>
<div class="card">
    <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
        <div>
            <strong>{sci_info.get('name', 'SCI')}</strong><br>
            {sci_info.get('address', '')}<br>
            {sci_info.get('postal_code', '')} {sci_info.get('city', '')}
        </div>
        <div style="text-align: right;">
            <strong>{tenant.get('first_name')} {tenant.get('last_name').upper()}</strong><br>
            {property_info.get('address', '')}<br>
            {property_info.get('postal_code', '')} {property_info.get('city', '')}
        </div>
    </div>

    <div class="alert-banner">
        Objet : Rappel amiable - Loyer en attente pour le terme de {period_str}
    </div>

    <p>Madame, Monsieur,</p>
    <p>
        Sauf erreur ou omission de notre part, nous constatons que le loyer du terme de <strong>{period_str}</strong>
        concernant votre logement situé au <strong>{property_info.get('address')}</strong> n'a pas été crédité sur notre compte bancaire à ce jour.
    </p>

    <div style="background: #f1f5f9; padding: 15px 20px; border-radius: 8px; margin: 20px 0;">
        <strong>Montant restant dû : <span style="color: #dc2626; font-size: 18px;">{balance:.2f} €</span></strong><br>
        Échéance initiale : {payment_record.get('due_date')}
    </div>

    <p>
        S'agissant très probablement d'un simple oubli ou d'un retard d'exécution bancaire indépendant de votre volonté,
        nous vous remercions de bien vouloir régulariser votre situation dans les plus brefs délais par virement.
    </p>

    <div style="background: #eff6ff; padding: 12px 16px; border-radius: 6px; font-size: 13px;">
        IBAN SCI : <code>{sci_info.get('iban', '')}</code>
    </div>

    <p>Si votre virement a été émis entre-temps, nous vous prions de ne pas tenir compte de ce rappel.</p>

    <p>Restant à votre disposition, nous vous prions d'agréer, Madame, Monsieur, nos salutations distinguées.</p>

    <div style="margin-top: 40px; text-align: right;">
        <strong>Pour {sci_info.get('name', 'SCI')}</strong><br>La Gérance
    </div>
</div>
</body>
</html>
"""
    return html

# 3. MISE EN DEMEURE FORMELLE (J+21 - LRAR)
def generate_mise_en_demeure_html(
    sci_info: Dict[str, Any],
    tenant: Dict[str, Any],
    property_info: Dict[str, Any],
    payment_record: Dict[str, Any]
) -> str:
    period_str = f"{MONTH_NAMES[payment_record.get('period_month', 1)]} {payment_record.get('period_year', 2026)}"
    balance = float(payment_record.get("total_due", 0.0)) - float(payment_record.get("amount_paid", 0.0))

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>Mise en demeure de payer - {tenant.get('last_name')}</title>
<style>
    body {{ font-family: -apple-system, sans-serif; padding: 40px; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
    .card {{ max-width: 720px; margin: 0 auto; background: white; padding: 50px; border-radius: 8px; border: 1px solid #cbd5e1; }}
    .badge-urgent {{ background: #fee2e2; color: #991b1b; padding: 8px 12px; border-radius: 4px; font-weight: 700; display: inline-block; margin-bottom: 20px; }}
    .btn-print {{ background-color: #dc2626; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }}
</style>
</head>
<body>
<div style="max-width: 720px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer LRAR</button>
</div>
<div class="card">
    <div class="badge-urgent">LETTRE RECOMMANDÉE AVEC AVIS DE RÉCEPTION (LRAR)</div>

    <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
        <div>
            <strong>{sci_info.get('name', 'SCI')}</strong><br>
            {sci_info.get('address', '')}<br>
            {sci_info.get('postal_code', '')} {sci_info.get('city', '')}
        </div>
        <div style="text-align: right;">
            <strong>{tenant.get('first_name')} {tenant.get('last_name').upper()}</strong><br>
            {property_info.get('address', '')}<br>
            {property_info.get('postal_code', '')} {property_info.get('city', '')}
        </div>
    </div>

    <div style="font-weight: 700; color: #991b1b; margin-bottom: 20px;">
        OBJET : MISE EN DEMEURE DE PAYER SOUS HUITINE AVANT MISE EN JEU DE LA CLAUSE RÉSOLUTOIRE
    </div>

    <p>Madame, Monsieur,</p>
    <p>
        Malgré nos précédentes relances restées sans effet, nous constatons que vous n'avez toujours pas réglé la somme de
        <strong>{balance:.2f} €</strong> au titre du loyer et des charges du mois de <strong>{period_str}</strong>,
        pour le logement que vous louez au <strong>{property_info.get('address')}</strong>.
    </p>

    <p>
        Par la présente lettre valant <strong>MISE EN DEMEURE</strong>, nous vous sommons formellement de nous faire parvenir
        le règlement intégral de cette somme de <strong>{balance:.2f} €</strong> dans un délai impératif de <strong>8 jours</strong>
        à compter de la réception de ce courrier.
    </p>

    <p>
        À défaut de règlement dans ce délai :
        <ul>
            <li>Nous transmettrons le dossier à un Commissaire de Justice (Huissier) pour délivrance d'un commandement de payer.</li>
            <li>La <strong>clause résolutoire</strong> inscrite à votre contrat de bail sera actionnée, entraînant la résiliation de plein droit de votre bail et l'engagement d'une procédure d'expulsion devant le juge des contentieux de la protection.</li>
            <li>Votre garant ({tenant.get('guarantor_info') or 'caution solidaire'}) sera immédiatement appelé en garantie.</li>
        </ul>
    </p>

    <p>Nous espérons ne pas avoir à en arriver à de telles extrémités et comptons sur votre prompte régularisation.</p>

    <div style="margin-top: 40px; text-align: right;">
        <strong>Le Gérant de la SCI {sci_info.get('name')}</strong>
    </div>
</div>
</body>
</html>
"""
    return html

# 4. PROCES-VERBAL D'ASSEMBLEE GENERALE ORDINAIRE (PV D'AGO)
def generate_pv_ago_html(
    sci_info: Dict[str, Any],
    fiscal_year: int,
    gross_income: float,
    operating_expenses: float,
    amortizations: float,
    financial_expenses: float,
    rcai: float,
    is_tax: float,
    net_result: float
) -> str:
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>PV Assemblée Générale Ordinaire {fiscal_year} - {sci_info.get('name')}</title>
<style>
    body {{ font-family: -apple-system, Georgia, serif; padding: 40px; background: #f8fafc; color: #1e293b; line-height: 1.6; }}
    .card {{ max-width: 760px; margin: 0 auto; background: white; padding: 50px; border-radius: 8px; border: 1px solid #cbd5e1; }}
    h1 {{ font-size: 18px; text-align: center; text-transform: uppercase; border-bottom: 2px solid #1e3a8a; padding-bottom: 12px; }}
    h2 {{ font-size: 15px; margin-top: 25px; color: #1e3a8a; }}
    .btn-print {{ background-color: #2563eb; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }}
</style>
</head>
<body>
<div style="max-width: 760px; margin: 0 auto 10px auto; text-align: right;">
    <button class="btn-print" onclick="window.print()">🖨️ Imprimer le PV d'AGO</button>
</div>
<div class="card">
    <div style="text-align: center; font-size: 13px; color: #64748b; margin-bottom: 15px;">
        Société Civile Immobilière au capital social de 1 000 euros<br>
        Siège social : {sci_info.get('address')}, {sci_info.get('postal_code')} {sci_info.get('city')}<br>
        SIREN : {sci_info.get('siren') or 'En cours d\'immatriculation'}
    </div>

    <h1>PROCÈS-VERBAL DE L'ASSEMBLÉE GÉNÉRALE ORDINAIRE ANNUELLE<br>DU 30 JUIN {fiscal_year + 1}</h1>

    <p>
        L'an <strong>{fiscal_year + 1}</strong>, le 30 juin à 18h00, les associés de la société <strong>{sci_info.get('name')}</strong>
        se sont réunis au siège social en Assemblée Générale Ordinaire, sous la présidence de <strong>{sci_info.get('manager_name') or 'la Gérance'}</strong>.
    </p>

    <h2>ORDRE DU JOUR</h2>
    <ol>
        <li>Rapport de gestion de la gérance sur l'exercice clos le 31 décembre {fiscal_year}.</li>
        <li>Présentation et approbation des comptes annuels de l'exercice (Liasse IS 2065).</li>
        <li>Quitus à la gérance.</li>
        <li>Affectation du résultat comptable de l'exercice.</li>
    </ol>

    <h2>PREMIÈRE RÉSOLUTION - APPROBATION DES COMPTES</h2>
    <p>L'Assemblée Générale, après avoir pris connaissance du rapport de la gérance, approuve les comptes de l'exercice {fiscal_year} faisant ressortir les éléments comptables suivants :</p>
    <ul>
        <li>Produits d'exploitation (loyers nets) : <strong>{gross_income:,.2f} €</strong></li>
        <li>Charges d'exploitation déductibles : <strong>{operating_expenses:,.2f} €</strong></li>
        <li>Dotations aux amortissements (bâti & mobilier) : <strong>{amortizations:,.2f} €</strong></li>
        <li>Charges financières (intérêts d'emprunts) : <strong>{financial_expenses:,.2f} €</strong></li>
        <li>Résultat Courant Avant Impôt (RCAI) : <strong>{rcai:,.2f} €</strong></li>
        <li>Impôt sur les Sociétés (IS) dû : <strong>{is_tax:,.2f} €</strong></li>
        <li><strong>Résultat Net Comptable de l'exercice : {net_result:,.2f} €</strong> ({'Bénéfice' if net_result >= 0 else 'Perte'})</li>
    </ul>
    <p><em>Cette résolution est adoptée à l'unanimité des associés.</em></p>

    <h2>DEUXIÈME RÉSOLUTION - QUITUS À LA GÉRANCE</h2>
    <p>L'Assemblée Générale donne quitus entier et sans réserve au gérant pour l'accomplissement de son mandat au cours de l'exercice écoulé.</p>
    <p><em>Cette résolution est adoptée à l'unanimité.</em></p>

    <h2>TROISIÈME RÉSOLUTION - AFFECTATION DU RÉSULTAT</h2>
    <p>
        L'Assemblée Générale décide d'affecter le résultat net de l'exercice, s'élevant à <strong>{net_result:,.2f} €</strong>,
        intégralement au compte de <strong>Report à nouveau</strong> de la société.
    </p>
    <p><em>Cette résolution est adoptée à l'unanimité.</em></p>

    <p style="margin-top: 40px;">
        L'ordre du jour étant épuisé, la séance est levée à 19h00.<br>
        De tout ce que dessus, il a été dressé le présent procès-verbal signé par l'ensemble des associés présents.
    </p>

    <div style="display: flex; justify-content: space-between; margin-top: 60px;">
        <div>
            <strong>Pour la Gérance</strong><br><br><br>
            ____________________________
        </div>
        <div>
            <strong>Pour les Associés</strong><br><br><br>
            ____________________________
        </div>
    </div>
</div>
</body>
</html>
"""
    return html
