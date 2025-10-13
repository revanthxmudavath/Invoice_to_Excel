"""
Main invoice parser module using OpenAI Vision API
"""

import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
from PIL import Image
import io

from config import Config
from openai_client import OpenAIClient
from file_processor import FileProcessor
from validators import InvoiceValidator
from schemas import InvoiceSchema

class InvoiceParser:
    """Main invoice parser class that orchestrates the parsing workflow"""
    
    def __init__(self, config: Config):
        self.config = config
        self.openai_client = OpenAIClient(config)
        self.file_processor = FileProcessor(config)
        self.validator = InvoiceValidator(config)
        self.logger = logging.getLogger(__name__)
    
    def parse_invoice(self, file_path: str, vendor: str) -> Dict[str, Any]:
        """
        Parse an invoice file and return structured JSON data
        
        Args:
            file_path: Path to the invoice file
            vendor: Vendor type (lakeshore, breakthru, southern_glazers)
            
        Returns:
            Dictionary containing the parsed invoice data
        """
        # Validate file and vendor
        self.config.validate_file(file_path)
        if vendor not in ["lakeshore", "breakthru", "southern_glazers"]:
            raise ValueError(f"Unsupported vendor: {vendor}")
        
        self.logger.info(f"Processing {file_path} for vendor {vendor}")
        
        try:
            # Process file into images
            images = self.file_processor.process_file(file_path)
            self.logger.info(f"Processed file into {len(images)} images")
            
            # Get vendor-specific prompt
            prompt = self.config.get_vendor_prompt(vendor)
            
            # Parse with OpenAI Vision
            raw_response = self.openai_client.parse_invoice(images, prompt)
            
            # Parse JSON response
            parsed_data = self._parse_json_response(raw_response)
            
            # Add metadata
            parsed_data["meta"] = {
                "source_file": file_path,
                "vendor_detected": vendor,
                "parse_confidence": 0.95,  # Placeholder
                "validation_flags": []
            }
            
            # Validate against schema
            validated_data = self.validator.validate_invoice(parsed_data, vendor)

            # Add validation flags to metadata
            if self.validator.validation_flags:
                validated_data["meta"]["validation_flags"] = self.validator.validation_flags

            # Check if items count matches barcode count (for invoices with barcodes)
            items_count = len(validated_data.get('items', []))
            barcodes = validated_data.get('barcode', [])
            if isinstance(barcodes, list) and len(barcodes) > 0:
                barcode_count = len(barcodes)
                if items_count < barcode_count:
                    warning_msg = f"WARNING: Found {barcode_count} barcodes but only {items_count} items extracted. Possible missing items!"
                    self.logger.warning(warning_msg)
                    if "validation_flags" not in validated_data["meta"]:
                        validated_data["meta"]["validation_flags"] = []
                    validated_data["meta"]["validation_flags"].append(warning_msg)

            self.logger.info(f"Successfully parsed invoice with {len(validated_data.get('items', []))} items")

            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error parsing invoice: {e}")
            raise
    
    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse the raw JSON response from OpenAI"""
        try:
            # Save original for comparison
            original_response = raw_response

            # Clean the response - remove any markdown formatting
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            cleaned_response = cleaned_response.strip()

            self.logger.debug(f"After markdown cleanup: {len(cleaned_response)} chars")

            # First, try to parse the JSON as-is without any "fixing"
            try:
                parsed = json.loads(cleaned_response)
                self.logger.info("JSON is already valid, no fixing needed")
                return parsed
            except json.JSONDecodeError as e:
                # JSON is invalid, try to fix it
                self.logger.warning(f"JSON is invalid (error: {e}), attempting to fix...")

                before_fix = cleaned_response

                # Try to fix common JSON issues
                cleaned_response = self._fix_json_response(cleaned_response)

                # Log the fix attempt
                self.logger.info(f"Attempted fix: {len(before_fix)} chars -> {len(cleaned_response)} chars")

                # Save both versions for comparison
                try:
                    with open('json_before_fix.txt', 'w', encoding='utf-8') as f:
                        f.write(before_fix)
                    with open('json_after_fix.txt', 'w', encoding='utf-8') as f:
                        f.write(cleaned_response)
                    self.logger.info("Saved before/after fix files for comparison")
                except:
                    pass

                # Parse the fixed JSON
                parsed = json.loads(cleaned_response)

            # Ensure we have the basic structure
            if not isinstance(parsed, dict):
                raise ValueError("Response is not a valid JSON object")

            return parsed
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.error(f"Raw content: {raw_response[:1000]}...")
            raise ValueError(f"Invalid JSON response from OpenAI: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error parsing response: {e}")
            raise
    
    def _fix_json_response(self, response: str) -> str:
        """Attempt to fix common JSON response issues"""
        # If response is truncated, try to close it properly
        if response.count('{') > response.count('}'):
            # Add missing closing braces
            missing_braces = response.count('{') - response.count('}')
            response += '}' * missing_braces
        
        # Handle truncated strings (common with long barcodes)
        if '"' in response:
            # Find the last complete field
            last_comma = response.rfind(',')
            if last_comma > 0:
                # Check if the last field is incomplete
                after_comma = response[last_comma + 1:].strip()
                if after_comma.startswith('"') and not after_comma.endswith('"'):
                    # This field is incomplete, try to close it
                    if ':' in after_comma:
                        # It's a key-value pair, close the value
                        response = response[:last_comma + 1] + after_comma.split(':')[0] + ': null'
                    else:
                        # It's just a value, close it
                        response = response[:last_comma + 1] + 'null'
        
        # Handle truncated items array specifically
        if '"items": [' in response:
            items_start = response.find('"items": [')
            if items_start > 0:
                items_content = response[items_start + 10:]  # Skip '"items": ['

                # Only try to fix if the array is truly incomplete (no closing bracket)
                # Check if there's a valid closing bracket for the items array
                bracket_count = 1  # We already opened with '['
                array_end = -1

                for i, char in enumerate(items_content):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            # Found the closing bracket for items array
                            array_end = i
                            break

                # If array_end is -1, the array is incomplete
                if array_end == -1:
                    # Array is incomplete - find the last complete item
                    # Look for '}, {' or '}]' patterns (the last item won't have comma)
                    last_complete_item = items_content.rfind('},')

                    if last_complete_item > 0:
                        # Found at least one complete item with comma, keep all up to and including it
                        response = response[:items_start + 10 + last_complete_item + 1] + ']'
                    else:
                        # No comma found, check if there's at least one complete item
                        last_brace = items_content.rfind('}')
                        if last_brace > 0:
                            # Check if this looks like a complete object
                            # by counting braces before it
                            before_brace = items_content[:last_brace + 1]
                            if before_brace.count('{') == before_brace.count('}'):
                                # This is a complete item, keep it
                                response = response[:items_start + 10 + last_brace + 1] + ']'
                            else:
                                # Incomplete, close the array empty
                                response = response[:items_start + 10] + '[]'
                        else:
                            # No complete items found, make it an empty array
                            response = response[:items_start + 10] + '[]'
                # else: Array is complete, don't modify it
        
        # If response ends with an incomplete array, close it
        if response.count('[') > response.count(']'):
            missing_brackets = response.count('[') - response.count(']')
            response += ']' * missing_brackets
        
        # Ensure the response ends properly
        if not response.endswith('}'):
            response = response.rstrip(',') + '}'
        
        return response
    
    def batch_parse(self, file_paths: List[str], vendor: str) -> List[Dict[str, Any]]:
        """Parse multiple invoice files"""
        results = []
        
        for file_path in file_paths:
            try:
                result = self.parse_invoice(file_path, vendor)
                results.append(result)
                self.logger.info(f"Successfully parsed {file_path}")
            except Exception as e:
                self.logger.error(f"Failed to parse {file_path}: {e}")
                # Continue with other files
                continue
        
        return results
    
    def get_parsing_stats(self) -> Dict[str, Any]:
        """Get parsing statistics"""
        # This would track statistics over time
        return {
            "total_processed": 0,
            "successful_parses": 0,
            "failed_parses": 0,
            "average_confidence": 0.0
        }
