"""
PDF generation for receipts, loan agreements, and reports.
Uses ReportLab.
"""
from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from app.config import get_config
from app.utils.formatters import fmt_currency, fmt_date, fmt_datetime, fmt_weight

GOLD = colors.HexColor("#D4A017")
DARK = colors.HexColor("#1A1A2E")
LIGHT_BG = colors.HexColor("#FFF8E1")

styles = getSampleStyleSheet()
heading_style = ParagraphStyle("Heading", fontSize=14, fontName="Helvetica-Bold", textColor=DARK)
sub_style = ParagraphStyle("Sub", fontSize=9, fontName="Helvetica", textColor=colors.grey)
normal_style = ParagraphStyle("Normal", fontSize=10, fontName="Helvetica")
bold_style = ParagraphStyle("Bold", fontSize=10, fontName="Helvetica-Bold")


def _business_header(cfg) -> list:
    elements = []
    elements.append(Paragraph(cfg.business_name, ParagraphStyle(
        "BizName", fontSize=18, fontName="Helvetica-Bold", textColor=DARK, alignment=TA_CENTER
    )))
    elements.append(Paragraph(cfg.get("business_address", ""), ParagraphStyle(
        "BizAddr", fontSize=9, fontName="Helvetica", textColor=colors.grey, alignment=TA_CENTER
    )))
    elements.append(Paragraph(
        f"Phone: {cfg.get('business_phone', '')}  |  Email: {cfg.get('business_email', '')}",
        ParagraphStyle("BizContact", fontSize=9, alignment=TA_CENTER)
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=GOLD, spaceAfter=8))
    return elements


def generate_repayment_receipt(repayment: dict, loan: dict, customer: dict, path: str) -> None:
    cfg = get_config()
    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    elements = _business_header(cfg)

    elements.append(Paragraph("PAYMENT RECEIPT", ParagraphStyle(
        "ReceiptTitle", fontSize=16, fontName="Helvetica-Bold", textColor=GOLD,
        alignment=TA_CENTER, spaceBefore=8, spaceAfter=4
    )))
    if repayment.get("is_reversed"):
        elements.append(Paragraph("*** REVERSED — NOT VALID ***", ParagraphStyle(
            "Reversed", fontSize=14, fontName="Helvetica-Bold", textColor=colors.red,
            alignment=TA_CENTER, spaceAfter=6
        )))
    elements.append(Paragraph(
        f"Receipt No: <b>{repayment.get('receipt_number')}</b>  |  "
        f"Date: <b>{fmt_date(repayment.get('payment_date'))}</b>",
        ParagraphStyle("ReceiptMeta", fontSize=10, alignment=TA_CENTER, spaceAfter=12)
    ))

    data = [
        ["Customer:", customer.get("full_name", ""), "Loan No:", loan.get("loan_number", "")],
        ["Customer ID:", customer.get("customer_id", ""), "Disbursed:", fmt_date(loan.get("disbursement_date"))],
        ["Mobile:", customer.get("mobile", ""), "Maturity:", fmt_date(loan.get("maturity_date"))],
    ]
    t = Table(data, colWidths=[4*cm, 7*cm, 4*cm, 5*cm])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 10))

    pay_data = [
        ["", "Amount"],
        ["Principal Paid", fmt_currency(repayment.get("principal_paid", 0))],
        ["Interest Paid", fmt_currency(repayment.get("interest_paid", 0))],
        ["Fee Paid", fmt_currency(repayment.get("fee_paid", 0))],
        ["Penalty Paid", fmt_currency(repayment.get("penalty_paid", 0))],
        ["TOTAL PAID", fmt_currency(repayment.get("total_paid", 0))],
        ["Remaining Principal", fmt_currency(repayment.get("balance_principal_after", 0))],
        ["Remaining Total Due", fmt_currency(
            repayment.get("total_outstanding_after", repayment.get("balance_principal_after", 0))
        )],
    ]
    pt = Table(pay_data, colWidths=[10*cm, 9*cm])
    pt.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -3), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -3), (-1, -3), LIGHT_BG),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#D4EDDA")),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -4), [colors.white, colors.HexColor("#FAFAFA")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(pt)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"Payment Mode: <b>{repayment.get('payment_mode', '').title()}</b>  |  "
        f"Ref: {repayment.get('transaction_ref') or '—'}",
        normal_style
    ))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Authorised Signature", ParagraphStyle(
        "Sig", fontSize=10, alignment=TA_RIGHT, textColor=colors.grey
    )))
    elements.append(Paragraph(
        f"Generated: {fmt_datetime(datetime.now())}",
        ParagraphStyle("Footer", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))
    doc.build(elements)


def generate_report_pdf(report_key: str, from_dt, to_dt, path: str) -> None:
    """Generic report PDF. Queries data and formats into a table."""
    from app.services.loan_service import get_loan_service
    from app.services.customer_service import get_customer_service
    cfg = get_config()

    doc = SimpleDocTemplate(path, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    elements = _business_header(cfg)

    title_map = {
        "active_loans": "Active Loans Report",
        "overdue_loans": "Overdue Loans Report",
        "outstanding_summary": "Outstanding Balance Summary",
        "daily_disbursements": "Daily Disbursements",
        "daily_collections": "Daily Collections",
        "closed_loans": "Closed Loans Report",
        "upcoming_maturities": "Upcoming Loan Maturities",
        "collateral_inventory": "Collateral Inventory",
        "interest_income": "Interest Income Report",
    }
    elements.append(Paragraph(title_map.get(report_key, report_key.replace("_", " ").title()),
                               heading_style))
    elements.append(Paragraph(
        f"Period: {fmt_date(from_dt)} to {fmt_date(to_dt)}", sub_style
    ))
    elements.append(Spacer(1, 10))

    # Fetch data
    if report_key == "active_loans":
        loans = get_loan_service().search_loans(status="active", limit=1000)
        headers = ["Loan #", "Customer", "Principal", "Disbursed", "Maturity", "Outstanding"]
        rows = [headers] + [
            [lo["loan_number"], lo["customer_name"],
             fmt_currency(lo["principal_amount"]),
             fmt_date(lo["disbursement_date"]),
             fmt_date(lo["maturity_date"]),
             fmt_currency(lo["total_outstanding"])]
            for lo in loans
        ]
    elif report_key == "overdue_loans":
        loans = get_loan_service().search_loans(status="overdue", limit=1000)
        headers = ["Loan #", "Customer", "Mobile", "Overdue Since", "Outstanding"]
        rows = [headers] + [
            [lo["loan_number"], lo["customer_name"], lo["customer_mobile"],
             fmt_date(lo["maturity_date"]), fmt_currency(lo["total_outstanding"])]
            for lo in loans
        ]
    else:
        rows = [["Report", "Details"], [report_key, f"From {fmt_date(from_dt)} to {fmt_date(to_dt)}"]]

    col_count = len(rows[0]) if rows else 2
    col_width = 19*cm / col_count
    t = Table(rows, colWidths=[col_width]*col_count, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFA")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"Generated: {fmt_datetime(datetime.now())}  |  Total rows: {len(rows)-1}",
        sub_style
    ))
    doc.build(elements)
