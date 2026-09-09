"""
Moteur de calcul financier pour les emprunts bancaires & amortissements de crédits.
Spécifique pour SCI à l'IS : ventilation rigoureuse capital / intérêts déductibles / assurance.
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime, date

def calculate_monthly_payment(principal: float, annual_rate_pct: float, duration_months: int) -> float:
    """
    Calcule la mensualité hors assurance à taux fixe (formule standard française).
    M = P * [r / (1 - (1+r)^(-n))]
    """
    if principal <= 0 or duration_months <= 0:
        return 0.0
    if annual_rate_pct <= 0:
        return principal / duration_months

    r = (annual_rate_pct / 100.0) / 12.0
    numerator = principal * r
    denominator = 1.0 - (1.0 + r) ** (-duration_months)
    return numerator / denominator

def generate_amortization_schedule(loan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Génère l'échéancier complet mois par mois d'un crédit immobilier.
    """
    principal = float(loan.get("amount", 0.0))
    annual_rate = float(loan.get("annual_interest_rate", 0.0))
    duration_months = int(loan.get("duration_months", 240))
    insurance = float(loan.get("monthly_insurance", 0.0))
    start_date_str = loan.get("start_date", "2024-01-01")

    try:
        current_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d").date()
    except Exception:
        current_date = date.today()

    monthly_payment_no_ins = calculate_monthly_payment(principal, annual_rate, duration_months)
    monthly_rate = (annual_rate / 100.0) / 12.0

    schedule = []
    balance = principal

    for m in range(1, duration_months + 1):
        if balance <= 0.001:
            break

        interest = balance * monthly_rate
        # Sur le dernier mois, ajustement de l'arrondi
        if m == duration_months or balance < monthly_payment_no_ins:
            capital = balance
            monthly_total_no_ins = capital + interest
        else:
            capital = monthly_payment_no_ins - interest
            monthly_total_no_ins = monthly_payment_no_ins

        end_balance = max(0.0, balance - capital)
        total_payment = monthly_total_no_ins + insurance

        schedule.append({
            "month_num": m,
            "date": current_date.strftime("%Y-%m-%d"),
            "year": current_date.year,
            "month": current_date.month,
            "start_balance": balance,
            "capital": capital,
            "interest": interest,
            "insurance": insurance,
            "total_monthly": total_payment,
            "end_balance": end_balance
        })

        balance = end_balance

        # Mois suivant
        new_year = current_date.year + (current_date.month // 12)
        new_month = (current_date.month % 12) + 1
        current_date = current_date.replace(year=new_year, month=new_month)

    return schedule

def get_annual_loan_breakdown(loan: Dict[str, Any], target_year: int) -> Dict[str, float]:
    """
    Calcule pour une année donnée le total du capital amorti, des intérêts déductibles et de l'assurance.
    """
    schedule = generate_amortization_schedule(loan)
    year_rows = [row for row in schedule if row["year"] == target_year]

    return {
        "capital_repaid": sum(r["capital"] for r in year_rows),
        "interest_paid": sum(r["interest"] for r in year_rows),
        "insurance_paid": sum(r["insurance"] for r in year_rows),
        "total_paid": sum(r["total_monthly"] for r in year_rows),
        "remaining_balance": year_rows[-1]["end_balance"] if year_rows else 0.0
    }
