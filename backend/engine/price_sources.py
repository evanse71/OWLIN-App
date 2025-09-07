"""
Price Source Ladder - Trust-Weighted References
Collect and weight price references from multiple sources.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from config_units import LADDER_CONF, REF_CONFLICT_THRESHOLD


class PriceSource:
    """Represents a single price reference from a source."""
    
    def __init__(self, source: str, value: float, uom_key: str, 
                 captured_at: datetime, source_hash: str):
        self.source = source
        self.value = value
        self.uom_key = uom_key
        self.captured_at = captured_at
        self.source_hash = source_hash
        self.weight = 0.0
        self.staleness_penalty = 0.0
    
    def calculate_weight(self, reference_date: datetime) -> float:
        """Calculate weight with staleness penalty."""
        if self.source not in LADDER_CONF:
            return 0.0
        
        config = LADDER_CONF[self.source]
        base_weight = config['w']
        penalty_per_day = config['penalty_per_day']
        
        # Calculate days since capture
        days_old = (reference_date - self.captured_at).days
        staleness_penalty = penalty_per_day * days_old
        
        self.staleness_penalty = staleness_penalty
        self.weight = max(0.0, base_weight - staleness_penalty)
        
        return self.weight


class PriceSourceLadder:
    """Manages price references from multiple sources."""
    
    def __init__(self):
        self.sources: List[PriceSource] = []
        self.reference_date = datetime.now()
    
    def add_source(self, source: str, value: float, uom_key: str, 
                   captured_at: datetime, source_hash: str) -> None:
        """Add a price source to the ladder."""
        price_source = PriceSource(source, value, uom_key, captured_at, source_hash)
        price_source.calculate_weight(self.reference_date)
        self.sources.append(price_source)
    
    def get_weighted_median(self) -> Optional[float]:
        """Calculate weighted median of all sources."""
        if not self.sources:
            return None
        
        # Filter sources with positive weight
        valid_sources = [s for s in self.sources if s.weight > 0]
        if not valid_sources:
            return None
        
        # Sort by value for median calculation
        valid_sources.sort(key=lambda x: x.value)
        
        # Calculate total weight
        total_weight = sum(s.weight for s in valid_sources)
        if total_weight == 0:
            return None
        
        # Find weighted median
        cumulative_weight = 0
        target_weight = total_weight / 2
        
        for source in valid_sources:
            cumulative_weight += source.weight
            if cumulative_weight >= target_weight:
                return source.value
        
        return valid_sources[-1].value
    
    def check_reference_conflict(self) -> Tuple[bool, Optional[str]]:
        """Check if top sources diverge significantly."""
        if len(self.sources) < 2:
            return False, None
        
        # Get top two sources by weight
        sorted_sources = sorted(self.sources, key=lambda x: x.weight, reverse=True)
        top_source = sorted_sources[0]
        second_source = sorted_sources[1]
        
        if top_source.weight == 0 or second_source.weight == 0:
            return False, None
        
        # Calculate percentage difference between top two sources
        if top_source.value == 0:
            return False, None
        
        pct_diff = abs(top_source.value - second_source.value) / top_source.value
        
        # Also check if any source differs significantly from the weighted median
        weighted_median = self.get_weighted_median()
        if weighted_median:
            for source in sorted_sources[:2]:  # Check top 2 sources
                if source.value > 0:
                    median_diff = abs(source.value - weighted_median) / weighted_median
                    if median_diff > REF_CONFLICT_THRESHOLD:
                        return True, "reference_conflict"
        
        if pct_diff > REF_CONFLICT_THRESHOLD:
            return True, "reference_conflict"
        
        return False, None
    
    def get_sources_summary(self) -> Dict:
        """Get summary of all sources for debugging."""
        return {
            'total_sources': len(self.sources),
            'valid_sources': len([s for s in self.sources if s.weight > 0]),
            'weighted_median': self.get_weighted_median(),
            'has_conflict': self.check_reference_conflict()[0],
            'sources': [
                {
                    'source': s.source,
                    'value': s.value,
                    'weight': s.weight,
                    'staleness_penalty': s.staleness_penalty,
                    'captured_at': s.captured_at.isoformat()
                }
                for s in self.sources
            ]
        }


def collect_contract_book_prices(sku_id: str, supplier_id: str, 
                                reference_date: datetime) -> List[PriceSource]:
    """Collect prices from contract book."""
    # TODO: Implement contract book lookup
    # This would query the supplier_discounts table and contract data
    return []


def collect_supplier_master_prices(sku_id: str, supplier_id: str,
                                  reference_date: datetime) -> List[PriceSource]:
    """Collect prices from supplier master data."""
    # TODO: Implement supplier master lookup
    # This would query supplier catalog data
    return []


def collect_venue_memory_prices(sku_id: str, venue_id: str, 
                               reference_date: datetime) -> List[PriceSource]:
    """Collect prices from venue's 90-day memory."""
    # TODO: Implement venue memory lookup
    # This would query recent invoice history for the venue
    return []


def collect_invoice_unit_prices(invoice_id: str, line_id: str,
                               reference_date: datetime) -> List[PriceSource]:
    """Collect unit prices from the current invoice."""
    # TODO: Implement invoice unit price extraction
    # This would parse the invoice line for unit pricing
    return []


def collect_peer_sibling_prices(sku_id: str, venue_id: str,
                               reference_date: datetime) -> List[PriceSource]:
    """Collect prices from peer/sibling sites."""
    # TODO: Implement peer site lookup
    # This would query other venues in the same group
    return []


def build_price_ladder(sku_id: str, supplier_id: str, venue_id: str,
                      invoice_id: str, line_id: str, 
                      reference_date: datetime) -> PriceSourceLadder:
    """Build complete price ladder from all available sources."""
    ladder = PriceSourceLadder()
    ladder.reference_date = reference_date
    
    # Collect from all sources
    contract_sources = collect_contract_book_prices(sku_id, supplier_id, reference_date)
    master_sources = collect_supplier_master_prices(sku_id, supplier_id, reference_date)
    venue_sources = collect_venue_memory_prices(sku_id, venue_id, reference_date)
    invoice_sources = collect_invoice_unit_prices(invoice_id, line_id, reference_date)
    peer_sources = collect_peer_sibling_prices(sku_id, venue_id, reference_date)
    
    # Add all sources to ladder
    for source in contract_sources + master_sources + venue_sources + invoice_sources + peer_sources:
        ladder.add_source(source.source, source.value, source.uom_key, 
                         source.captured_at, source.source_hash)
    
    return ladder


def persist_price_sources_snapshot(ladder: PriceSourceLadder, invoice_id: str, 
                                  line_id: str, db_connection) -> None:
    """Persist price sources snapshot to database."""
    for source in ladder.sources:
        if source.weight > 0:  # Only persist valid sources
            db_connection.execute("""
                INSERT INTO price_sources_snapshot 
                (id, invoice_id, line_id, source, value, uom_key, captured_at, source_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                hashlib.sha256(f"{invoice_id}_{line_id}_{source.source}".encode()).hexdigest(),
                invoice_id,
                line_id,
                source.source,
                source.value,
                source.uom_key,
                source.captured_at.isoformat(),
                source.source_hash
            )) 