from typing import List, Dict, Any
import re

class UtilityProcessor:
    def parse(self, text: str) -> Dict[str, Any]:
        """Extract core fields for utility bills with 1-2 pseudo line items."""
        lines = [l.strip() for l in (text or '').splitlines() if l.strip()]
        # Attempt to capture period and totals
        period = next((l for l in lines if re.search(r"\b(period|from|to|billing)\b", l, re.I)), None)
        total_match = next((re.search(r"\btotal\b\D*(\d+(?:\.\d+)?)", l, re.I) for l in lines if re.search(r"\btotal\b", l, re.I)), None)
        total_amount = float(total_match.group(1)) if total_match else 0.0
        items: List[Dict[str, Any]] = []
        if total_amount:
            items.append({"description": period or "Charges", "quantity": 1, "unit_price": total_amount, "line_total": total_amount})
        return {"line_items": items, "total_amount": total_amount} 