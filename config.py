"""
Configuration management for the invoice parsing application
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

class Config:
    """Configuration class for the invoice parsing application"""
    
    def __init__(self, api_key: Optional[str] = None):
        # Load environment variables from .env file
        load_dotenv()
        
        # OpenAI configuration
        self.openai_api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable "
                "or pass --api-key argument"
            )
        
        # Model configuration
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "16000"))
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
        
        # File processing configuration
        self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg"]
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        
        # Output configuration
        self.output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        self.output_dir.mkdir(exist_ok=True)
        
        # Validation configuration
        self.confidence_threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
        self.currency_precision = int(os.getenv("CURRENCY_PRECISION", "2"))
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "invoice_parser.log")
        
        # Vendor-specific prompts
        self.vendor_prompts = {
            "lakeshore": self._get_lakeshore_prompt(),
            "breakthru": self._get_breakthru_prompt(),
            "southern_glazers": self._get_southern_glazers_prompt()
        }
    
    def _get_lakeshore_prompt(self) -> str:
        """Get the prompt for Lakeshore Beverage invoices"""
        return """You are an invoice reader for Lakeshore Beverage invoices. Read the uploaded image(s) and extract all relevant data. Return strictly JSON (no backticks or commentary). If not found, use "None".

Required top-level fields: vendor_name, vendor_address, vendor_phone, invoice_datetime, account_number, account_info, invoice_number, po_number, license, load, terms, driver, sales_rep, invoice_date, cases, bottles, kegs, misc, credits, total_sales, total_discount, barcode.

Items array: each with item_number, qty, description, upc, unit_price, discount, discounted_price, deposit, extended_amount, size.

Notes: If you can read barcode(s), include their numbers; else "None"."""

    def _get_breakthru_prompt(self) -> str:
        """Get the prompt for Breakthru Beverage Illinois invoices"""
        return """You are an invoice reader for Breakthru Beverage Illinois invoices. Return STRICT JSON only (no code fences or commentary). If a field is absent, use "None". Keep responses concise and prioritize essential data.

Required fields: vendor_name, vendor_address, vendor_phone, invoice_number, customer_number, route, stop, terms, license, exp_date, chain, delivery_number, invoice_date, due_date, po_number, special_instructions, barcode, total_bottles, total_liquor_gallons, total_beer_gallons, gross_total, total_discount, net_amount.

Items array: Extract ONLY the first 10 visible table rows with Case, Btles, Item, Size, BPC, Description, cs_price, cs_disc, cs_net, cnty_tax, city_tax, ext_w/o_tax, slp, deal. Use "None" for empty values. For barcode, use only the first 20 characters if it's very long. DO NOT try to extract all items - limit to first 10 rows maximum."""

    def _get_southern_glazers_prompt(self) -> str:
        """Get the prompt for Southern Glazer's of IL invoices"""
        return """You are an invoice reader for Southern Glazer's of IL invoices. Output ONLY JSON (no extra text). Use "None" when a field is not present. When parsing the table, align values to the visible column headers. For UPC, output digits only (no dashes) and prefer the UPC printed on the same line; do not copy the big page barcode.

Top-level fields to return exactly: vendor_name, remit_to_address, vendor_phone, account_number, invoice_number, route, stop, page, ship_date, due_date, carton, invoice_date, phone_number, pay_this_amount, total_discount, net_amount, customer_name, customer_address. Map labels precisely: 'TOTAL # BTLS:' → total_bottles; 'GROSS TOTAL' → gross_total; 'TOTAL DISCOUNT' → total_discount; 'PAY THIS AMOUNT' → pay_this_amount; 'NET AMOUNT' → net_amount. Use the exact numbers printed; do not compute or guess.

Items: For each visible line, capture: location_code, cases, bottles, size, description, pack, promo_number, upc, product_code, net_bottle_price, unit_price, div_cde, unit_discount, net_amount.

Totals at bottom: cases_page_total, cases_order_total, bottles_page_total, bottles_order_total, liquor_gallons, beer_gallons, wine_14%, gross_total, total_bottles, previous_period_sales. Also capture any delivery charges as separate item lines. If any value is empty, include it as "None"."""

    def get_vendor_prompt(self, vendor: str) -> str:
        """Get the prompt for a specific vendor"""
        if vendor not in self.vendor_prompts:
            raise ValueError(f"Unsupported vendor: {vendor}")
        return self.vendor_prompts[vendor]
    
    def validate_file(self, file_path: str) -> bool:
        """Validate that the file is supported and within size limits"""
        path = Path(file_path)
        
        # Check file exists
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check file format
        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(
                f"Unsupported file format: {path.suffix}. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )
        
        # Check file size
        file_size_mb = path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(
                f"File too large: {file_size_mb:.1f}MB. "
                f"Maximum allowed: {self.max_file_size_mb}MB"
            )
        
        return True
