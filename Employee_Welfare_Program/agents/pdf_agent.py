import os
import json
from datetime import datetime
from typing import Optional
from pypdf import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()


def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_invoice_data(text: str, llm: ChatOpenAI) -> dict:
    system_prompt = """You are an invoice data extraction specialist.
Extract the following data points from the invoice text and return them as JSON:
- name: The name of the person or company the invoice is billed to (customer/bill-to name)
- invoice_date: The date of the invoice in ISO format (YYYY-MM-DD)
- items: A list of items/services purchased, each with:
    - description: Item or service description
    - category: Best-fit category (e.g. Electronics, Office Supplies, Travel, Medical, etc.)
    - amount: Item amount as a float
- total_amount: The total invoice amount as a float
- currency: The currency code (e.g. USD, EUR, INR)

Return only valid JSON with no explanation or markdown."""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Extract invoice data from this text:\n\n{text}"),
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    # Strip markdown code fences if the model wrapped the JSON
    if content.startswith("```"):
        parts = content.split("```")
        content = parts[1] if len(parts) > 1 else content
        if content.startswith("json"):
            content = content[4:]
    content = content.strip()

    return json.loads(content)


def validate_invoice(invoice_data: dict, instructions: dict) -> dict:
    """
    Validate extracted invoice data against the provided instructions.

    Instructions format:
    {
        "expected_name"   : str,         # Name that must appear on the invoice
        "valid_categories": list[str],   # Acceptable item categories
        "category_limits" : dict,        # Max amount per category: {"Category": max_amount}
                                         # Use key "overall" for a total-invoice cap
        "current_year"    : int          # Optional – defaults to the real current year
    }

    Returns:
    {
        "status"      : "Approved" | "Rejected",
        "checks"      : { name_match, year_valid, category_valid, amount_within_limit },
        "failures"    : list[str],
        "invoice_data": dict
    }
    """
    failures = []
    checks = {}
    current_year = instructions.get("current_year", datetime.now().year)

    # ── Check 1: Name match ───────────────────────────────────────────────────
    expected_name = (instructions.get("expected_name") or "").strip().lower()
    invoice_name = (invoice_data.get("name") or "").strip().lower()
    name_match = expected_name in invoice_name or invoice_name in expected_name
    checks["name_match"] = name_match
    if not name_match:
        failures.append(
            f"Name mismatch: expected '{instructions.get('expected_name')}', "
            f"found '{invoice_data.get('name')}'"
        )

    # ── Check 2: Invoice date in current year ─────────────────────────────────
    invoice_date_str = invoice_data.get("invoice_date")
    year_valid = False
    if invoice_date_str:
        try:
            invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
            year_valid = invoice_date.year == current_year
            if not year_valid:
                failures.append(
                    f"Invoice year {invoice_date.year} is not the current year ({current_year})"
                )
        except ValueError:
            failures.append(f"Could not parse invoice date: '{invoice_date_str}'")
    else:
        failures.append("Invoice date not found in the document")
    checks["year_valid"] = year_valid

    # ── Check 3: Item categories are valid ────────────────────────────────────
    valid_categories = [c.lower() for c in (instructions.get("valid_categories") or [])]
    items = invoice_data.get("items") or []
    invalid_items = []
    for item in items:
        item_category = (item.get("category") or "").lower()
        if valid_categories:
            matched = any(
                vc in item_category or item_category in vc for vc in valid_categories
            )
            if not matched:
                invalid_items.append(
                    f"'{item.get('description', 'Unknown')}' (category: {item.get('category')})"
                )
    category_valid = len(invalid_items) == 0
    checks["category_valid"] = category_valid
    if not category_valid:
        failures.append(f"Items with invalid categories: {', '.join(invalid_items)}")

    # ── Check 4: Amounts within category limits ───────────────────────────────
    category_limits = instructions.get("category_limits") or {}
    total_amount = float(invoice_data.get("total_amount") or 0)
    amount_within_limit = True

    for item in items:
        item_category = (item.get("category") or "").lower()
        item_amount = float(item.get("amount") or 0)
        for limit_key, limit_value in category_limits.items():
            if limit_key.lower() in ("overall", "total"):
                continue
            if limit_key.lower() in item_category or item_category in limit_key.lower():
                if item_amount > limit_value:
                    amount_within_limit = False
                    failures.append(
                        f"Item '{item.get('description')}' amount {item_amount} exceeds "
                        f"the {limit_key} limit of {limit_value}"
                    )

    overall_limit = category_limits.get("overall") or category_limits.get("total")
    if overall_limit and total_amount > float(overall_limit):
        amount_within_limit = False
        failures.append(
            f"Total invoice amount {total_amount} exceeds the overall limit of {overall_limit}"
        )

    checks["amount_within_limit"] = amount_within_limit

    status = "Approved" if all(checks.values()) else "Rejected"
    return {
        "status": status,
        "checks": checks,
        "failures": failures,
        "invoice_data": invoice_data,
    }


def process_invoice(pdf_path: str, instructions: dict, model: str = "gpt-4o-mini") -> dict:
    """
    Read an invoice PDF, extract all data points using an LLM, then validate
    them against the provided instructions.

    Args:
        pdf_path    : Path to the invoice PDF file.
        instructions: Validation rules with keys:
                        expected_name    (str)       – name that must be on the invoice
                        valid_categories (list[str]) – accepted item categories
                        category_limits  (dict)      – max amount per category;
                                                       use "overall" for a total cap
                        current_year     (int)       – optional, defaults to current year
        model       : OpenAI model to use (default: gpt-4o-mini).

    Returns:
        {
            "status"      : "Approved" or "Rejected",
            "checks"      : dict of individual check results,
            "failures"    : list of failure reasons (empty if Approved),
            "invoice_data": dict of extracted invoice fields
        }
    """
    llm = ChatOpenAI(model=model, temperature=0)

    pdf_text = extract_pdf_text(pdf_path)
    if not pdf_text.strip():
        return {
            "status": "Rejected",
            "checks": {},
            "failures": ["Could not extract text from the PDF"],
            "invoice_data": {},
        }

    invoice_data = extract_invoice_data(pdf_text, llm)
    return validate_invoice(invoice_data, instructions)


# ── Example usage ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_instructions = {
        "expected_name": "John Doe",
        "valid_categories": ["Electronics", "Office Supplies"],
        "category_limits": {
            "Electronics": 5000,
            "Office Supplies": 1000,
            "overall": 6000,
        },
    }

    result = process_invoice("invoice.pdf", sample_instructions)

    print(f"\nStatus : {result['status']}")
    print(f"Checks : {result['checks']}")
    if result["failures"]:
        print("Failures:")
        for f in result["failures"]:
            print(f"  - {f}")
    print(f"\nExtracted invoice data:\n{json.dumps(result['invoice_data'], indent=2)}")
