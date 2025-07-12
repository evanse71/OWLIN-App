"""
OCR Preprocessing Pipeline for Owlin App
Enhances image quality before OCR processing to improve accuracy.
"""
import cv2
import numpy as np
import logging
from typing import List, Tuple, Dict, Optional
from skimage import filters, morphology, measure
from skimage.restoration import denoise_bilateral, denoise_tv_chambolle
from skimage.filters import threshold_otsu, threshold_local
from skimage.transform import rotate
from skimage.util import img_as_ubyte

logger = logging.getLogger(__name__)

class OCRPreprocessor:
    """Advanced OCR preprocessing pipeline for improving image quality and OCR accuracy."""
    
    def __init__(self, config: Optional[Dict] = None):
        """Initialize the OCR preprocessor with configuration."""
        self.config = config or self._get_default_config()
        logger.info("OCR Preprocessor initialized")
    
    def _get_default_config(self) -> Dict:
        """Get default preprocessing configuration."""
        return {
            'denoising': {'enabled': True, 'method': 'bilateral', 'sigma_color': 75, 'sigma_spatial': 75},
            'thresholding': {'enabled': True, 'method': 'adaptive', 'block_size': 35, 'offset': 10},
            'deskewing': {'enabled': True, 'max_angle': 15},
            'contrast_enhancement': {'enabled': True, 'method': 'clahe', 'clip_limit': 2.0},
            'morphology': {'enabled': True, 'operation': 'opening', 'kernel_size': 2},
            'resize': {'enabled': True, 'min_width': 800, 'max_width': 2000},
            'quality_assessment': {'enabled': True, 'min_quality_score': 0.3}
        }
    
    def assess_image_quality(self, image: np.ndarray) -> Dict[str, float]:
        """
        Assess image quality to determine if preprocessing is needed.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary with quality metrics
        """
        try:
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Calculate quality metrics
            metrics = {}
            
            # 1. Contrast (standard deviation)
            metrics['contrast'] = float(np.std(gray))
            
            # 2. Sharpness (Laplacian variance)
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            metrics['sharpness'] = float(laplacian.var())
            
            # 3. Noise level (high-frequency content)
            kernel = np.array([[-1, -1, -1], [-1, 8, -1], [-1, -1, -1]])
            noise = cv2.filter2D(gray.astype(np.float32), -1, kernel)
            metrics['noise_level'] = float(np.std(noise))
            
            # 4. Overall quality score (0-1)
            # Normalize metrics to 0-1 range
            contrast_score = min(metrics['contrast'] / 50.0, 1.0)  # Good contrast > 50
            sharpness_score = min(metrics['sharpness'] / 500.0, 1.0)  # Good sharpness > 500
            noise_score = max(0, 1.0 - metrics['noise_level'] / 30.0)  # Low noise is better
            
            metrics['quality_score'] = (contrast_score + sharpness_score + noise_score) / 3.0
            
            # 5. Determine if preprocessing is recommended
            metrics['needs_preprocessing'] = metrics['quality_score'] < self.config['quality_assessment']['min_quality_score']
            
            logger.debug(f"Image quality assessment: score={metrics['quality_score']:.3f}, needs_preprocessing={metrics['needs_preprocessing']}")
            return metrics
            
        except Exception as e:
            logger.warning(f"Quality assessment failed: {e}")
            return {
                'contrast': 0.0,
                'sharpness': 0.0,
                'noise_level': 0.0,
                'quality_score': 0.0,
                'needs_preprocessing': True  # Default to preprocessing if assessment fails
            }
    
    def preprocess_image(self, image: np.ndarray, force_preprocessing: bool = False) -> np.ndarray:
        """
        Apply comprehensive preprocessing pipeline to improve OCR accuracy.
        
        Args:
            image: Input image as numpy array
            force_preprocessing: Whether to skip quality assessment and always preprocess
            
        Returns:
            Preprocessed image optimized for OCR
        """
        try:
            logger.debug(f"Starting preprocessing for image shape: {image.shape}")
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Assess image quality if enabled
            if self.config['quality_assessment']['enabled'] and not force_preprocessing:
                quality_metrics = self.assess_image_quality(gray)
                if not quality_metrics['needs_preprocessing']:
                    logger.info(f"Image quality is good (score: {quality_metrics['quality_score']:.3f}), skipping preprocessing")
                    return gray
            
            processed = gray.copy()
            
            # Apply preprocessing steps
            if self.config['resize']['enabled']:
                processed = self._resize_image(processed)
            
            if self.config['deskewing']['enabled']:
                processed = self._deskew_image(processed)
            
            if self.config['denoising']['enabled']:
                processed = self._denoise_image(processed)
            
            if self.config['contrast_enhancement']['enabled']:
                processed = self._enhance_contrast(processed)
            
            if self.config['thresholding']['enabled']:
                processed = self._apply_thresholding(processed)
            
            if self.config['morphology']['enabled']:
                processed = self._apply_morphology(processed)
            
            processed = img_as_ubyte(processed)
            logger.info("Preprocessing completed successfully")
            return processed
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Return original image if preprocessing fails
            return image
    
    def _resize_image(self, image: np.ndarray) -> np.ndarray:
        """Resize image to optimal dimensions for OCR."""
        try:
            height, width = image.shape
            min_width = self.config['resize']['min_width']
            max_width = self.config['resize']['max_width']
            
            if width < min_width:
                scale_factor = min_width / width
                new_width, new_height = min_width, int(height * scale_factor)
            elif width > max_width:
                scale_factor = max_width / width
                new_width, new_height = max_width, int(height * scale_factor)
            else:
                return image
            
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            logger.debug(f"Resized from {width}x{height} to {new_width}x{new_height}")
            return resized
            
        except Exception as e:
            logger.warning(f"Image resizing failed: {e}")
            return image
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Deskew the image by detecting and correcting rotation."""
        try:
            binary = image > threshold_otsu(image)
            contours, _ = cv2.findContours(img_as_ubyte(binary), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return image
            
            largest_contour = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(largest_contour)
            angle = rect[2]
            
            if angle < -45:
                angle = 90 + angle
            
            max_angle = self.config['deskewing']['max_angle']
            if abs(angle) > max_angle or abs(angle) < 0.5:
                return image
            
            height, width = image.shape
            center = (width // 2, height // 2)
            rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            deskewed = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            logger.debug(f"Deskewed by {angle:.2f} degrees")
            return deskewed
            
        except Exception as e:
            logger.warning(f"Deskewing failed: {e}")
            return image
    
    def _denoise_image(self, image: np.ndarray) -> np.ndarray:
        """Apply denoising to reduce noise while preserving edges."""
        method = self.config['denoising']['method']
        
        try:
            if method == 'bilateral':
                sigma_color = self.config['denoising']['sigma_color']
                sigma_spatial = self.config['denoising']['sigma_spatial']
                denoised = denoise_bilateral(image, sigma_color=sigma_color, sigma_spatial=sigma_spatial)
            elif method == 'tv_chambolle':
                denoised = denoise_tv_chambolle(image, weight=0.1)
            elif method == 'gaussian':
                denoised = cv2.GaussianBlur(image, (3, 3), 0)
            else:
                return image
            
            logger.debug(f"Applied {method} denoising")
            return denoised
            
        except Exception as e:
            logger.warning(f"Denoising failed: {e}")
            return image
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance image contrast for better OCR results."""
        method = self.config['contrast_enhancement']['method']
        
        try:
            if method == 'clahe':
                clip_limit = self.config['contrast_enhancement']['clip_limit']
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
                enhanced = clahe.apply(image)
            elif method == 'histogram_equalization':
                enhanced = cv2.equalizeHist(image)
            elif method == 'gamma':
                gamma = 1.2
                normalized = image.astype(np.float32) / 255.0
                corrected = np.power(normalized, gamma)
                enhanced = (corrected * 255).astype(np.uint8)
            else:
                return image
            
            logger.debug(f"Applied {method} contrast enhancement")
            return enhanced
            
        except Exception as e:
            logger.warning(f"Contrast enhancement failed: {e}")
            return image
    
    def _apply_thresholding(self, image: np.ndarray) -> np.ndarray:
        """Apply adaptive thresholding for better text extraction."""
        method = self.config['thresholding']['method']
        
        try:
            if method == 'otsu':
                threshold = threshold_otsu(image)
                binary = image > threshold
            elif method == 'adaptive':
                block_size = self.config['thresholding']['block_size']
                offset = self.config['thresholding']['offset']
                # Use OpenCV adaptive thresholding instead of skimage
                binary = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                             cv2.THRESH_BINARY, block_size, offset)
                return binary
            elif method == 'local':
                block_size = self.config['thresholding']['block_size']
                offset = self.config['thresholding']['offset']
                binary = threshold_local(image, block_size, offset=offset)
            else:
                return image
            
            binary = img_as_ubyte(binary)
            logger.debug(f"Applied {method} thresholding")
            return binary
            
        except Exception as e:
            logger.warning(f"Thresholding failed: {e}")
            return image
    
    def _apply_morphology(self, image: np.ndarray) -> np.ndarray:
        """Apply morphological operations to clean up the image."""
        operation = self.config['morphology']['operation']
        kernel_size = self.config['morphology']['kernel_size']
        
        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
            
            if operation == 'opening':
                processed = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
            elif operation == 'closing':
                processed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
            elif operation == 'both':
                processed = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
                processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)
            else:
                return image
            
            logger.debug(f"Applied {operation} morphological operation")
            return processed
            
        except Exception as e:
            logger.warning(f"Morphological operation failed: {e}")
            return image
    
    def batch_preprocess(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Preprocess multiple images in batch."""
        logger.info(f"Starting batch preprocessing of {len(images)} images")
        
        processed_images = []
        for i, image in enumerate(images):
            logger.debug(f"Preprocessing image {i+1}/{len(images)}")
            processed = self.preprocess_image(image)
            processed_images.append(processed)
        
        logger.info(f"Batch preprocessing completed for {len(images)} images")
        return processed_images
    
    def get_preprocessing_stats(self, original: np.ndarray, processed: np.ndarray) -> Dict:
        """Calculate statistics about preprocessing improvements."""
        try:
            return {
                'contrast_improvement': float(np.std(processed) - np.std(original)),
                'noise_reduction': float(np.var(original) - np.var(processed)),
                'edge_preservation': self._calculate_edge_preservation(original, processed),
                'text_clarity': self._calculate_text_clarity(processed)
            }
        except Exception as e:
            logger.warning(f"Failed to calculate preprocessing stats: {e}")
            return {
                'contrast_improvement': 0.0,
                'noise_reduction': 0.0,
                'edge_preservation': 0.0,
                'text_clarity': 0.0
            }
    
    def _calculate_edge_preservation(self, original: np.ndarray, processed: np.ndarray) -> float:
        """Calculate edge preservation metric."""
        try:
            grad_orig = cv2.Sobel(original, cv2.CV_64F, 1, 1)
            grad_proc = cv2.Sobel(processed, cv2.CV_64F, 1, 1)
            correlation = np.corrcoef(grad_orig.flatten(), grad_proc.flatten())[0, 1]
            return float(correlation if not np.isnan(correlation) else 0.0)
        except:
            return 0.0
    
    def _calculate_text_clarity(self, image: np.ndarray) -> float:
        """Calculate text clarity metric."""
        try:
            kernel = np.ones((3, 3), np.float32) / 9
            local_mean = cv2.filter2D(image.astype(np.float32), -1, kernel)
            local_var = cv2.filter2D((image.astype(np.float32) - local_mean) ** 2, -1, kernel)
            return float(np.mean(local_var))
        except:
            return 0.0

def create_preprocessing_config(denoising_method: str = 'bilateral',
                              thresholding_method: str = 'adaptive',
                              contrast_method: str = 'clahe',
                              enable_deskewing: bool = True) -> Dict:
    """Create a preprocessing configuration with specified parameters."""
    return {
        'denoising': {'enabled': True, 'method': denoising_method, 'sigma_color': 75, 'sigma_spatial': 75},
        'thresholding': {'enabled': True, 'method': thresholding_method, 'block_size': 35, 'offset': 10},
        'deskewing': {'enabled': enable_deskewing, 'max_angle': 15},
        'contrast_enhancement': {'enabled': True, 'method': contrast_method, 'clip_limit': 2.0},
        'morphology': {'enabled': True, 'operation': 'opening', 'kernel_size': 2},
        'resize': {'enabled': True, 'min_width': 800, 'max_width': 2000},
        'quality_assessment': {'enabled': True, 'min_quality_score': 0.3}
    } 