from datetime import datetime, timedelta
from typing import Dict, Optional
import unicodedata

def normalize_name(name: str) -> str:
    if not name:
        return ''
    return unicodedata.normalize('NFKD', name).casefold().strip()

def parse_date(date_str: str) -> Optional[datetime]:
    # Try common date formats, fallback to None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue
    return None

def match_documents(invoice_data: Dict, delivery_data: Dict, max_days: int = 3) -> bool:
    """
    Returns True if invoice and delivery note are likely a match.
    - Supplier name similarity (normalize/casefold)
    - Date proximity (within max_days)
    - Optional: shared identifiers
    """
    inv_name = normalize_name(invoice_data.get('supplier_name', ''))
    del_name = normalize_name(delivery_data.get('supplier_name', ''))
    if not inv_name or not del_name:
        return False
    if inv_name != del_name:
        return False
    # Date proximity
    inv_date = parse_date(invoice_data.get('invoice_date', ''))
    del_date = parse_date(delivery_data.get('delivery_date', ''))
    if not inv_date or not del_date:
        return False
    if abs((inv_date - del_date).days) > max_days:
        return False
    # Optional: shared identifiers
    inv_num = invoice_data.get('invoice_number', '').strip()
    del_num = delivery_data.get('delivery_note_number', '').strip()
    if inv_num and del_num and inv_num == del_num:
        return True
    # If names and dates match, that's enough
    return True 