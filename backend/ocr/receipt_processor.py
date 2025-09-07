from typing import List, Dict, Any
import re

class ReceiptProcessor:
    def parse(self, text: str) -> List[Dict[str, Any]]:
        """
        Minimal receipt line extraction:
        - Detect lines with pattern: <desc> ... <qty> <price> <total>
        - Allow missing VAT per row
        - Return list of {description, quantity, unit_price, line_total}
        """
        items: List[Dict[str, Any]] = []
        lines = [l.strip() for l in (text or '').splitlines() if l.strip()]
        for line in lines:
            # Heuristic: numbers at end of line
            m = re.search(r"(.+?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s*$", line)
            if m:
                desc = m.group(1).strip('.- ')
                qty = float(m.group(2))
                price = float(m.group(3))
                total = float(m.group(4))
                items.append({
                    "description": desc,
                    "quantity": qty,
                    "unit_price": price,
                    "line_total": total,
                })
        return items 