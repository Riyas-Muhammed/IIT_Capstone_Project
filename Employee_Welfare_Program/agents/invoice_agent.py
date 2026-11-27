import sys
import json
from pathlib import Path
from datetime import datetime
from pypdf import PdfReader
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

config_path = Path(__file__).parent.parent / "config" / "config.json"
with open(config_path, "r") as f:
    config = json.load(f)

sys.path.insert(0, str(Path.cwd()))
from prompts.prompts import data_system_prompt, val_system_prompt
try:
    from modules.llm import get_llm
except ImportError:
    from modules.llm import get_llm



def extract_pdf_text(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def get_invoice_data(data: str) -> dict:
    """"
    Extract the following data points from the invoice text and return them as JSON:
    """
    provider = config["provider"]
    client = get_llm(provider)
    
    prompt_template = PromptTemplate(
        input_variables=["text"],
        template=data_system_prompt
    )
    prompt = prompt_template.format(text=data)
    response = client.invoke(prompt)
    print(f"Invoice data: {response.content}")
    return response.content

def validate_invoice(invoice_data: dict) -> dict:
    """
    Validate the invoice and approve/reject the reimbursment
    """
    provider = config["provider"]
    client = get_llm(provider)
    year = datetime.now().isoformat()[:4]
    items = []

    prompt_template = PromptTemplate(
        input_variables=["employee", "year", "items", "balance" "data"],
        template=val_system_prompt
    )
    prompt = prompt_template.format(employee=config["employee"], year=year, items=items, balance=config["points_available"], data=invoice_data)
    response = client.invoke(prompt)
    print(f"Invoice data: {response.content}")
    return response.content

def process_invoice(pdf_path: str = None) -> dict:
    """
    Read the invoice and acture all the data. Validate the invoice and approve/reject 
    """
    path = "C:/Users/MHPB/OneDrive - Novo Nordisk/Desktop/FitPro_Gym_Sample_Invoice_Riyas.pdf"
    invoice_text = extract_pdf_text(path)
    invoice_data = get_invoice_data(invoice_text)
    status = validate_invoice(invoice_data)

    # Formating the json response
    json_start = status.find("{")
    json_end = status.rfind("}") + 1
    json_string = status[json_start:json_end]
    output = json.loads(json_string)
    return output


if __name__ == "__main__":
    process_invoice()
    