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
            
            self.logger.info(f"Successfully parsed invoice with {len(validated_data.get('items', []))} items")
            
            return validated_data
            
        except Exception as e:
            self.logger.error(f"Error parsing invoice: {e}")
            raise
    
    def _parse_json_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse the raw JSON response from OpenAI"""
        try:
            # Clean the response - remove any markdown formatting
            cleaned_response = raw_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            
            # Try to fix common JSON issues
            cleaned_response = self._fix_json_response(cleaned_response)
            
            # Parse JSON
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
        
        # Handle truncated items array specifically - more aggressive approach
        if '"items": [' in response:
            items_start = response.find('"items": [')
            if items_start > 0:
                # Look for incomplete items
                items_content = response[items_start + 10:]  # Skip '"items": ['
                
                # Find the last complete item
                last_complete_item = items_content.rfind('},')
                if last_complete_item > 0:
                    # Cut off at the last complete item and close properly
                    response = response[:items_start + 10 + last_complete_item + 1] + ']'
                elif items_content.count('[') > items_content.count(']'):
                    # Just close the array if it's incomplete
                    response = response.rstrip(',') + ']'
        
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
