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
        # Using gpt-4o for better vision capabilities with complex tables
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o")
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "16384"))  # gpt-4o max output tokens
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))  # 0 for maximum consistency
        
        # File processing configuration
        self.supported_formats = [".pdf", ".png", ".jpg", ".jpeg"]
        self.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
        
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

CRITICAL INSTRUCTIONS FOR EXTRACTING ITEMS:
The items table starts after the "ITEM# QTY DESCRIPTION U.P.C. PRICE DISC D.Price DEP EXT" header row.
Each line item has: ITEM#, QTY, DESCRIPTION (with size on next line), U.P.C., PRICE, DISC, D.Price, DEP, EXT, and a BARCODE below it.
The items table ends at the dashed line (----------) before "Cases:", "Bottles:", etc.

YOU MUST:
1. Look at the ENTIRE items table from top to bottom until you see the dashed line
2. Count how many barcodes appear in the items section - this tells you how many items exist
3. Extract EVERY line, including the LAST line right before the dashed line/totals section
4. The LAST ITEM is often a different product and appears right before totals - DO NOT SKIP IT!
5. Verify: number of items in your items array MUST EQUAL number of barcodes

Each item needs: item_number, qty, description, upc, unit_price, discount, discounted_price, deposit, extended_amount, size.

Notes: If you can read barcode(s), include their numbers; else "None"."""

    def _get_breakthru_prompt(self) -> str:
        """Get the prompt for Breakthru Beverage Illinois invoices"""
        return """You are an expert invoice reader for Breakthru Beverage Illinois invoices. Return STRICT JSON only (no code fences or commentary). Use "None" for absent text fields and null for absent numeric fields.

REQUIRED TOP-LEVEL FIELDS:
vendor_name, vendor_address, vendor_phone, invoice_number, customer_number, route, stop, terms, license, exp_date, chain, delivery_number, invoice_date, due_date, po_number, special_instructions, barcode, total_bottles, total_liquor_gallons, total_beer_gallons, gross_total, total_discount, net_amount

CRITICAL: The line items array MUST be named "items" (not "line_items").

TABLE STRUCTURE:
The invoice has a dense table with very small text. Each row has data in specific column positions, followed by a BARCODE underneath (ignore barcodes).

COLUMN HEADERS (in exact order from left to right):
Case | Btles | Item | Size | BPC | Description | (gap with barcode) | CS Price | CS Disc | CS Net | Cnty Tax | City Tax | Ext W/O | SLP | Deal    

CRITICAL READING INSTRUCTIONS:
1. Case: FAR LEFT column - single digit (1-9)
2. Btles: Usually blank (write "None")
3. Item: 7-DIGIT number in the Item column (e.g., 9000322, 9760614) - NOT the barcode below!
4. Size: Look for bottle size like 375ML, 100ML, 750ML, 1L, 1.75L
5. BPC: Small number (6, 12, 24, 48, 120) - bottles per case
6. Description: Product name in caps (e.g., CROWN ROYAL 80, FIREBALL CINNAMON WHISKY)
7. cs_price: First price column (3 digits usually, e.g., 322.25, 115.00)
8. cs_disc: Second price column (discount, e.g., 77.00, 62.20) - can be 0
9. cs_net: Third price column (net price after discount, e.g., 245.25, 52.80)
10. cnty_tax: Usually 0.00
11. city_tax: Usually 0.00
12. ext_w_o_tax: Extended amount (rightmost price, e.g., 981.00, 52.80)
13. slp: 3-4 DIGIT code only (e.g., 644, 470) - NOT 8 digits!
14. deal: 8-digit code at FAR RIGHT (e.g., 80858535, 80820373)

CRITICAL WARNINGS - READ CAREFULLY:
- The BARCODE appears BELOW each row - DO NOT use barcode as Item number!
- Item column contains 7-digit codes like 9000322 (NOT 13-digit barcodes)
- SLP is only 3-4 digits (644, 470) - if you see 8 digits, you're reading the Deal column
- There are THREE separate price columns: cs_price, cs_disc, cs_net - read carefully
- Size values like "375ML" go in Size field, NOT Btles field
- Focus on the row data, ignore barcodes between rows

EXAMPLE ROW (to help you understand):
Case=4, Btles=None, Item=9000322, Size=375ML, BPC=24, Description=CROWN ROYAL 80, cs_price=322.25, cs_disc=77.00, cs_net=245.25, cnty_tax=0.00, city_tax=0.00, ext_w_o_tax=981.00, slp=644, deal=80858535

Extract ALL line items. Return JSON with top-level fields + "items" array. Be precise with numeric values."""
    
    def _get_southern_glazers_prompt(self) -> str:
        """Get the prompt for Southern Glazer's of IL invoices"""
        return """You are an invoice reader for Southern Glazer's of IL invoices. Output ONLY JSON (no extra text). Use "None" when a field is not present. When parsing the table, align values to the visible column headers. For UPC, output digits only (no dashes) and prefer the UPC printed on the same line; do not copy the big page barcode.

Top-level fields to return exactly: vendor_name, remit_to_address, vendor_phone, account_number, invoice_number, route, stop, page, ship_date, due_date, carton, invoice_date, phone_number, pay_this_amount, total_discount, net_amount, customer_name, customer_address. Map labels precisely: 'TOTAL # BTLS:' → total_bottles; 'GROSS TOTAL' → gross_total; 'TOTAL DISCOUNT' → total_discount; 'PAY THIS AMOUNT' → pay_this_amount; 'NET AMOUNT' → net_amount. Use the exact numbers printed; do not compute or guess.

Items: Extract ALL line items from the invoice table, including the very last item. For each visible line, capture: location_code, cases, bottles, size, description, pack, promo_number, upc, product_code, net_bottle_price, unit_price, div_cde, unit_discount, net_amount. Do not skip any items - extract every single row.

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
