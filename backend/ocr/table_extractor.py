from typing import List, Dict, Any
import numpy as np
import os
import datetime
import re
import logging

logger = logging.getLogger(__name__)

Box = Dict[str, any]

# New: snap words to median column rails
def snap_to_column_rails(ocr_words: List[Box], max_cols: int = 6) -> List[List[Box]]:
    if not ocr_words:
        return []
    # Sort by y
    words = sorted(ocr_words, key=lambda w: (w['top'] + w['height'] // 2, w['left']))
    # Row clustering by Y
    rows: List[List[Box]] = []
    last_y = None
    for w in words:
        y = w['top'] + w['height'] // 2
        if last_y is None or abs(y - last_y) > 15:
            rows.append([w])
        else:
            rows[-1].append(w)
        last_y = y
    # Compute candidate rails from global X distribution
    xs = sorted([w['left'] for w in ocr_words])
    if not xs:
        return rows
    # K-medoids-ish by quantiles
    rails = []
    for k in range(1, min(max_cols, max(2, len(xs)//8)) + 1):
        # pick k quantiles
        q = [np.percentile(xs, p) for p in np.linspace(0, 100, k+2)[1:-1]]
        rails = q
    # Snap each word to nearest rail index
    snapped_rows: List[List[Box]] = []
    for row in rows:
        cols: Dict[int, List[Box]] = {}
        for w in row:
            x = w['left']
            if not rails:
                idx = 0
            else:
                idx = int(np.argmin([abs(x - r) for r in rails]))
            cols.setdefault(idx, []).append(w)
        # Build ordered row by rail index
        ordered = []
        for idx in sorted(cols.keys()):
            ordered.extend(sorted(cols[idx], key=lambda b: b['left']))
        snapped_rows.append(ordered)
    return snapped_rows

def extract_table_data(ocr_words: List[Box]) -> List[List[str]]:
    """
    Extract table data from OCR word boxes using spatial clustering.
    
    Args:
        ocr_words: List of word boxes with position data
        
    Returns:
        Table data as list of rows, each row is a list of cell strings
    """
    if not ocr_words:
        return []
    
    try:
        # Use rail snapping to stabilize columns
        snapped_rows = snap_to_column_rails(ocr_words)
        table: List[List[str]] = []
        for row_words in snapped_rows:
            # Merge contiguous words into cells by small gaps
            cells: List[str] = []
            if not row_words:
                continue
            current = row_words[0]['text']
            last_right = row_words[0]['left'] + row_words[0]['width']
            for w in row_words[1:]:
                gap = w['left'] - last_right
                if gap > 20:
                    cells.append(current.strip())
                    current = w['text']
                else:
                    current += ' ' + w['text']
                last_right = w['left'] + w['width']
            if current:
                cells.append(current.strip())
            if cells:
                table.append(cells)
        # Log for debugging
        log_table_structure(table)
        return table
        
    except Exception as e:
        logger.error(f"Table extraction failed: {str(e)}")
        return []

# Map snapped table rows to invoice line item dicts
def table_rows_to_items(table: List[List[str]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for row in table:
        if len(row) < 3:
            continue
        # Heuristic: last two numeric cells likely unit price and line total
        nums = [i for i, c in enumerate(row) if re.search(r'[£$€]?\s*\d+[.,]\d{2}$', c)]
        if len(nums) >= 2:
            unit_idx, total_idx = nums[-2], nums[-1]
            desc = ' '.join(row[:max(1, unit_idx-1)]).strip()
            # quantity likely right before unit price
            qty = None
            try:
                qty_candidate = row[unit_idx-1].strip()
                if re.match(r'^\d+(?:\.\d+)?$', qty_candidate):
                    qty = float(qty_candidate)
            except Exception:
                pass
            unit_price = float(re.sub(r'[^\d.,]', '', row[unit_idx]).replace(',', '.'))
            line_total = float(re.sub(r'[^\d.,]', '', row[total_idx]).replace(',', '.'))
            item: Dict[str, Any] = {
                'description': desc or row[0],
                'quantity': qty if qty is not None else 1.0,
                'unit_price': unit_price,
                'line_total': line_total,
            }
            # optional VAT % somewhere in row
            for cell in row:
                m = re.search(r'(\d{1,2})\s*%$', cell)
                if m:
                    try:
                        item['vat_percent'] = float(m.group(1))
                        break
                    except Exception:
                        pass
            items.append(item)
    return items

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
    
    try:
        # Split text into lines
        lines = text.split('\n')
        
        # Find line item section
        line_item_section = find_line_item_section(lines)
        
        if not line_item_section:
            logger.warning("No line item section found in text")
            return line_items
        
        # Parse each line in the section
        for line in line_item_section:
            line_item = parse_line_from_text(line)
            if line_item and line_item.get('description'):
                line_items.append(line_item)
        
        logger.info(f"Extracted {len(line_items)} line items from text")
        return line_items
        
    except Exception as e:
        logger.error(f"Line item extraction from text failed: {str(e)}")
        return []

def find_line_item_section(lines: List[str]) -> List[str]:
    """
    Find the section of text that contains line items.
    
    Args:
        lines: List of text lines
        
    Returns:
        List of lines that appear to be line items
    """
    section_start_keywords = [
        'description', 'item', 'product', 'service', 'qty', 'quantity', 
        'unit price', 'price', 'amount', 'total', 'line', 'details'
    ]
    
    section_end_keywords = [
        'subtotal', 'net total', 'total ex', 'vat', 'tax', 'grand total',
        'amount due', 'balance', 'payment', 'terms'
    ]
    
    line_items = []
    in_line_items = False
    
    for line in lines:
        line_lower = line.lower().strip()
        
        # Check if this line starts the line item section
        if not in_line_items:
            if any(keyword in line_lower for keyword in section_start_keywords):
                # Look ahead for price patterns to confirm
                price_patterns = [r'£\d+\.\d{2}', r'\$\d+\.\d{2}', r'€\d+\.\d{2}', r'\d+\.\d{2}']
                has_prices = any(re.search(pattern, line) for pattern in price_patterns)
                
                if has_prices or 'description' in line_lower or 'item' in line_lower:
                    in_line_items = True
                    continue
        
        # Check if we've reached the end of line items
        if in_line_items:
            if any(keyword in line_lower for keyword in section_end_keywords):
                break
            
            # Add line if it has meaningful content
            if line.strip() and len(line.strip()) > 3:
                line_items.append(line)
    
    return line_items

def parse_line_from_text(line: str) -> Dict[str, Any]:
    """
    Parse a single line of text into a line item.
    
    Args:
        line: Single line of text
        
    Returns:
        Line item dictionary or None if invalid
    """
    if not line or len(line.strip()) < 5:
        return None
    
    # Clean the line
    line = re.sub(r'\s+', ' ', line.strip())
    
    # Try different parsing strategies
    strategies = [
        parse_tabular_line_from_text,
        parse_space_separated_line_from_text,
        parse_pattern_based_line_from_text
    ]
    
    for strategy in strategies:
        try:
            result = strategy(line)
            if result and result.get('description'):
                return result
        except Exception as e:
            logger.debug(f"Strategy {strategy.__name__} failed for line: {line[:50]}...")
            continue
    
    return None

def parse_tabular_line_from_text(line: str) -> Dict[str, Any]:
    """
    Parse line item from tabular format in text.
    
    Args:
        line: Single line of text
        
    Returns:
        Line item dictionary
    """
    # Split by common delimiters
    delimiters = ['\t', '  ', ' | ', ' |', '| ', '|']
    parts = None
    
    for delimiter in delimiters:
        if delimiter in line:
            parts = [part.strip() for part in line.split(delimiter) if part.strip()]
            if len(parts) >= 3:  # At least description, qty, price
                break
    
    if not parts:
        # Try splitting by multiple spaces
        parts = [part.strip() for part in re.split(r'\s{2,}', line) if part.strip()]
    
    if len(parts) < 2:
        return None
    
    # Extract components
    description = ""
    quantity = 1.0
    unit_price = 0.0
    total_price = 0.0
    
    for part in parts:
        part_lower = part.lower()
        
        # Skip header/total indicators
        if any(keyword in part_lower for keyword in ['total', 'subtotal', 'vat', 'tax', 'amount']):
            continue
        
        # Try to identify quantity
        qty_match = re.search(r'^(\d+(?:\.\d+)?)$', part)
        if qty_match and quantity == 1.0:
            quantity = float(qty_match.group(1))
            continue
        
        # Try to identify prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', part)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            if unit_price == 0:
                unit_price = price_val
            elif total_price == 0:
                total_price = price_val
            continue
        
        # If not quantity or price, it's description
        if not description:
            description = part
        else:
            description += " " + part
    
    # Calculate missing values
    if unit_price > 0 and total_price == 0:
        total_price = unit_price * quantity
    elif total_price > 0 and unit_price == 0 and quantity > 0:
        unit_price = total_price / quantity
    
    if not description:
        return None
    
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "total_price": round(total_price, 2)
    }

def parse_space_separated_line_from_text(line: str) -> Dict[str, Any]:
    """
    Parse line item from space-separated format in text.
    
    Args:
        line: Single line of text
        
    Returns:
        Line item dictionary
    """
    parts = line.split()
    
    if len(parts) < 3:
        return None
    
    description = ""
    quantity = 1.0
    unit_price = 0.0
    total_price = 0.0
    
    i = 0
    while i < len(parts):
        part = parts[i]
        
        # Check for quantity (e.g., "5 x")
        if part.isdigit() and i + 1 < len(parts) and parts[i + 1].lower() in ['x', 'of', 'units']:
            quantity = float(part)
            i += 2
            continue
        
        # Check for prices
        price_match = re.search(r'[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)', part)
        if price_match:
            price_val = float(price_match.group(1).replace(',', ''))
            
            if unit_price == 0:
                unit_price = price_val
            elif total_price == 0:
                total_price = price_val
            i += 1
            continue
        
        # Add to description
        if not description:
            description = part
        else:
            description += " " + part
        i += 1
    
    # Calculate missing values
    if unit_price > 0 and total_price == 0:
        total_price = unit_price * quantity
    elif total_price > 0 and unit_price == 0 and quantity > 0:
        unit_price = total_price / quantity
    
    if not description:
        return None
    
    return {
        "description": description,
        "quantity": quantity,
        "unit_price": round(unit_price, 2),
        "total_price": round(total_price, 2)
    }

def parse_pattern_based_line_from_text(line: str) -> Dict[str, Any]:
    """
    Parse line item using pattern matching from text.
    
    Args:
        line: Single line of text
        
    Returns:
        Line item dictionary
    """
    # Pattern: "Item Name X x £Y.YY £Z.ZZ"
    pattern1 = r'^(.+?)\s+(\d+(?:\.\d+)?)\s*x\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s*[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern1, line)
    if match:
        description = match.group(1).strip()
        quantity = float(match.group(2))
        unit_price = float(match.group(3).replace(',', ''))
        total_price = float(match.group(4).replace(',', ''))
        
        return {
            "description": description,
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "total_price": round(total_price, 2)
        }
    
    # Pattern: "Item Name £Y.YY each X units £Z.ZZ"
    pattern2 = r'^(.+?)\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)\s+each\s+(\d+(?:\.\d+)?)\s+units\s+[£$€]?\s*(\d+(?:,\d+)*(?:\.\d{2})?)'
    match = re.search(pattern2, line)
    if match:
        description = match.group(1).strip()
        unit_price = float(match.group(2).replace(',', ''))
        quantity = float(match.group(3))
        total_price = float(match.group(4).replace(',', ''))
        
        return {
            "description": description,
            "quantity": quantity,
            "unit_price": round(unit_price, 2),
            "total_price": round(total_price, 2)
        }
    
    return None

def log_table_structure(table: List[List[str]]):
    """
    Log the extracted table structure for debugging.
    
    Args:
        table: Extracted table data
    """
    try:
        log_dir = 'data/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f'table_debug_{timestamp}.txt')
        
        with open(log_file, 'w') as f:
            f.write(f"Table structure extracted at {timestamp}\n")
            f.write(f"Total rows: {len(table)}\n")
            f.write("=" * 50 + "\n")
            
            for i, row in enumerate(table):
                f.write(f"Row {i+1}: {' | '.join(row)}\n")
            
            f.write("=" * 50 + "\n")
            
    except Exception as e:
        logger.error(f"Failed to log table structure: {str(e)}") 