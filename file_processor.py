"""
File processing module for handling different invoice file formats
"""

import logging
from pathlib import Path
from typing import List
from PIL import Image
import fitz  # PyMuPDF
import io

from config import Config

class FileProcessor:
    """Handles file processing and conversion to images"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def process_file(self, file_path: str) -> List[Image.Image]:
        """
        Process a file and convert it to a list of PIL Image objects
        
        Args:
            file_path: Path to the file to process
            
        Returns:
            List of PIL Image objects
        """
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()
        
        if suffix == '.pdf':
            return self._process_pdf(file_path)
        elif suffix in ['.png', '.jpg', '.jpeg']:
            return self._process_image(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    def _process_pdf(self, pdf_path: Path) -> List[Image.Image]:
        """Convert PDF to images"""
        try:
            self.logger.info(f"Loading PDF: {pdf_path}")
            doc = fitz.open(pdf_path)
            
            images = []
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Render page to image with high resolution
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Convert to PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))
                
                images.append(img)
                self.logger.debug(f"Converted page {page_num + 1} to image")
            
            doc.close()
            self.logger.info(f"Successfully converted PDF to {len(images)} images")
            return images
            
        except Exception as e:
            self.logger.error(f"Error processing PDF {pdf_path}: {e}")
            raise
    
    def _process_image(self, image_path: Path) -> List[Image.Image]:
        """Load image file"""
        try:
            self.logger.info(f"Loading image: {image_path}")
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            self.logger.info(f"Successfully loaded image: {image_path}")
            return [img]
            
        except Exception as e:
            self.logger.error(f"Error loading image {image_path}: {e}")
            raise
    
    def validate_image_quality(self, image: Image.Image) -> bool:
        """Validate that image quality is sufficient for OCR"""
        # Check minimum dimensions
        if image.width < 800 or image.height < 600:
            self.logger.warning(f"Image dimensions ({image.width}x{image.height}) may be too small")
            return False
        
        # Check file size (rough estimate)
        img_buffer = io.BytesIO()
        image.save(img_buffer, format='PNG')
        size_kb = len(img_buffer.getvalue()) / 1024
        
        if size_kb < 50:  # Less than 50KB might be too compressed
            self.logger.warning(f"Image size ({size_kb:.1f}KB) may be too small")
            return False
        
        return True
    
    def optimize_image(self, image: Image.Image) -> Image.Image:
        """Optimize image for better OCR results"""
        # Convert to RGB if not already
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize if too large (keep aspect ratio)
        max_dimension = 2048
        if image.width > max_dimension or image.height > max_dimension:
            ratio = min(max_dimension / image.width, max_dimension / image.height)
            new_width = int(image.width * ratio)
            new_height = int(image.height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.logger.info(f"Resized image to {new_width}x{new_height}")
        
        return image
