from typing import List, Dict, Any
import numpy as np
import os
import datetime
import re
import logging

logger = logging.getLogger(__name__)

Box = Dict[str, any]

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
        # Cluster by y-coordinate (rows)
        y_centers = np.array([w['top'] + w['height'] // 2 for w in ocr_words])
        y_sorted = np.argsort(y_centers)
        sorted_words = [ocr_words[i] for i in y_sorted]
        
        # Group words into rows based on y-coordinate proximity
        row_clusters = []
        current_row = []
        last_y = None
        
        for w in sorted_words:
            y = w['top'] + w['height'] // 2
            
            if last_y is None or abs(y - last_y) > 15:  # New row threshold
                if current_row:
                    row_clusters.append(current_row)
                current_row = [w]
            else:
                current_row.append(w)
            last_y = y
        
        # Don't forget the last row
        if current_row:
            row_clusters.append(current_row)
        
        # Process each row to extract columns
        table = []
        for row_words in row_clusters:
            # Sort words in row by x-coordinate
            row_words = sorted(row_words, key=lambda w: w['left'])
            
            # Group words into columns based on x-coordinate proximity
            cells = []
            current_cell = []
            last_x = None
            
            for w in row_words:
                x = w['left']
                
                if last_x is None or abs(x - last_x) > 25:  # New column threshold
                    if current_cell:
                        cells.append(' '.join([word['text'] for word in current_cell]))
                    current_cell = [w]
                else:
                    current_cell.append(w)
                last_x = x
            
            # Don't forget the last cell
            if current_cell:
                cells.append(' '.join([word['text'] for word in current_cell]))
            
            if cells:
                table.append(cells)
        
        # Log table structure for debugging
        log_table_structure(table)
        
        return table
        
    except Exception as e:
        logger.error(f"Table extraction failed: {str(e)}")
        return []

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