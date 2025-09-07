#!/usr/bin/env python3
"""
Enhanced Document Ingestion for Phase B

Features:
- HEIC/HEIF support via pillow_heif
- Multiple format support
- Image preprocessing integration
- Error handling and logging
"""

import os
import logging
from typing import Optional, Tuple, Dict, Any
import numpy as np
from PIL import Image
import io

# Import image operations
from .image_ops import convert_heic_to_rgb, preprocess_for_ocr, get_image_info

logger = logging.getLogger(__name__)

class DocumentIngester:
    """Enhanced document ingester with HEIC support"""
    
    def __init__(self):
        self.supported_formats = {
            '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf', '.heic', '.heif'
        }
        
        # Try to register HEIC support
        self.heic_supported = self._register_heic_support()
    
    def _register_heic_support(self) -> bool:
        """Register HEIC support if pillow_heif is available"""
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            logger.info("✅ HEIC support registered via pillow_heif")
            return True
        except ImportError:
            logger.warning("⚠️ pillow_heif not available - HEIC support disabled")
            return False
    
    def ingest_document(self, file_path: str, preprocess: bool = True) -> Dict[str, Any]:
        """
        Ingest document from file path
        
        Args:
            file_path: Path to document file
            preprocess: Whether to apply preprocessing
            
        Returns:
            Dictionary with image data and metadata
        """
        logger.info(f"🔄 Ingesting document: {file_path}")
        
        try:
            # Check file format
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            # Handle HEIC files
            if file_ext in ['.heic', '.heif']:
                if not self.heic_supported:
                    # Return quarantine result for HEIC without support
                    return {
                        'success': False,
                        'file_path': file_path,
                        'format': 'heic',
                        'error': 'HEIC_NOT_SUPPORTED',
                        'policy_action': 'QUARANTINE',
                        'reasons': ['HEIC_NOT_SUPPORTED'],
                        'heic_supported': False,
                        'message': 'Install HEIC support to auto-process iPhone photos.'
                    }
                return self._ingest_heic(file_path, preprocess)
            
            # Handle other image formats
            elif file_ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']:
                return self._ingest_image(file_path, preprocess)
            
            # Handle PDF files
            elif file_ext == '.pdf':
                return self._ingest_pdf(file_path, preprocess)
            
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
        except Exception as e:
            logger.error(f"❌ Document ingestion failed: {e}")
            raise
    
    def _ingest_heic(self, file_path: str, preprocess: bool) -> Dict[str, Any]:
        """Ingest HEIC file"""
        logger.info(f"📸 Ingesting HEIC file: {file_path}")
        
        try:
            # Read HEIC data
            with open(file_path, 'rb') as f:
                heic_data = f.read()
            
            # Convert to RGB
            rgb_array = convert_heic_to_rgb(heic_data)
            
            # Get image info
            image_info = get_image_info(rgb_array)
            
            # Preprocess if requested
            if preprocess:
                processed_image, steps = preprocess_for_ocr(rgb_array, profile="auto")
                image_info['preprocessing_steps'] = steps
            else:
                processed_image = rgb_array
                image_info['preprocessing_steps'] = []
            
            return {
                'success': True,
                'file_path': file_path,
                'format': 'heic',
                'original_image': rgb_array,
                'processed_image': processed_image,
                'image_info': image_info,
                'heic_supported': True
            }
            
        except Exception as e:
            logger.error(f"❌ HEIC ingestion failed: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'format': 'heic',
                'error': str(e),
                'heic_supported': self.heic_supported
            }
    
    def _ingest_image(self, file_path: str, preprocess: bool) -> Dict[str, Any]:
        """Ingest standard image file"""
        logger.info(f"📸 Ingesting image file: {file_path}")
        
        try:
            # Read image with PIL
            pil_image = Image.open(file_path)
            
            # Convert to RGB if needed
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Convert to numpy array
            rgb_array = np.array(pil_image)
            
            # Get image info
            image_info = get_image_info(rgb_array)
            
            # Preprocess if requested
            if preprocess:
                processed_image, steps = preprocess_for_ocr(rgb_array, profile="auto")
                image_info['preprocessing_steps'] = steps
            else:
                processed_image = rgb_array
                image_info['preprocessing_steps'] = []
            
            return {
                'success': True,
                'file_path': file_path,
                'format': os.path.splitext(file_path)[1].lower(),
                'original_image': rgb_array,
                'processed_image': processed_image,
                'image_info': image_info,
                'heic_supported': self.heic_supported
            }
            
        except Exception as e:
            logger.error(f"❌ Image ingestion failed: {e}")
            return {
                'success': False,
                'file_path': file_path,
                'format': os.path.splitext(file_path)[1].lower(),
                'error': str(e),
                'heic_supported': self.heic_supported
            }
    
    def _ingest_pdf(self, file_path: str, preprocess: bool) -> Dict[str, Any]:
        """Ingest PDF file (placeholder for future implementation)"""
        logger.info(f"📄 Ingesting PDF file: {file_path}")
        
        # For now, return a placeholder
        # TODO: Implement PDF to image conversion
        return {
            'success': False,
            'file_path': file_path,
            'format': 'pdf',
            'error': 'PDF ingestion not yet implemented',
            'heic_supported': self.heic_supported
        }
    
    def ingest_from_bytes(self, file_data: bytes, file_name: str, preprocess: bool = True) -> Dict[str, Any]:
        """
        Ingest document from bytes data
        
        Args:
            file_data: Document data as bytes
            file_name: Original file name
            preprocess: Whether to apply preprocessing
            
        Returns:
            Dictionary with image data and metadata
        """
        logger.info(f"🔄 Ingesting document from bytes: {file_name}")
        
        try:
            # Determine format from file name
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported file format: {file_ext}")
            
            # Handle HEIC files
            if file_ext in ['.heic', '.heif']:
                if not self.heic_supported:
                    raise ValueError("HEIC support not available - install pillow_heif")
                
                # Convert HEIC to RGB
                rgb_array = convert_heic_to_rgb(file_data)
                
                # Get image info
                image_info = get_image_info(rgb_array)
                
                # Preprocess if requested
                if preprocess:
                    processed_image, steps = preprocess_for_ocr(rgb_array, profile="auto")
                    image_info['preprocessing_steps'] = steps
                else:
                    processed_image = rgb_array
                    image_info['preprocessing_steps'] = []
                
                return {
                    'success': True,
                    'file_name': file_name,
                    'format': 'heic',
                    'original_image': rgb_array,
                    'processed_image': processed_image,
                    'image_info': image_info,
                    'heic_supported': True
                }
            
            # Handle other image formats
            else:
                # Read image from bytes
                pil_image = Image.open(io.BytesIO(file_data))
                
                # Convert to RGB if needed
                if pil_image.mode != 'RGB':
                    pil_image = pil_image.convert('RGB')
                
                # Convert to numpy array
                rgb_array = np.array(pil_image)
                
                # Get image info
                image_info = get_image_info(rgb_array)
                
                # Preprocess if requested
                if preprocess:
                    processed_image, steps = preprocess_for_ocr(rgb_array, profile="auto")
                    image_info['preprocessing_steps'] = steps
                else:
                    processed_image = rgb_array
                    image_info['preprocessing_steps'] = []
                
                return {
                    'success': True,
                    'file_name': file_name,
                    'format': file_ext,
                    'original_image': rgb_array,
                    'processed_image': processed_image,
                    'image_info': image_info,
                    'heic_supported': self.heic_supported
                }
                
        except Exception as e:
            logger.error(f"❌ Bytes ingestion failed: {e}")
            return {
                'success': False,
                'file_name': file_name,
                'format': os.path.splitext(file_name)[1].lower(),
                'error': str(e),
                'heic_supported': self.heic_supported
            }

def get_document_ingester() -> DocumentIngester:
    """Get document ingester instance"""
    return DocumentIngester() 