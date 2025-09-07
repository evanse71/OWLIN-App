"""
Page Fingerprinting System - Bulletproof Ingestion v3

Provides perceptual hashing and layout fingerprinting for duplicate detection
and cross-file stitching capabilities.
"""

import hashlib
import numpy as np
from typing import Tuple, Dict, Any, List, Optional
from dataclasses import dataclass
from PIL import Image
import cv2
import logging

logger = logging.getLogger(__name__)

@dataclass
class PageFingerprint:
    """Page fingerprint data structure"""
    phash: str
    header_simhash: str
    footer_simhash: str
    text_hash: str
    width: int
    height: int
    aspect_ratio: float
    features: Dict[str, Any]

class PageFingerprinter:
    """Page fingerprinting system using perceptual hashing and simhash"""
    
    def __init__(self, hash_size: int = 8):
        self.hash_size = hash_size
        self.phash_size = hash_size
        
    def compute_perceptual_hash(self, image: Image.Image) -> str:
        """
        Compute perceptual hash of image using DCT-based approach
        
        Args:
            image: PIL Image object
            
        Returns:
            Perceptual hash as hexadecimal string
        """
        try:
            # Convert to grayscale and resize
            if image.mode != 'L':
                image = image.convert('L')
            
            # Resize to hash_size x hash_size
            resized = image.resize((self.phash_size, self.phash_size))
            
            # Convert to numpy array
            pixels = np.array(resized, dtype=np.float64)
            
            # Compute DCT
            dct = cv2.dct(pixels)
            
            # Take top-left hash_size x hash_size (excluding DC component)
            dct_low = dct[:self.phash_size, :self.phash_size]
            
            # Compute median
            median = np.median(dct_low)
            
            # Create hash: 1 if value > median, 0 otherwise
            hash_bits = dct_low > median
            
            # Convert to hexadecimal
            hash_int = 0
            for i in range(self.phash_size):
                for j in range(self.phash_size):
                    if hash_bits[i, j]:
                        hash_int |= 1 << (i * self.phash_size + j)
            
            return format(hash_int, '016x')
            
        except Exception as e:
            logger.error(f"Failed to compute perceptual hash: {e}")
            return "0" * 16
    
    def compute_simhash(self, text: str, window_size: int = 4) -> str:
        """
        Compute simhash for text (header/footer detection)
        
        Args:
            text: Text content
            window_size: Size of sliding window for n-grams
            
        Returns:
            Simhash as hexadecimal string
        """
        try:
            if not text or len(text.strip()) < window_size:
                return "0" * 16
            
            # Create n-grams
            ngrams = []
            text_lower = text.lower()
            
            for i in range(len(text_lower) - window_size + 1):
                ngrams.append(text_lower[i:i + window_size])
            
            if not ngrams:
                return "0" * 16
            
            # Hash each n-gram
            hash_values = []
            for ngram in ngrams:
                hash_val = hash(ngram) & 0xFFFFFFFFFFFFFFFF  # 64-bit hash
                hash_values.append(hash_val)
            
            # Compute simhash
            simhash_bits = [0] * 64
            
            for hash_val in hash_values:
                for i in range(64):
                    if hash_val & (1 << i):
                        simhash_bits[i] += 1
                    else:
                        simhash_bits[i] -= 1
            
            # Convert to final hash
            simhash_int = 0
            for i in range(64):
                if simhash_bits[i] > 0:
                    simhash_int |= 1 << i
            
            return format(simhash_int, '016x')
            
        except Exception as e:
            logger.error(f"Failed to compute simhash: {e}")
            return "0" * 16
    
    def compute_text_hash(self, text: str) -> str:
        """Compute simple hash of text content"""
        try:
            if not text:
                return "0" * 16
            return hashlib.md5(text.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"Failed to compute text hash: {e}")
            return "0" * 16
    
    def extract_header_footer(self, text: str, header_ratio: float = 0.1, footer_ratio: float = 0.1) -> Tuple[str, str]:
        """
        Extract header and footer text from page content
        
        Args:
            text: Full page text
            header_ratio: Ratio of page height for header (default 10%)
            footer_ratio: Ratio of page height for footer (default 10%)
            
        Returns:
            Tuple of (header_text, footer_text)
        """
        try:
            lines = text.split('\n')
            if not lines:
                return "", ""
            
            header_end = max(1, int(len(lines) * header_ratio))
            footer_start = max(0, len(lines) - int(len(lines) * footer_ratio))
            
            header_text = '\n'.join(lines[:header_end])
            footer_text = '\n'.join(lines[footer_start:])
            
            return header_text.strip(), footer_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract header/footer: {e}")
            return "", ""
    
    def compute_fingerprint(self, image: Image.Image, text: str = "") -> PageFingerprint:
        """
        Compute comprehensive page fingerprint
        
        Args:
            image: PIL Image object
            text: OCR text content
            
        Returns:
            PageFingerprint object
        """
        try:
            # Compute perceptual hash
            phash = self.compute_perceptual_hash(image)
            
            # Extract header/footer and compute simhashes
            header_text, footer_text = self.extract_header_footer(text)
            header_simhash = self.compute_simhash(header_text)
            footer_simhash = self.compute_simhash(footer_text)
            
            # Compute text hash
            text_hash = self.compute_text_hash(text)
            
            # Extract basic features
            width, height = image.size
            aspect_ratio = width / height if height > 0 else 0
            
            features = {
                'width': width,
                'height': height,
                'aspect_ratio': aspect_ratio,
                'text_length': len(text),
                'text_lines': len(text.split('\n')),
                'has_text': len(text.strip()) > 0
            }
            
            return PageFingerprint(
                phash=phash,
                header_simhash=header_simhash,
                footer_simhash=footer_simhash,
                text_hash=text_hash,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                features=features
            )
            
        except Exception as e:
            logger.error(f"Failed to compute page fingerprint: {e}")
            # Return default fingerprint
            return PageFingerprint(
                phash="0" * 16,
                header_simhash="0" * 16,
                footer_simhash="0" * 16,
                text_hash="0" * 16,
                width=0,
                height=0,
                aspect_ratio=0.0,
                features={}
            )
    
    def compute_hamming_distance(self, hash1: str, hash2: str) -> int:
        """
        Compute Hamming distance between two hexadecimal hashes
        
        Args:
            hash1: First hash as hex string
            hash2: Second hash as hex string
            
        Returns:
            Hamming distance (number of different bits)
        """
        try:
            # Convert hex strings to integers
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            
            # XOR and count set bits
            xor_result = int1 ^ int2
            return bin(xor_result).count('1')
            
        except Exception as e:
            logger.error(f"Failed to compute Hamming distance: {e}")
            return float('inf')
    
    def are_pages_similar(self, fp1: PageFingerprint, fp2: PageFingerprint, 
                         phash_threshold: int = 8, simhash_threshold: float = 0.86) -> bool:
        """
        Determine if two pages are similar based on fingerprints
        
        Args:
            fp1: First page fingerprint
            fp2: Second page fingerprint
            phash_threshold: Maximum Hamming distance for perceptual hash
            simhash_threshold: Minimum similarity for simhash
            
        Returns:
            True if pages are considered similar
        """
        try:
            # Check perceptual hash similarity
            phash_distance = self.compute_hamming_distance(fp1.phash, fp2.phash)
            if phash_distance <= phash_threshold:
                return True
            
            # Check header/footer simhash similarity
            header_distance = self.compute_hamming_distance(fp1.header_simhash, fp2.header_simhash)
            footer_distance = self.compute_hamming_distance(fp1.footer_simhash, fp2.footer_simhash)
            
            # Convert to similarity scores (0-1)
            header_similarity = 1 - (header_distance / 64)
            footer_similarity = 1 - (footer_distance / 64)
            
            if header_similarity >= simhash_threshold or footer_similarity >= simhash_threshold:
                return True
            
            # Check text hash exact match
            if fp1.text_hash == fp2.text_hash and fp1.text_hash != "0" * 16:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to compare page similarity: {e}")
            return False 