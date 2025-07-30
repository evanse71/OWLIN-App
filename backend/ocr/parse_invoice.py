import re
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def extract_invoice_metadata(text: str) -> Dict[str, Any]:
    """
    Extract invoice metadata from OCR text with enhanced VAT and total detection.
    
    Args:
        text: OCR text to parse
        
    Returns:
        Dictionary with invoice metadata
    """
    # Invoice number patterns
    invoice_patterns = [
        r'invoice\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'invoice\s*number\s*:?\s*([A-Z0-9\-_/]+)',
        r'inv\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'bill\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'order\s*#?\s*:?\s*([A-Z0-9\-_/]+)',
        r'reference\s*:?\s*([A-Z0-9\-_/]+)',
        r'ref\s*:?\s*([A-Z0-9\-_/]+)'
    ]
    
    # Date patterns
    date_patterns = [
        r'date\s*:?\s*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
        r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})'
    ]
    
    # ✅ Enhanced supplier patterns for better detection
    supplier_patterns = [
        # Company name patterns
        r'(?:from|supplier|vendor|company|business)\s*:?\s*([A-Za-z\s&.,\-]+(?:Ltd|Limited|Inc|Corp|Company|Brewery|Restaurant|Cafe|Bar|Pub|Store|Shop))',
        r'([A-Za-z\s&.,\-]+(?:Ltd|Limited|Inc|Corp|Company|Brewery|Restaurant|Cafe|Bar|Pub|Store|Shop))\s*(?:Ltd|Limited|Inc|Corp|Company)',
        # Generic patterns
        r'from\s*:?\s*([A-Za-z\s&.,\-]+)',
        r'supplier\s*:?\s*([A-Za-z\s&.,\-]+)',
        r'vendor\s*:?\s*([A-Za-z\s&.,\-]+)',
        r'company\s*:?\s*([A-Za-z\s&.,\-]+)',
        r'business\s*:?\s*([A-Za-z\s&.,\-]+)',
        # Invoice header patterns
        r'^([A-Za-z\s&.,\-]+)\s*invoice',
        r'invoice\s*from\s*([A-Za-z\s&.,\-]+)',
        # Address-based patterns
        r'([A-Za-z\s&.,\-]+)\s*\n\s*(?:address|street|road|lane)',
    ]
    
    # ✅ Enhanced amount patterns for better detection with fuzzy matching
    amount_patterns = [
        # Prefer gross totals (incl. VAT)
        r'total\s*(?:amount\s*)?(?:payable|due|incl\.?\s*vat|including\s*vat)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'amount\s*(?:payable|due)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'grand\s*total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'balance\s*due\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        # Fallback to any total
        r'total\s*(?:\(ex\.?\s*vat\))?\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'amount\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'[£$€]\s*([\d,]+\.?\d*)\s*$'
    ]
    
    # ✅ Enhanced VAT patterns
    vat_patterns = [
        r'vat\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'tax\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'gst\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'vat\s*20%\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'20%\s*vat\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)'
    ]
    
    # ✅ Enhanced subtotal patterns
    subtotal_patterns = [
        r'subtotal\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'sub\s*total\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'net\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)',
        r'total\s*\(ex\.?\s*vat\)\s*:?\s*[£$€]?\s*([\d,]+\.?\d*)'
    ]
    
    # VAT rate patterns
    vat_rate_patterns = [
        r'vat\s*rate\s*:?\s*(\d+(?:\.\d+)?)\s*%',
        r'(\d+(?:\.\d+)?)\s*%\s*vat',
        r'vat\s*(\d+(?:\.\d+)?)\s*%'
    ]
    
    # Extract invoice number
    invoice_number = "Unknown"
    for pattern in invoice_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            invoice_number = match.group(1).strip()
            break
    
    # Extract date
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                date_str = match.group(1).strip()
                # Try to parse the date
                if '/' in date_str:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        if len(parts[2]) == 2:
                            parts[2] = '20' + parts[2]
                        invoice_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                elif '-' in date_str:
                    parts = date_str.split('-')
                    if len(parts) == 3:
                        if len(parts[0]) == 4:  # YYYY-MM-DD
                            invoice_date = f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
                        else:  # DD-MM-YYYY
                            invoice_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                break
            except Exception as e:
                logger.debug(f"Date parsing failed: {e}")
                continue
    
    # Extract supplier name
    supplier_name = "Unknown"
    for pattern in supplier_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            supplier_name = match.group(1).strip()
            break
    
    # ✅ Enhanced amount extraction with preference for gross totals
    total_amount = 0.0
    total_found = False
    
    # First, try to find gross totals (incl. VAT)
    for i, pattern in enumerate(amount_patterns[:4]):  # First 4 patterns prefer gross
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                amount_str = match.group(1).replace(',', '')
                total_amount = float(amount_str)
                total_found = True
                logger.debug(f"Found gross total: £{total_amount} (pattern {i+1})")
                break
            except ValueError:
                continue
    
    # If no gross total found, try any total
    if not total_found:
        for pattern in amount_patterns[4:]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1).replace(',', '')
                    total_amount = float(amount_str)
                    logger.debug(f"Found fallback total: £{total_amount}")
                    break
                except ValueError:
                    continue
    
    # ✅ Enhanced VAT extraction
    vat_amount = 0.0
    for pattern in vat_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                vat_str = match.group(1).replace(',', '')
                vat_amount = float(vat_str)
                logger.debug(f"Found VAT amount: £{vat_amount}")
                break
            except ValueError:
                continue
    
    # ✅ Enhanced subtotal extraction
    subtotal = 0.0
    for pattern in subtotal_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                subtotal_str = match.group(1).replace(',', '')
                subtotal = float(subtotal_str)
                logger.debug(f"Found subtotal: £{subtotal}")
                break
            except ValueError:
                continue
    
    # Extract VAT rate
    vat_rate = 20.0  # Default UK VAT rate
    for pattern in vat_rate_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                vat_rate = float(match.group(1))
                logger.debug(f"Found VAT rate: {vat_rate}%")
                break
            except ValueError:
                continue
    
    # ✅ Improved calculation logic
    if total_amount > 0.0:
        # We have a total, calculate missing values
        if subtotal > 0.0 and vat_amount > 0.0:
            # All three values exist, verify consistency
            calculated_total = subtotal + vat_amount
            if abs(calculated_total - total_amount) < 0.01:  # Within 1p tolerance
                logger.debug("All three values consistent")
            else:
                # Prefer the total we found, recalculate others
                if total_amount > subtotal:
                    vat_amount = total_amount - subtotal
                else:
                    subtotal = total_amount - vat_amount
        elif subtotal > 0.0:
            # Have total and subtotal, calculate VAT
            vat_amount = total_amount - subtotal
        elif vat_amount > 0.0:
            # Have total and VAT, calculate subtotal
            subtotal = total_amount - vat_amount
        else:
            # Only have total, assume it's gross and calculate VAT
            vat_amount = total_amount * (vat_rate / 100)
            subtotal = total_amount - vat_amount
    elif subtotal > 0.0:
        # Only have subtotal, calculate VAT and total
        vat_amount = subtotal * (vat_rate / 100)
        total_amount = subtotal + vat_amount
    elif vat_amount > 0.0:
        # Only have VAT, calculate subtotal and total
        subtotal = vat_amount / (vat_rate / 100)
        total_amount = subtotal + vat_amount
    
    # ✅ Calculate total incl VAT (prefer the found total)
    total_incl_vat = total_amount if total_amount > 0.0 else (subtotal + vat_amount)
    
    logger.debug(f"Final values - Total: £{total_amount}, Subtotal: £{subtotal}, VAT: £{vat_amount}, Total incl VAT: £{total_incl_vat}")
    
    return {
        'invoice_number': invoice_number,
        'invoice_date': invoice_date,
        'supplier_name': supplier_name,
        'total_amount': total_amount,
        'subtotal': subtotal,
        'vat': vat_amount,
        'vat_rate': vat_rate,
        'total_incl_vat': total_incl_vat
    }

def extract_line_items(table_data: List[List[str]]) -> List[Dict[str, Any]]:
    """
    Extract line items from table data with enhanced pattern matching.
    
    Args:
        table_data: Table data as list of rows
        
    Returns:
        List of line item dictionaries
    """
    line_items = []
    
    if not table_data or len(table_data) < 2:
        return line_items
    
    # ✅ Enhanced header detection for common invoice formats
    header_keywords = [
        'qty', 'quantity', 'code', 'item', 'description', 'desc', 
        'unit', 'price', 'unit price', 'discount', 'vat', 'line', 'total',
        'amount', 'rate', 'net', 'gross'
    ]
    
    # Find header row
    header_row = None
    for i, row in enumerate(table_data):
        row_text = ' '.join(row).lower()
        if any(keyword in row_text for keyword in header_keywords):
            header_row = i
            logger.info(f"Found header row at index {i}: {row}")
            break
    
    if header_row is None:
        logger.warning("No header row found in table data")
        return line_items
    
    # ✅ Enhanced line item parsing
    for i in range(header_row + 1, len(table_data)):
        row = table_data[i]
        if len(row) < 2:
            continue
        
        # Skip total/subtotal rows
        row_text = ' '.join(row).lower()
        if any(keyword in row_text for keyword in ['total', 'subtotal', 'balance', 'due', 'grand']):
            continue
        
        # Try to extract line item data
        line_item = parse_line_item_row(row)
        if line_item and line_item.get('item'):
            line_items.append(line_item)
            logger.debug(f"Extracted line item: {line_item.get('item')} - {line_item.get('total_price')}")
    
    logger.info(f"Extracted {len(line_items)} line items from table")
    return line_items

def parse_line_item_row(row: List[str]) -> Dict[str, Any]:
    """
    Parse a single row as a line item with enhanced pattern matching.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary or None if invalid
    """
    if len(row) < 2:
        return None
    
    # ✅ Enhanced parsing strategies for invoice format
    strategies = [
        parse_enhanced_tabular_line_item,  # New enhanced strategy
        parse_tabular_line_item,
        parse_space_separated_line_item,
        parse_pattern_based_line_item
    ]
    
    for strategy in strategies:
        try:
            result = strategy(row)
            if result and result.get('item'):
                return result
        except Exception as e:
            logger.debug(f"Strategy {strategy.__name__} failed: {str(e)}")
            continue
    
    return None

def parse_tabular_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item from tabular format.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    # Look for quantity, description, unit price, total
    qty = 1.0
    description = ""
    unit_price = 0.0
    line_total = 0.0
    
    for i, cell in enumerate(row):
        cell = cell.strip()
        if not cell:
            continue
        
        # Try to identify quantity
        qty_match = re.search(r'^(\d+(?:\.\d+)?)$', cell)
        if qty_match and qty == 1.0:
            qty = float(qty_match.group(1))
            continue
        
        # Try to identify prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', cell)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            # If we have a unit price, this might be line total
            if unit_price > 0 and line_total == 0:
                line_total = price_val
            elif unit_price == 0:
                unit_price = price_val
            continue
        
        # If not quantity or price, it's description
        if not description:
            description = cell
        else:
            description += " " + cell
    
    # Calculate missing values
    if unit_price > 0 and line_total == 0:
        line_total = unit_price * qty
    elif line_total > 0 and unit_price == 0 and qty > 0:
        unit_price = line_total / qty
    
    if not description:
        description = "Unknown Item"
    
    return create_line_item_dict(
        item=description,
        quantity=qty,
        unit_price_excl_vat=unit_price,
        line_total_excl_vat=line_total,
        vat_rate=0.2
    )

def parse_space_separated_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item from space-separated format.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    # Join all cells and split by spaces
    text = ' '.join(row)
    parts = text.split()
    
    qty = 1.0
    description = ""
    unit_price = 0.0
    line_total = 0.0
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # Check for quantity (e.g., "5 x")
        if part.isdigit() and i + 1 < len(parts) and parts[i + 1].lower() in ['x', 'of', 'units']:
            qty = float(part)
            i += 2
            continue
        
        # Check for prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', part)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            if unit_price > 0 and line_total == 0:
                line_total = price_val
            elif unit_price == 0:
                unit_price = price_val
            i += 1
            continue
        
        # Add to description
        if not description:
            description = part
        else:
            description += " " + part
        i += 1
    
    # Calculate missing values
    if unit_price > 0 and line_total == 0:
        line_total = unit_price * qty
    elif line_total > 0 and unit_price == 0 and qty > 0:
        unit_price = line_total / qty
    
    if not description:
        description = "Unknown Item"
    
    return create_line_item_dict(
        item=description,
        quantity=qty,
        unit_price_excl_vat=unit_price,
        line_total_excl_vat=line_total,
        vat_rate=0.2
    )

def parse_pattern_based_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Parse line item using pattern matching.
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    text = ' '.join(row)
    
    # Pattern: "Item Name X x £Y.YY £Z.ZZ"
    pattern1 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*x\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern1, text)
    if match:
        description = match.group(1).strip()
        qty = float(match.group(2))
        unit_price = float(match.group(3).replace(',', ''))
        line_total = float(match.group(4).replace(',', ''))
        
        return create_line_item_dict(
            item=description,
            quantity=qty,
            unit_price_excl_vat=unit_price,
            line_total_excl_vat=line_total,
            vat_rate=0.2
        )
    
    # Pattern: "Item Name £Y.YY each X units £Z.ZZ"
    pattern2 = r'^(.+?)\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s+each\s+(\d+(?:\.\d+)?)\s+units\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern2, text)
    if match:
        description = match.group(1).strip()
        unit_price = float(match.group(2).replace(',', ''))
        qty = float(match.group(3))
        line_total = float(match.group(4).replace(',', ''))
        
        return create_line_item_dict(
            item=description,
            quantity=qty,
            unit_price_excl_vat=unit_price,
            line_total_excl_vat=line_total,
            vat_rate=0.2
        )
    
    return None

def parse_enhanced_tabular_line_item(row: List[str]) -> Dict[str, Any]:
    """
    Enhanced parsing for common invoice line item format:
    QTY CODE ITEM UNIT PRICE DISCOUNT VAT LINE PRICE
    
    Args:
        row: List of cell strings
        
    Returns:
        Line item dictionary
    """
    if len(row) < 3:
        return None
    
    # Clean and normalize row data
    cleaned_row = [cell.strip() for cell in row if cell.strip()]
    if len(cleaned_row) < 3:
        return None
    
    # Try to identify components based on patterns
    qty = 1.0
    code = ""
    item = ""
    unit_price = 0.0
    discount = 0.0
    vat_rate = 20.0
    line_total = 0.0
    
    # ✅ Enhanced pattern matching for invoice format
    for i, cell in enumerate(cleaned_row):
        cell_lower = cell.lower()
        
        # Quantity detection (first column often)
        if i == 0 and re.match(r'^\d+(?:\.\d+)?$', cell):
            qty = float(cell)
            continue
        
        # Code detection (alphanumeric, often second column)
        if (i == 1 or i == 0) and re.match(r'^[A-Z0-9\-_]+$', cell):
            code = cell
            continue
        
        # Price detection patterns
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', cell)
        if price_match:
            price_str = price_match.group(1).replace(',', '')
            price_value = float(price_str)
            
            # Determine which price this is based on position and context
            if 'unit' in cell_lower or 'price' in cell_lower:
                unit_price = price_value
            elif 'line' in cell_lower or 'total' in cell_lower:
                line_total = price_value
            elif 'discount' in cell_lower:
                discount = price_value
            elif 'vat' in cell_lower:
                # This might be VAT amount, not rate
                continue
            else:
                # Default to line total if no other price found
                if line_total == 0.0:
                    line_total = price_value
                elif unit_price == 0.0:
                    unit_price = price_value
        
        # VAT rate detection
        vat_match = re.search(r'(\d+(?:\.\d+)?)\s*%', cell)
        if vat_match and 'vat' in cell_lower:
            vat_rate = float(vat_match.group(1))
            continue
        
        # Item description (longest text, not a price or code)
        if (len(cell) > 3 and 
            not re.match(r'^\d+(?:\.\d+)?$', cell) and
            not re.match(r'^[A-Z0-9\-_]+$', cell) and
            not re.search(r'[£$€]?\s*\d+', cell) and
            not item):  # Only take first long text as item
            item = cell
    
    # ✅ Fallback item detection if not found
    if not item:
        # Find the longest text that's not a price or code
        for cell in cleaned_row:
            if (len(cell) > 3 and 
                not re.match(r'^\d+(?:\.\d+)?$', cell) and
                not re.match(r'^[A-Z0-9\-_]+$', cell) and
                not re.search(r'[£$€]?\s*\d+', cell)):
                item = cell
                break
    
    # ✅ Calculate missing values
    if unit_price == 0.0 and line_total > 0.0 and qty > 0.0:
        unit_price = line_total / qty
    
    if line_total == 0.0 and unit_price > 0.0 and qty > 0.0:
        line_total = unit_price * qty
    
    # ✅ Create line item if we have essential data
    if item and (unit_price > 0.0 or line_total > 0.0):
        return create_enhanced_line_item_dict(
            item=item,
            code=code,
            quantity=qty,
            unit_price_excl_vat=unit_price,
            line_total_excl_vat=line_total,
            discount=discount,
            vat_rate=vat_rate
        )
    
    return None

def create_line_item_dict(item: str, quantity: float, unit_price_excl_vat: float, 
                         line_total_excl_vat: float, vat_rate: float) -> Dict[str, Any]:
    """
    Create a standardized line item dictionary.
    
    Args:
        item: Item description
        quantity: Quantity
        unit_price_excl_vat: Unit price excluding VAT
        line_total_excl_vat: Line total excluding VAT
        vat_rate: VAT rate
        
    Returns:
        Line item dictionary
    """
    # Calculate VAT-inclusive values
    unit_price_incl_vat = unit_price_excl_vat * (1 + vat_rate)
    line_total_incl_vat = line_total_excl_vat * (1 + vat_rate)
    
    # Calculate price per unit (VAT-inclusive)
    price_per_unit = unit_price_incl_vat
    
    return {
        "item": item,
        "description": item,  # Backward compatibility
        "quantity": quantity,
        "unit_price": unit_price_excl_vat,  # Backward compatibility
        "total_price": line_total_excl_vat,  # Backward compatibility
        "unit_price_excl_vat": round(unit_price_excl_vat, 2),
        "unit_price_incl_vat": round(unit_price_incl_vat, 2),
        "line_total_excl_vat": round(line_total_excl_vat, 2),
        "line_total_incl_vat": round(line_total_incl_vat, 2),
        "price_excl_vat": round(unit_price_excl_vat, 2),
        "price_incl_vat": round(unit_price_incl_vat, 2),
        "price_per_unit": round(price_per_unit, 2),
        "vat_rate": round(vat_rate, 3),
        "line_position": 0,
        "flagged": False
    }

def create_enhanced_line_item_dict(item: str, code: str, quantity: float, unit_price_excl_vat: float, 
                                  line_total_excl_vat: float, discount: float, vat_rate: float) -> Dict[str, Any]:
    """
    Create a standardized line item dictionary for enhanced parsing.
    
    Args:
        item: Item description
        code: Item code (e.g., SKU)
        quantity: Quantity
        unit_price_excl_vat: Unit price excluding VAT
        line_total_excl_vat: Line total excluding VAT
        discount: Discount amount
        vat_rate: VAT rate
        
    Returns:
        Line item dictionary
    """
    # Calculate VAT-inclusive values
    unit_price_incl_vat = unit_price_excl_vat * (1 + vat_rate / 100)
    line_total_incl_vat = line_total_excl_vat * (1 + vat_rate / 100)
    
    # Calculate price per unit (VAT-inclusive)
    price_per_unit = unit_price_incl_vat
    
    return {
        "item": item,
        "code": code,
        "quantity": quantity,
        "unit_price_excl_vat": round(unit_price_excl_vat, 2),
        "unit_price_incl_vat": round(unit_price_incl_vat, 2),
        "line_total_excl_vat": round(line_total_excl_vat, 2),
        "line_total_incl_vat": round(line_total_incl_vat, 2),
        "discount": round(discount, 2),
        "vat_rate": round(vat_rate, 1),
        "price_per_unit": round(price_per_unit, 2),
        "line_position": 0,
        "flagged": False
    }

def calculate_confidence(parsed: Dict) -> float:
    """
    Calculate confidence score based on parsed data quality.
    
    Args:
        parsed: Parsed invoice data
        
    Returns:
        Confidence score (0-100)
    """
    confidence = 0.0
    
    # Base confidence from metadata completeness
    if parsed.get('supplier_name') and parsed.get('supplier_name') != 'Unknown':
        confidence += 20.0
    
    if parsed.get('invoice_number') and parsed.get('invoice_number') != 'Unknown':
        confidence += 15.0
    
    if parsed.get('invoice_date'):
        confidence += 10.0
    
    if parsed.get('total_amount', 0) > 0:
        confidence += 15.0
    
    if parsed.get('subtotal', 0) > 0:
        confidence += 10.0
    
    if parsed.get('vat', 0) > 0:
        confidence += 10.0
    
    # Line items bonus
    line_items = parsed.get('line_items', [])
    if line_items:
        confidence += min(len(line_items) * 5.0, 20.0)  # Max 20 points for line items
    
    # ✅ Ensure confidence is 0-100 scale
    confidence = min(max(confidence, 0.0), 100.0)
    
    return round(confidence, 1) 

def parse_invoice_text(text: str) -> Dict:
    """
    Parse invoice text and extract structured data with enhanced fallback handling.
    
    Args:
        text: Raw OCR text from invoice
        
    Returns:
        Dictionary with parsed invoice data
    """
    try:
        # Initialize with safe defaults
        parsed = {
            'supplier_name': 'Unknown',
            'invoice_number': 'Unknown',
            'invoice_date': 'Unknown',
            'total_amount': 0.0,
            'subtotal': 0.0,
            'vat': 0.0,
            'vat_rate': 20.0,
            'total_incl_vat': 0.0,
            'line_items': [],  # Always return empty list, never None
            'currency': 'GBP'
        }
        
        if not text or not text.strip():
            logger.warning("Empty text provided to parse_invoice_text")
            return parsed
        
        # Extract metadata using safe methods
        try:
            metadata = extract_invoice_metadata(text)
            if metadata:
                # Use .get() with defaults for all fields
                parsed['supplier_name'] = metadata.get('supplier_name', 'Unknown')
                parsed['invoice_number'] = metadata.get('invoice_number', 'Unknown')
                parsed['invoice_date'] = metadata.get('invoice_date', 'Unknown')
                parsed['total_amount'] = float(metadata.get('total_amount', 0))
                parsed['subtotal'] = float(metadata.get('subtotal', 0))
                parsed['vat'] = float(metadata.get('vat', 0))
                parsed['vat_rate'] = float(metadata.get('vat_rate', 20.0))
                parsed['total_incl_vat'] = float(metadata.get('total_incl_vat', 0))
                parsed['currency'] = metadata.get('currency', 'GBP')
        except Exception as metadata_error:
            logger.warning(f"Metadata extraction failed: {metadata_error}")
        
        # Extract line items with safe fallback
        try:
            line_items = extract_line_items(text)
            if line_items and isinstance(line_items, list):
                parsed['line_items'] = line_items
            else:
                parsed['line_items'] = []  # Ensure it's always a list
                logger.warning("Line items extraction returned invalid data, using empty list")
        except Exception as line_items_error:
            logger.warning(f"Line items extraction failed: {line_items_error}")
            parsed['line_items'] = []  # Ensure it's always a list
        
        # Calculate totals if missing
        if parsed['total_incl_vat'] == 0 and parsed['subtotal'] > 0 and parsed['vat'] > 0:
            parsed['total_incl_vat'] = parsed['subtotal'] + parsed['vat']
            logger.debug(f"Calculated total_incl_vat: {parsed['total_incl_vat']}")
        
        if parsed['total_amount'] == 0 and parsed['total_incl_vat'] > 0:
            parsed['total_amount'] = parsed['total_incl_vat']
            logger.debug(f"Set total_amount from total_incl_vat: {parsed['total_amount']}")
        
        if parsed['vat'] == 0 and parsed['subtotal'] > 0 and parsed['vat_rate'] > 0:
            parsed['vat'] = parsed['subtotal'] * (parsed['vat_rate'] / 100)
            logger.debug(f"Calculated VAT: {parsed['vat']}")
        
        logger.debug(f"Parsed metadata: {parsed}")
        logger.debug(f"Line items: {parsed.get('line_items', [])}")
        
        return parsed
        
    except Exception as e:
        logger.error(f"❌ parse_invoice_text failed: {e}")
        # Return safe fallback
        return {
            'supplier_name': 'Unknown',
            'invoice_number': 'Unknown',
            'invoice_date': 'Unknown',
            'total_amount': 0.0,
            'subtotal': 0.0,
            'vat': 0.0,
            'vat_rate': 20.0,
            'total_incl_vat': 0.0,
            'line_items': [],  # Always empty list, never None
            'currency': 'GBP'
        } 

def extract_line_items_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from raw OCR text using pattern matching.
    
    Args:
        text: Raw OCR text from invoice
        
    Returns:
        List of line item dictionaries
    """
    line_items = []
    
    if not text:
        return line_items
    
    # Common line item patterns
    line_patterns = [
        # Pattern: "2 x £108.50 Camden Hells 30L"
        r'(\d+)\s*x\s*[£$€]?(\d+\.?\d*)\s+([A-Za-z\s\-]+)',
        # Pattern: "Camden Hells 30L 2 £108.50"
        r'([A-Za-z\s\-]+)\s+(\d+)\s+[£$€]?(\d+\.?\d*)',
        # Pattern: "Description Qty Price Total"
        r'([A-Za-z\s\-]+)\s+(\d+)\s+[£$€]?(\d+\.?\d*)\s+[£$€]?(\d+\.?\d*)',
        # Pattern: "Item - Quantity x Price"
        r'([A-Za-z\s\-]+)\s*-\s*(\d+)\s*x\s*[£$€]?(\d+\.?\d*)',
    ]
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
            
        # Skip header lines
        if any(header in line.lower() for header in ['description', 'item', 'qty', 'quantity', 'price', 'total', 'amount']):
            continue
            
        # Try each pattern
        for pattern in line_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    if len(match.groups()) == 3:
                        # Pattern 1 or 2: quantity, price, description
                        quantity = float(match.group(1))
                        price = float(match.group(2))
                        description = match.group(3).strip()
                        total = quantity * price
                    elif len(match.groups()) == 4:
                        # Pattern 3: description, quantity, price, total
                        description = match.group(1).strip()
                        quantity = float(match.group(2))
                        price = float(match.group(3))
                        total = float(match.group(4))
                    else:
                        continue
                    
                    # Validate the line item
                    if quantity > 0 and price > 0 and description and len(description) > 2:
                        line_item = {
                            'description': description,
                            'quantity': quantity,
                            'unit_price': price,
                            'total_price': total,
                            'line_total_excl_vat': total,
                            'vat_rate': 20.0
                        }
                        line_items.append(line_item)
                        logger.debug(f"✅ Extracted line item: {description} - {quantity} x £{price}")
                        break
                        
                except (ValueError, IndexError) as e:
                    logger.debug(f"⚠️ Failed to parse line item: {line} - {e}")
                    continue
    
    logger.info(f"✅ Extracted {len(line_items)} line items from text")
    return line_items 