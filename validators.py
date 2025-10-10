"""
Validation module for invoice data
"""

import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP

from config import Config

class InvoiceValidator:
    """Validates parsed invoice data against schemas and business rules"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.validation_flags = []
    
    def validate_invoice(self, data: Dict[str, Any], vendor: str) -> Dict[str, Any]:
        """
        Validate invoice data and return validated data with flags
        
        Args:
            data: Parsed invoice data
            vendor: Vendor type for validation rules
            
        Returns:
            Validated data with any corrections applied
        """
        self.validation_flags = []
        
        try:
            # Basic structure validation
            self._validate_basic_structure(data)
            
            # Vendor-specific validation
            if vendor == "lakeshore":
                self._validate_lakeshore(data)
            elif vendor == "breakthru":
                self._validate_breakthru(data)
            elif vendor == "southern_glazers":
                self._validate_southern_glazers(data)
            
            # Business rule validation
            self._validate_business_rules(data)
            
            # Data type validation and conversion
            validated_data = self._validate_data_types(data)
            
            self.logger.info(f"Validation complete. Flags: {self.validation_flags}")
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Validation error: {e}")
            self.validation_flags.append(f"validation_error: {str(e)}")
            raise
    
    def _validate_basic_structure(self, data: Dict[str, Any]):
        """Validate basic data structure"""
        required_sections = ["vendor", "invoice", "account", "items"]
        
        for section in required_sections:
            if section not in data:
                self.validation_flags.append(f"missing_section: {section}")
                data[section] = {}
        
        # Ensure items is a list
        if not isinstance(data.get("items"), list):
            self.validation_flags.append("items_not_list")
            data["items"] = []
    
    def _validate_lakeshore(self, data: Dict[str, Any]):
        """Validate Lakeshore Beverage specific data"""
        required_fields = [
            "vendor_name", "invoice_number", "invoice_date"
        ]
        
        for field in required_fields:
            if not data.get(field):
                self.validation_flags.append(f"missing_required_field: {field}")
    
    def _validate_breakthru(self, data: Dict[str, Any]):
        """Validate Breakthru Beverage specific data"""
        required_fields = [
            "vendor_name", "invoice_number", "customer_number"
        ]
        
        for field in required_fields:
            if not data.get(field):
                self.validation_flags.append(f"missing_required_field: {field}")
    
    def _validate_southern_glazers(self, data: Dict[str, Any]):
        """Validate Southern Glazer's specific data"""
        required_fields = [
            "vendor_name", "invoice_number", "account_number"
        ]
        
        for field in required_fields:
            if not data.get(field):
                self.validation_flags.append(f"missing_required_field: {field}")
    
    def _validate_business_rules(self, data: Dict[str, Any]):
        """Validate business logic rules"""
        items = data.get("items", [])
        
        if items:
            # Check for UPC format
            for i, item in enumerate(items):
                upc = item.get("upc")
                if upc and not self._is_valid_upc(upc):
                    self.validation_flags.append(f"invalid_upc_format: item_{i}")
                
                # Check for negative quantities
                qty = item.get("qty") or item.get("bottles") or item.get("cases")
                if qty is not None and qty != "None":
                    try:
                        # Convert to float for comparison, skip if conversion fails
                        qty_num = float(qty)
                        if qty_num < 0:
                            self.validation_flags.append(f"negative_quantity: item_{i}")
                    except (ValueError, TypeError):
                        # Skip validation for non-numeric values
                        continue
            
            # Validate totals if present
            self._validate_totals(data)
    
    def _validate_totals(self, data: Dict[str, Any]):
        """Validate invoice totals against item calculations"""
        items = data.get("items", [])
        if not items:
            return
        
        # Calculate total from items
        calculated_total = 0
        for item in items:
            extended_amount = item.get("extended_amount") or item.get("net_amount")
            if extended_amount is not None and extended_amount != "None":
                try:
                    calculated_total += float(extended_amount)
                except (ValueError, TypeError):
                    continue
        
        # Compare with invoice total
        invoice_total = data.get("total_sales") or data.get("gross_total")
        if invoice_total is not None and invoice_total != "None":
            try:
                tolerance = 0.01  # $0.01 tolerance for rounding differences
                if abs(calculated_total - float(invoice_total)) > tolerance:
                    self.validation_flags.append("totals_mismatch")
            except (ValueError, TypeError):
                self.validation_flags.append("invalid_invoice_total")
    
    def _validate_data_types(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and convert data types"""
        validated_data = data.copy()
        
        # Convert numeric fields
        numeric_fields = [
            "total_sales", "total_discount", "gross_total", "net_amount",
            "pay_this_amount", "total_bottles", "total_liquor_gallons",
            "total_beer_gallons"
        ]
        
        for field in numeric_fields:
            if field in validated_data and validated_data[field] is not None and validated_data[field] != "None":
                try:
                    validated_data[field] = float(validated_data[field])
                except (ValueError, TypeError):
                    self.validation_flags.append(f"invalid_numeric_field: {field}")
                    validated_data[field] = None
        
        # Validate and convert item fields
        items = validated_data.get("items", [])
        for item in items:
            # Convert UPC to digits only
            if "upc" in item and item["upc"]:
                item["upc"] = self._clean_upc(item["upc"])
            
            # Convert numeric item fields
            numeric_item_fields = [
                "qty", "bottles", "cases", "unit_price", "discount",
                "extended_amount", "net_amount", "deposit"
            ]
            
            for field in numeric_item_fields:
                if field in item and item[field] is not None and item[field] != "None":
                    try:
                        item[field] = float(item[field])
                    except (ValueError, TypeError):
                        item[field] = None
        
        return validated_data
    
    def _is_valid_upc(self, upc: str) -> bool:
        """Validate UPC format"""
        if not upc:
            return False
        
        # Remove non-digits
        digits = ''.join(filter(str.isdigit, str(upc)))
        
        # Check length (UPC-A is 12 digits, UPC-E is 8 digits)
        if len(digits) not in [8, 12]:
            return False
        
        return True
    
    def _clean_upc(self, upc: str) -> str:
        """Clean UPC to digits only"""
        if not upc:
            return ""
        
        # Extract only digits
        digits = ''.join(filter(str.isdigit, str(upc)))
        return digits
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation results"""
        return {
            "total_flags": len(self.validation_flags),
            "flags": self.validation_flags,
            "is_valid": len(self.validation_flags) == 0
        }
