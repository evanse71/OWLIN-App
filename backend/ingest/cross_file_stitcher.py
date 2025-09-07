"""
Cross-File Stitcher - Bulletproof Ingestion v3

Reconstructs documents that have been split across multiple files or have pages
out of order. Uses multiple signals to determine which segments belong together.
"""

import re
import hashlib
from typing import List, Dict, Any, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class StitchGroup:
    """Group of segments that should be stitched together"""
    group_id: str
    segments: List[Dict[str, Any]]
    confidence: float
    doc_type: str
    supplier_guess: str
    invoice_numbers: List[str]
    dates: List[str]
    reasons: List[str]

@dataclass
class StitchCandidate:
    """Candidate for stitching two segments"""
    segment1_id: str
    segment2_id: str
    score: float
    reasons: List[str]
    metadata: Dict[str, Any]

class CrossFileStitcher:
    """Cross-file stitching system for reconstructing split documents"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.stitch_score_min = self.config.get('stitch_score_min', 0.72)
        self.header_simhash_min = self.config.get('header_simhash_min', 0.86)
        self.footer_simhash_min = self.config.get('footer_simhash_min', 0.84)
        self.max_stitch_group_size = self.config.get('max_stitch_group_size', 10)
        
    def extract_invoice_numbers(self, text: str) -> List[str]:
        """Extract all invoice numbers from text"""
        patterns = [
            r'\b(?:invoice|inv)\s*#?\s*:?\s*([A-Za-z0-9\-_/]{3,20})\b',
            r'\b(INV[0-9\-_/]{3,20})\b',
            r'\b([A-Z]{2,4}[0-9]{3,8})\b'
        ]
        
        invoice_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    invoice_numbers.extend(match)
                else:
                    invoice_numbers.append(match)
        
        return list(set(invoice_numbers))
    
    def extract_dates(self, text: str) -> List[str]:
        """Extract all dates from text"""
        patterns = [
            r'\b(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
            r'\b(\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2})\b',
            r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b'
        ]
        
        dates = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return list(set(dates))
    
    def extract_supplier_guess(self, text: str) -> str:
        """Extract supplier name from text"""
        patterns = [
            r'\b([A-Z][A-Z\s&\.]+(?:LTD|LIMITED|INC|CORP|LLC|CO|COMPANY))\b',
            r'^(?:from|supplier|company):\s*([A-Za-z\s&\.]+)',
            r'\b([A-Z][A-Z\s&\.]{3,20})\s+(?:invoice|delivery|receipt)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def compute_similarity_score(self, seg1: Dict[str, Any], seg2: Dict[str, Any]) -> float:
        """
        Compute similarity score between two segments
        
        Args:
            seg1: First segment data
            seg2: Second segment data
            
        Returns:
            Similarity score (0-1)
        """
        score = 0.0
        reasons = []
        
        # Check supplier similarity
        supplier1 = seg1.get('supplier_guess', '').lower()
        supplier2 = seg2.get('supplier_guess', '').lower()
        if supplier1 and supplier2:
            if supplier1 == supplier2:
                score += 0.3
                reasons.append('Same supplier')
            elif supplier1 in supplier2 or supplier2 in supplier1:
                score += 0.2
                reasons.append('Similar supplier')
        
        # Check invoice numbers
        inv_nums1 = set(seg1.get('invoice_numbers', []))
        inv_nums2 = set(seg2.get('invoice_numbers', []))
        if inv_nums1 and inv_nums2:
            common_inv = inv_nums1.intersection(inv_nums2)
            if common_inv:
                score += 0.4
                reasons.append(f'Common invoice numbers: {list(common_inv)}')
        
        # Check dates
        dates1 = set(seg1.get('dates', []))
        dates2 = set(seg2.get('dates', []))
        if dates1 and dates2:
            common_dates = dates1.intersection(dates2)
            if common_dates:
                score += 0.2
                reasons.append(f'Common dates: {list(common_dates)}')
        
        # Check header/footer simhash similarity
        header_sim1 = seg1.get('header_simhash', '')
        header_sim2 = seg2.get('header_simhash', '')
        footer_sim1 = seg1.get('footer_simhash', '')
        footer_sim2 = seg2.get('footer_simhash', '')
        
        if header_sim1 and header_sim2:
            similarity = self.compute_hash_similarity(header_sim1, header_sim2)
            if similarity >= self.header_simhash_min:
                score += 0.2
                reasons.append(f'Similar header (similarity: {similarity:.2f})')
        
        if footer_sim1 and footer_sim2:
            similarity = self.compute_hash_similarity(footer_sim1, footer_sim2)
            if similarity >= self.footer_simhash_min:
                score += 0.2
                reasons.append(f'Similar footer (similarity: {similarity:.2f})')
        
        # Check temporal proximity (upload times)
        time1 = seg1.get('upload_time')
        time2 = seg2.get('upload_time')
        if time1 and time2:
            try:
                time_diff = abs((time1 - time2).total_seconds())
                if time_diff < 3600:  # Within 1 hour
                    score += 0.1
                    reasons.append('Temporal proximity')
            except:
                pass
        
        # Check document type compatibility
        doc_type1 = seg1.get('doc_type', 'other')
        doc_type2 = seg2.get('doc_type', 'other')
        if doc_type1 == doc_type2 and doc_type1 != 'other':
            score += 0.1
            reasons.append('Same document type')
        
        return min(score, 1.0), reasons
    
    def compute_hash_similarity(self, hash1: str, hash2: str) -> float:
        """Compute similarity between two hashes"""
        try:
            if not hash1 or not hash2 or hash1 == "0" * 16 or hash2 == "0" * 16:
                return 0.0
            
            # Convert hex strings to integers
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            
            # Compute Hamming distance
            xor_result = int1 ^ int2
            hamming_distance = bin(xor_result).count('1')
            
            # Convert to similarity (0-1)
            max_distance = 64  # 64-bit hash
            similarity = 1 - (hamming_distance / max_distance)
            
            return similarity
            
        except Exception as e:
            logger.error(f"Failed to compute hash similarity: {e}")
            return 0.0
    
    def find_stitch_candidates(self, segments: List[Dict[str, Any]]) -> List[StitchCandidate]:
        """
        Find potential stitch candidates among segments
        
        Args:
            segments: List of segment data
            
        Returns:
            List of StitchCandidate objects
        """
        candidates = []
        
        for i, seg1 in enumerate(segments):
            for j, seg2 in enumerate(segments[i+1:], i+1):
                score, reasons = self.compute_similarity_score(seg1, seg2)
                
                if score >= self.stitch_score_min:
                    candidate = StitchCandidate(
                        segment1_id=seg1.get('id', f'seg_{i}'),
                        segment2_id=seg2.get('id', f'seg_{j}'),
                        score=score,
                        reasons=reasons,
                        metadata={
                            'supplier1': seg1.get('supplier_guess', ''),
                            'supplier2': seg2.get('supplier_guess', ''),
                            'doc_type1': seg1.get('doc_type', ''),
                            'doc_type2': seg2.get('doc_type', ''),
                            'invoice_nums1': seg1.get('invoice_numbers', []),
                            'invoice_nums2': seg2.get('invoice_numbers', [])
                        }
                    )
                    candidates.append(candidate)
        
        # Sort by score (highest first)
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates
    
    def build_stitch_groups(self, segments: List[Dict[str, Any]]) -> List[StitchGroup]:
        """
        Build stitch groups from segments
        
        Args:
            segments: List of segment data
            
        Returns:
            List of StitchGroup objects
        """
        # Find stitch candidates
        candidates = self.find_stitch_candidates(segments)
        
        # Build groups using greedy approach
        groups = []
        used_segments = set()
        
        for candidate in candidates:
            # Skip if either segment is already used
            if (candidate.segment1_id in used_segments or 
                candidate.segment2_id in used_segments):
                continue
            
            # Find existing group for segment1
            group1 = None
            for group in groups:
                if any(seg.get('id') == candidate.segment1_id for seg in group.segments):
                    group1 = group
                    break
            
            # Find existing group for segment2
            group2 = None
            for group in groups:
                if any(seg.get('id') == candidate.segment2_id for seg in group.segments):
                    group2 = group
                    break
            
            if group1 and group2:
                # Merge groups if they're different
                if group1 != group2:
                    group1.segments.extend(group2.segments)
                    group1.confidence = min(group1.confidence, group2.confidence, candidate.score)
                    group1.reasons.extend(group2.reasons)
                    group1.reasons.extend(candidate.reasons)
                    groups.remove(group2)
            
            elif group1:
                # Add segment2 to group1
                seg2 = next(seg for seg in segments if seg.get('id') == candidate.segment2_id)
                group1.segments.append(seg2)
                group1.confidence = min(group1.confidence, candidate.score)
                group1.reasons.extend(candidate.reasons)
                used_segments.add(candidate.segment2_id)
            
            elif group2:
                # Add segment1 to group2
                seg1 = next(seg for seg in segments if seg.get('id') == candidate.segment1_id)
                group2.segments.append(seg1)
                group2.confidence = min(group2.confidence, candidate.score)
                group2.reasons.extend(candidate.reasons)
                used_segments.add(candidate.segment1_id)
            
            else:
                # Create new group
                seg1 = next(seg for seg in segments if seg.get('id') == candidate.segment1_id)
                seg2 = next(seg for seg in segments if seg.get('id') == candidate.segment2_id)
                
                # Determine group properties
                doc_type = seg1.get('doc_type') if seg1.get('doc_type') != 'other' else seg2.get('doc_type')
                supplier_guess = seg1.get('supplier_guess') or seg2.get('supplier_guess')
                invoice_numbers = list(set(seg1.get('invoice_numbers', []) + seg2.get('invoice_numbers', [])))
                dates = list(set(seg1.get('dates', []) + seg2.get('dates', [])))
                
                group = StitchGroup(
                    group_id=f"stitch_group_{len(groups)}",
                    segments=[seg1, seg2],
                    confidence=candidate.score,
                    doc_type=doc_type or 'other',
                    supplier_guess=supplier_guess,
                    invoice_numbers=invoice_numbers,
                    dates=dates,
                    reasons=candidate.reasons
                )
                groups.append(group)
                used_segments.add(candidate.segment1_id)
                used_segments.add(candidate.segment2_id)
        
        # Add unused segments as individual groups
        for segment in segments:
            if segment.get('id') not in used_segments:
                group = StitchGroup(
                    group_id=f"stitch_group_{len(groups)}",
                    segments=[segment],
                    confidence=1.0,
                    doc_type=segment.get('doc_type', 'other'),
                    supplier_guess=segment.get('supplier_guess', ''),
                    invoice_numbers=segment.get('invoice_numbers', []),
                    dates=segment.get('dates', []),
                    reasons=['Single segment']
                )
                groups.append(group)
        
        return groups
    
    def stitch_segments(self, segments: List[Dict[str, Any]]) -> List[StitchGroup]:
        """
        Main stitching method
        
        Args:
            segments: List of segment data with fingerprints and metadata
            
        Returns:
            List of StitchGroup objects
        """
        try:
            # Preprocess segments
            for segment in segments:
                segment['invoice_numbers'] = self.extract_invoice_numbers(segment.get('text', ''))
                segment['dates'] = self.extract_dates(segment.get('text', ''))
                if not segment.get('supplier_guess'):
                    segment['supplier_guess'] = self.extract_supplier_guess(segment.get('text', ''))
            
            # Build stitch groups
            groups = self.build_stitch_groups(segments)
            
            # Sort segments within each group (if possible)
            for group in groups:
                group.segments = self.sort_segments_within_group(group.segments)
            
            logger.info(f"✅ Created {len(groups)} stitch groups from {len(segments)} segments")
            return groups
            
        except Exception as e:
            logger.error(f"Stitching failed: {e}")
            # Return individual segments as groups
            return [
                StitchGroup(
                    group_id=f"stitch_group_{i}",
                    segments=[segment],
                    confidence=1.0,
                    doc_type=segment.get('doc_type', 'other'),
                    supplier_guess=segment.get('supplier_guess', ''),
                    invoice_numbers=segment.get('invoice_numbers', []),
                    dates=segment.get('dates', []),
                    reasons=['Stitching failed']
                )
                for i, segment in enumerate(segments)
            ]
    
    def sort_segments_within_group(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sort segments within a group by page numbers or other indicators
        
        Args:
            segments: List of segments in the group
            
        Returns:
            Sorted list of segments
        """
        try:
            # Try to extract page numbers
            segment_pages = []
            for segment in segments:
                page_num = self.extract_page_number(segment.get('text', ''))
                segment_pages.append((page_num, segment))
            
            # Sort by page number
            segment_pages.sort(key=lambda x: x[0] if x[0] is not None else float('inf'))
            
            return [segment for _, segment in segment_pages]
            
        except Exception as e:
            logger.error(f"Failed to sort segments: {e}")
            return segments
    
    def extract_page_number(self, text: str) -> Optional[int]:
        """Extract page number from text"""
        patterns = [
            r'\b(?:page|p)\s*(\d+)\b',
            r'\b(\d+)\s*(?:of\s*\d+)?\s*$'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    return int(matches[0])
                except:
                    continue
        
        return None 