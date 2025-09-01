"""
Header fingerprinting for document assembly.
Combines pHash, ORB features, and OCR keywords to identify document headers.
"""
import hashlib
import cv2
import numpy as np
from PIL import Image
import io
from typing import Dict, List, Optional, Tuple, Union
from pathlib import Path

class HeaderFingerprint:
    """Document header fingerprinting for assembly"""
    
    def __init__(self):
        self.orb = cv2.ORB_create(nfeatures=50)
        self.phash_size = 8
        
    def compute_header_id(self, image_path: Union[str, Path]) -> str:
        """Compute combined header fingerprint"""
        try:
            # Load image
            img = cv2.imread(str(image_path))
            if img is None:
                return ""
                
            # Crop top 20% for header
            height = img.shape[0]
            header_crop = img[:int(height * 0.2), :]
            
            # Compute components
            phash = self._compute_phash(header_crop)
            orb_hash = self._compute_orb_hash(header_crop)
            ocr_bag = self._compute_ocr_keywords(header_crop)
            
            # Combine into header ID
            combined = f"{phash}|{orb_hash}|{ocr_bag}"
            return hashlib.sha1(combined.encode()).hexdigest()[:16]
            
        except Exception as e:
            print(f"Header fingerprint failed for {image_path}: {e}")
            return ""
    
    def _compute_phash(self, img: np.ndarray) -> str:
        """Perceptual hash of header region"""
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Resize to 8x8
        resized = cv2.resize(gray, (self.phash_size, self.phash_size))
        
        # Compute DCT
        dct = cv2.dct(np.float32(resized))
        
        # Extract top-left 8x8 (excluding DC component)
        dct_reduced = dct[0:self.phash_size, 0:self.phash_size]
        
        # Compute median
        median = np.median(dct_reduced)
        
        # Generate hash
        hash_bits = dct_reduced > median
        phash = ''.join(['1' if bit else '0' for bit in hash_bits.flatten()])
        
        return phash
    
    def _compute_orb_hash(self, img: np.ndarray) -> str:
        """ORB feature hash of header region"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Detect ORB keypoints and descriptors
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        if descriptors is None or len(descriptors) == 0:
            return "0" * 32
            
        # Hash the descriptors
        desc_bytes = descriptors.tobytes()
        return hashlib.md5(desc_bytes).hexdigest()[:8]
    
    def _compute_ocr_keywords(self, img: np.ndarray) -> str:
        """OCR keyword bag from header region"""
        try:
            # Simple OCR for header keywords (company names, addresses)
            # For MVP, use basic text extraction
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold for better OCR
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert to PIL for OCR
            pil_img = Image.fromarray(thresh)
            
            # Extract text (would use pytesseract in production)
            # For now, return empty bag
            keywords = []
            
            # Sort and join keywords
            keyword_bag = "|".join(sorted(set(keywords)))
            return hashlib.md5(keyword_bag.encode()).hexdigest()[:8]
            
        except Exception:
            return "0" * 8
    
    def compare_headers(self, header_id1: str, header_id2: str) -> float:
        """Compare two header IDs and return similarity score (0-1)"""
        if not header_id1 or not header_id2 or header_id1 == header_id2:
            return 1.0 if header_id1 == header_id2 else 0.0
            
        # For now, simple string comparison
        # In production, would parse components and compute Hamming distance
        return 0.8 if header_id1[:8] == header_id2[:8] else 0.2
    
    def hamming_distance(self, hash1: str, hash2: str) -> int:
        """Compute Hamming distance between two hash strings"""
        if len(hash1) != len(hash2):
            return max(len(hash1), len(hash2))
        return sum(c1 != c2 for c1, c2 in zip(hash1, hash2)) 