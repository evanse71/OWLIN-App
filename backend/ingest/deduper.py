"""
Deduplication Engine - Bulletproof Ingestion v3

Detects and collapses duplicate pages and files while preserving provenance.
Uses perceptual hashing and content similarity for robust duplicate detection.
"""

import hashlib
from typing import List, Dict, Any, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

@dataclass
class DuplicateGroup:
    """Group of duplicate pages/files"""
    group_id: str
    primary_id: str
    duplicates: List[str]
    confidence: float
    duplicate_type: str  # 'page' or 'file'
    reasons: List[str]

@dataclass
class DuplicateCandidate:
    """Candidate for deduplication"""
    primary_id: str
    duplicate_id: str
    similarity: float
    duplicate_type: str
    reasons: List[str]
    metadata: Dict[str, Any]

class Deduper:
    """Deduplication engine for pages and files"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.phash_dup_hamming_max = self.config.get('phash_dup_hamming_max', 8)
        self.dedupe_confidence_threshold = self.config.get('dedupe_confidence_threshold', 0.85)
        
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
    
    def compute_similarity_score(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> float:
        """
        Compute similarity score between two items (pages or files)
        
        Args:
            item1: First item data
            item2: Second item data
            
        Returns:
            Similarity score (0-1)
        """
        score = 0.0
        reasons = []
        
        # Check perceptual hash similarity
        phash1 = item1.get('phash', '')
        phash2 = item2.get('phash', '')
        
        if phash1 and phash2:
            hamming_distance = self.compute_hamming_distance(phash1, phash2)
            if hamming_distance <= self.phash_dup_hamming_max:
                similarity = 1 - (hamming_distance / 64)  # 64-bit hash
                score += similarity * 0.6
                reasons.append(f'Perceptual hash similarity: {similarity:.2f}')
        
        # Check text hash similarity
        text_hash1 = item1.get('text_hash', '')
        text_hash2 = item2.get('text_hash', '')
        
        if text_hash1 and text_hash2 and text_hash1 == text_hash2:
            score += 0.4
            reasons.append('Exact text match')
        
        # Check header/footer simhash similarity
        header_sim1 = item1.get('header_simhash', '')
        header_sim2 = item2.get('header_simhash', '')
        footer_sim1 = item1.get('footer_simhash', '')
        footer_sim2 = item2.get('footer_simhash', '')
        
        if header_sim1 and header_sim2:
            header_distance = self.compute_hamming_distance(header_sim1, header_sim2)
            header_similarity = 1 - (header_distance / 64)
            if header_similarity > 0.8:
                score += header_similarity * 0.2
                reasons.append(f'Header similarity: {header_similarity:.2f}')
        
        if footer_sim1 and footer_sim2:
            footer_distance = self.compute_hamming_distance(footer_sim1, footer_sim2)
            footer_similarity = 1 - (footer_distance / 64)
            if footer_similarity > 0.8:
                score += footer_similarity * 0.2
                reasons.append(f'Footer similarity: {footer_similarity:.2f}')
        
        return min(score, 1.0), reasons
    
    def find_duplicate_candidates(self, items: List[Dict[str, Any]], item_type: str = 'page') -> List[DuplicateCandidate]:
        """
        Find potential duplicate candidates among items
        
        Args:
            items: List of item data
            item_type: Type of items ('page' or 'file')
            
        Returns:
            List of DuplicateCandidate objects
        """
        candidates = []
        
        for i, item1 in enumerate(items):
            for j, item2 in enumerate(items[i+1:], i+1):
                score, reasons = self.compute_similarity_score(item1, item2)
                
                if score >= self.dedupe_confidence_threshold:
                    candidate = DuplicateCandidate(
                        primary_id=item1.get('id', f'{item_type}_{i}'),
                        duplicate_id=item2.get('id', f'{item_type}_{j}'),
                        similarity=score,
                        duplicate_type=item_type,
                        reasons=reasons,
                        metadata={
                            'primary_path': item1.get('file_path', ''),
                            'duplicate_path': item2.get('file_path', ''),
                            'primary_size': item1.get('file_size', 0),
                            'duplicate_size': item2.get('file_size', 0)
                        }
                    )
                    candidates.append(candidate)
        
        # Sort by similarity score (highest first)
        candidates.sort(key=lambda x: x.similarity, reverse=True)
        return candidates
    
    def build_duplicate_groups(self, items: List[Dict[str, Any]], item_type: str = 'page') -> List[DuplicateGroup]:
        """
        Build duplicate groups from items
        
        Args:
            items: List of item data
            item_type: Type of items ('page' or 'file')
            
        Returns:
            List of DuplicateGroup objects
        """
        # Find duplicate candidates
        candidates = self.find_duplicate_candidates(items, item_type)
        
        # Build groups using greedy approach
        groups = []
        used_items = set()
        
        for candidate in candidates:
            # Skip if either item is already used
            if (candidate.primary_id in used_items or 
                candidate.duplicate_id in used_items):
                continue
            
            # Find existing group for primary
            primary_group = None
            for group in groups:
                if group.primary_id == candidate.primary_id:
                    primary_group = group
                    break
            
            # Find existing group for duplicate
            duplicate_group = None
            for group in groups:
                if group.primary_id == candidate.duplicate_id:
                    duplicate_group = group
                    break
            
            if primary_group and duplicate_group:
                # Merge groups if they're different
                if primary_group != duplicate_group:
                    primary_group.duplicates.extend(duplicate_group.duplicates)
                    primary_group.duplicates.append(duplicate_group.primary_id)
                    primary_group.confidence = min(primary_group.confidence, duplicate_group.confidence, candidate.similarity)
                    primary_group.reasons.extend(duplicate_group.reasons)
                    primary_group.reasons.extend(candidate.reasons)
                    groups.remove(duplicate_group)
                    used_items.add(duplicate_group.primary_id)
            
            elif primary_group:
                # Add duplicate to primary group
                primary_group.duplicates.append(candidate.duplicate_id)
                primary_group.confidence = min(primary_group.confidence, candidate.similarity)
                primary_group.reasons.extend(candidate.reasons)
                used_items.add(candidate.duplicate_id)
            
            elif duplicate_group:
                # Add primary to duplicate group (rename)
                duplicate_group.duplicates.append(duplicate_group.primary_id)
                duplicate_group.primary_id = candidate.primary_id
                duplicate_group.confidence = min(duplicate_group.confidence, candidate.similarity)
                duplicate_group.reasons.extend(candidate.reasons)
                used_items.add(candidate.duplicate_id)
            
            else:
                # Create new group
                group = DuplicateGroup(
                    group_id=f"dup_group_{item_type}_{len(groups)}",
                    primary_id=candidate.primary_id,
                    duplicates=[candidate.duplicate_id],
                    confidence=candidate.similarity,
                    duplicate_type=item_type,
                    reasons=candidate.reasons
                )
                groups.append(group)
                used_items.add(candidate.primary_id)
                used_items.add(candidate.duplicate_id)
        
        # Add unused items as individual groups (non-duplicates)
        for item in items:
            if item.get('id') not in used_items:
                group = DuplicateGroup(
                    group_id=f"dup_group_{item_type}_{len(groups)}",
                    primary_id=item.get('id', 'unknown'),
                    duplicates=[],
                    confidence=1.0,
                    duplicate_type=item_type,
                    reasons=['No duplicates found']
                )
                groups.append(group)
        
        return groups
    
    def dedupe_pages(self, pages: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """
        Deduplicate pages based on perceptual hashing and content similarity
        
        Args:
            pages: List of page data with fingerprints
            
        Returns:
            List of DuplicateGroup objects for pages
        """
        try:
            logger.info(f"🔍 Starting page deduplication for {len(pages)} pages")
            
            # Build duplicate groups
            groups = self.build_duplicate_groups(pages, 'page')
            
            # Log results
            duplicate_count = sum(len(group.duplicates) for group in groups)
            logger.info(f"✅ Page deduplication complete: {len(groups)} groups, {duplicate_count} duplicates found")
            
            return groups
            
        except Exception as e:
            logger.error(f"Page deduplication failed: {e}")
            # Return individual pages as groups
            return [
                DuplicateGroup(
                    group_id=f"dup_group_page_{i}",
                    primary_id=page.get('id', f'page_{i}'),
                    duplicates=[],
                    confidence=1.0,
                    duplicate_type='page',
                    reasons=['Deduplication failed']
                )
                for i, page in enumerate(pages)
            ]
    
    def dedupe_files(self, files: List[Dict[str, Any]]) -> List[DuplicateGroup]:
        """
        Deduplicate files based on content similarity
        
        Args:
            files: List of file data with metadata
            
        Returns:
            List of DuplicateGroup objects for files
        """
        try:
            logger.info(f"🔍 Starting file deduplication for {len(files)} files")
            
            # Build duplicate groups
            groups = self.build_duplicate_groups(files, 'file')
            
            # Log results
            duplicate_count = sum(len(group.duplicates) for group in groups)
            logger.info(f"✅ File deduplication complete: {len(groups)} groups, {duplicate_count} duplicates found")
            
            return groups
            
        except Exception as e:
            logger.error(f"File deduplication failed: {e}")
            # Return individual files as groups
            return [
                DuplicateGroup(
                    group_id=f"dup_group_file_{i}",
                    primary_id=file.get('id', f'file_{i}'),
                    duplicates=[],
                    confidence=1.0,
                    duplicate_type='file',
                    reasons=['Deduplication failed']
                )
                for i, file in enumerate(files)
            ]
    
    def is_duplicate_page(self, page1: Dict[str, Any], page2: Dict[str, Any]) -> bool:
        """
        Check if two pages are duplicates
        
        Args:
            page1: First page data
            page2: Second page data
            
        Returns:
            True if pages are considered duplicates
        """
        try:
            score, _ = self.compute_similarity_score(page1, page2)
            return score >= self.dedupe_confidence_threshold
            
        except Exception as e:
            logger.error(f"Failed to check page duplication: {e}")
            return False
    
    def is_duplicate_file(self, file1: Dict[str, Any], file2: Dict[str, Any]) -> bool:
        """
        Check if two files are duplicates
        
        Args:
            file1: First file data
            file2: Second file data
            
        Returns:
            True if files are considered duplicates
        """
        try:
            score, _ = self.compute_similarity_score(file1, file2)
            return score >= self.dedupe_confidence_threshold
            
        except Exception as e:
            logger.error(f"Failed to check file duplication: {e}")
            return False
    
    def get_deduplication_summary(self, page_groups: List[DuplicateGroup], file_groups: List[DuplicateGroup]) -> Dict[str, Any]:
        """
        Generate deduplication summary
        
        Args:
            page_groups: List of page duplicate groups
            file_groups: List of file duplicate groups
            
        Returns:
            Summary dictionary
        """
        total_pages = sum(1 + len(group.duplicates) for group in page_groups)
        duplicate_pages = sum(len(group.duplicates) for group in page_groups)
        
        total_files = sum(1 + len(group.duplicates) for group in file_groups)
        duplicate_files = sum(len(group.duplicates) for group in file_groups)
        
        return {
            'pages': {
                'total': total_pages,
                'duplicates': duplicate_pages,
                'unique': total_pages - duplicate_pages,
                'groups': len(page_groups)
            },
            'files': {
                'total': total_files,
                'duplicates': duplicate_files,
                'unique': total_files - duplicate_files,
                'groups': len(file_groups)
            },
            'total_savings': duplicate_pages + duplicate_files
        } 