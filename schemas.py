"""
Data schemas for invoice parsing
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime

class InvoiceSchema:
    """Base schema class for invoice data"""
    
    @staticmethod
    def get_unified_schema() -> Dict[str, Any]:
        """Get the unified schema that covers all vendors"""
        return {
            "vendor": {
                "vendor_name": "string|null",
                "vendor_address": "string|null",
                "vendor_phone": "string|null",
                "remit_to_address": "string|null"
            },
            "invoice": {
                "invoice_number": "string|null",
                "invoice_date": "string|null",
                "invoice_datetime": "string|null",
                "po_number": "string|null",
                "terms": "string|null",
                "license": "string|null",
                "exp_date": "string|null",
                "route": "string|null",
                "stop": "string|null",
                "page": "string|null",
                "load": "string|null",
                "driver": "string|null",
                "sales_rep": "string|null",
                "chain": "string|null",
                "delivery_number": "string|null",
                "due_date": "string|null",
                "special_instructions": "string|null",
                "carton": "string|null",
                "pay_this_amount": "number|null",
                "gross_total": "number|null",
                "total_discount": "number|null",
                "net_amount": "number|null",
                "barcode": "string|null"
            },
            "account": {
                "account_number": "string|null",
                "account_info": "string|null",
                "customer_number": "string|null",
                "customer_name": "string|null",
                "customer_address": "string|null",
                "phone_number": "string|null"
            },
            "items": [
                {
                    "item_number": "string|null",
                    "description": "string|null",
                    "size": "string|null",
                    "qty": "number|null",
                    "cases": "number|null",
                    "bottles": "number|null",
                    "upc": "string|null",
                    "product_code": "string|null",
                    "unit_price": "number|null",
                    "discount": "number|null",
                    "discounted_price": "number|null",
                    "deposit": "number|null",
                    "extended_amount": "number|null",
                    "net_bottle_price": "number|null",
                    "cs_price": "number|null",
                    "cs_disc": "number|null",
                    "cs_net": "number|null",
                    "cnty_tax": "number|null",
                    "city_tax": "number|null",
                    "ext_w_o_tax": "number|null",
                    "slp": "string|null",
                    "deal": "string|null",
                    "promo_number": "string|null",
                    "div_cde": "string|null",
                    "unit_discount": "number|null",
                    "net_amount": "number|null",
                    "bpc": "string|null",
                    "barcode": "string|null"
                }
            ],
            "summary": {
                "cases": "number|null",
                "bottles": "number|null",
                "kegs": "number|null",
                "misc": "number|null",
                "credits": "number|null",
                "total_sales": "number|null",
                "total_discount": "number|null",
                "total_bottles": "number|null",
                "total_liquor_gallons": "number|null",
                "total_beer_gallons": "number|null",
                "liquor_gallons": "number|null",
                "beer_gallons": "number|null",
                "wine_14_percent": "number|null",
                "previous_period_sales": "number|null",
                "order_totals": {
                    "cases_page_total": "number|null",
                    "cases_order_total": "number|null",
                    "bottles_page_total": "number|null",
                    "bottles_order_total": "number|null"
                }
            },
            "meta": {
                "source_file": "string",
                "parse_confidence": "number",
                "validation_flags": ["string"],
                "vendor_detected": "string|null"
            }
        }
    
    @staticmethod
    def get_lakeshore_schema() -> Dict[str, Any]:
        """Get Lakeshore Beverage specific schema"""
        return {
            "vendor_name": "string",
            "vendor_address": "string",
            "vendor_phone": "string",
            "invoice_datetime": "string",
            "account_number": "string",
            "account_info": "string",
            "invoice_number": "string",
            "po_number": "string|null",
            "license": "string|null",
            "load": "string|null",
            "terms": "string|null",
            "driver": "string|null",
            "sales_rep": "string|null",
            "invoice_date": "string",
            "cases": "number|null",
            "bottles": "number|null",
            "kegs": "number|null",
            "misc": "number|null",
            "credits": "number|null",
            "total_sales": "number|null",
            "total_discount": "number|null",
            "barcode": "string|null",
            "items": [
                {
                    "item_number": "string|null",
                    "qty": "number|null",
                    "description": "string",
                    "upc": "string|null",
                    "unit_price": "number|null",
                    "discount": "number|null",
                    "discounted_price": "number|null",
                    "deposit": "number|null",
                    "extended_amount": "number|null",
                    "size": "string|null"
                }
            ]
        }
    
    @staticmethod
    def get_breakthru_schema() -> Dict[str, Any]:
        """Get Breakthru Beverage Illinois specific schema

        Note: Item should contain product codes (numbers like 9000322)
              Description should contain product names (text)
              Size should contain bottle sizes (375ML, 750ML, etc.)
              BPC should contain bottles per case (24, 48, 12)
              ext_w_o_tax is the underscore version of ext_w/o_tax
        """
        return {
            "vendor_name": "string",
            "vendor_address": "string",
            "vendor_phone": "string",
            "invoice_number": "string",
            "customer_number": "string",
            "route": "string|null",
            "stop": "string|null",  # Changed from number to string for consistency
            "terms": "string|null",
            "license": "string|null",
            "exp_date": "string|null",
            "chain": "string|null",
            "delivery_number": "string|null",
            "invoice_date": "string",
            "due_date": "string|null",
            "po_number": "string|null",
            "special_instructions": "string|null",
            "total_bottles": "number|null",
            "total_liquor_gallons": "number|null",
            "total_beer_gallons": "number|null",
            "gross_total": "number|null",
            "total_discount": "number|null",
            "net_amount": "number|null",
            "items": [
                {
                    "Case": "number|null",
                    "Btles": "string|null",  # Usually "None", only populated if specified
                    "Item": "string|null",    # Product code (e.g., "9000322")
                    "Size": "string|null",    # Bottle size (e.g., "375ML", "750ML", "1L")
                    "BPC": "string|null",     # Bottles per case (e.g., "24", "48", "12")
                    "Description": "string",  # Product name (e.g., "CROWN ROYAL 80")
                    "cs_price": "number|null",
                    "cs_disc": "number|null",
                    "cs_net": "number|null",
                    "cnty_tax": "number|null",
                    "city_tax": "number|null",
                    "ext_w_o_tax": "number|null",  # Changed from ext_w/o_tax to match prompt
                    "slp": "string|null",
                    "deal": "string|null"
                }
            ]
        }
    
    @staticmethod
    def get_southern_glazers_schema() -> Dict[str, Any]:
        """Get Southern Glazer's of IL specific schema"""
        return {
            "vendor_name": "string",
            "remit_to_address": "string",
            "vendor_phone": "string",
            "account_number": "string",
            "invoice_number": "string",
            "route": "string|null",
            "stop": "string|null",
            "page": "string|null",
            "ship_date": "string|null",
            "due_date": "string|null",
            "carton": "string|null",
            "invoice_date": "string",
            "phone_number": "string|null",
            "pay_this_amount": "number|null",
            "total_discount": "number|null",
            "gross_total": "number|null",
            "net_amount": "number|null",
            "customer_name": "string|null",
            "customer_address": "string|null",
            "total_bottles": "number|null",
            "cases_page_total": "number|null",
            "cases_order_total": "number|null",
            "bottles_page_total": "number|null",
            "bottles_order_total": "number|null",
            "liquor_gallons": "number|null",
            "beer_gallons": "number|null",
            "wine_14%": "number|null",
            "previous_period_sales": "number|null",
            "items": [
                {
                    "location_code": "string|null",
                    "cases": "number|null",
                    "bottles": "number|null",
                    "size": "string|null",
                    "description": "string",
                    "promo_number": "string|null",
                    "upc": "string|null",
                    "product_code": "string|null",
                    "net_bottle_price": "number|null",
                    "unit_price": "number|null",
                    "div_cde": "string|null",
                    "unit_discount": "number|null",
                    "net_amount": "number|null"
                }
            ]
        }

@dataclass
class InvoiceData:
    """Data class for structured invoice data"""
    vendor_name: str
    invoice_number: str
    invoice_date: str
    items: List[Dict[str, Any]]
    total_amount: Optional[float] = None
    vendor_address: Optional[str] = None
    vendor_phone: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "vendor_name": self.vendor_name,
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "items": self.items,
            "total_amount": self.total_amount,
            "vendor_address": self.vendor_address,
            "vendor_phone": self.vendor_phone
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvoiceData':
        """Create from dictionary format"""
        return cls(
            vendor_name=data.get("vendor_name", ""),
            invoice_number=data.get("invoice_number", ""),
            invoice_date=data.get("invoice_date", ""),
            items=data.get("items", []),
            total_amount=data.get("total_amount"),
            vendor_address=data.get("vendor_address"),
            vendor_phone=data.get("vendor_phone")
        )
