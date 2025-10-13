"""
OpenAI client for invoice parsing using Vision API
"""

import base64
import logging
from typing import List, Dict, Any
from openai import OpenAI
from PIL import Image
import io

from config import Config

class OpenAIClient:
    """Client for OpenAI Vision API"""
    
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.logger = logging.getLogger(__name__)
    
    def parse_invoice(self, images: List[Image.Image], prompt: str) -> str:
        """
        Parse invoice images using OpenAI Vision API
        
        Args:
            images: List of PIL Image objects
            prompt: Vendor-specific prompt for parsing
            
        Returns:
            Raw response from OpenAI
        """
        try:
            # Convert images to base64
            image_contents = []
            for img in images:
                # Convert PIL image to base64
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}"
                    }
                })
            
            # Prepare the message
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ] + image_contents
                }
            ]
            
            self.logger.info(f"Sending request to OpenAI with {len(images)} images")
            
            # Make the API call (OpenAI Python SDK v1.x)
            response = self.client.chat.completions.create(
                model=self.config.model_name,
                messages=messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            # Extract the response content
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                self.logger.info("Successfully received response from OpenAI")

                # Log response details for debugging
                self.logger.debug(f"Response length: {len(content)} characters")
                self.logger.debug(f"Response finish_reason: {response.choices[0].finish_reason}")

                # Save raw response to file for inspection
                try:
                    with open('raw_openai_response.txt', 'w', encoding='utf-8') as f:
                        f.write("="*80 + "\n")
                        f.write("RAW OPENAI RESPONSE\n")
                        f.write("="*80 + "\n")
                        f.write(f"Length: {len(content)} characters\n")
                        f.write(f"Finish Reason: {response.choices[0].finish_reason}\n")
                        f.write("="*80 + "\n")
                        f.write(content)
                        f.write("\n" + "="*80 + "\n")
                    self.logger.info("Raw response saved to raw_openai_response.txt")
                except Exception as e:
                    self.logger.warning(f"Could not save raw response: {e}")

                return content
            else:
                raise ValueError("No response content received from OpenAI")
                
        except Exception as e:
            self.logger.error(f"Error parsing invoice with OpenAI Vision: {e}")
            raise
    
    def validate_response(self, response: str) -> bool:
        """Basic validation of the OpenAI response"""
        if not response or not response.strip():
            return False
        
        # Check if response looks like JSON
        response = response.strip()
        if response.startswith('{') and response.endswith('}'):
            return True
        
        # Check if response is wrapped in markdown
        if response.startswith('```') and response.endswith('```'):
            return True
        
        return False
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        # This would track token usage and costs
        return {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "estimated_cost": 0.0
        }
