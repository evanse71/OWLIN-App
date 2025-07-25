import re
from typing import Dict, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def parse_invoice_text(text: str) -> Dict:
    """
    Parse invoice text and extract structured data including VAT calculations.
    
    Args:
        text: Raw OCR text from invoice
        
    Returns:
        Dictionary containing parsed invoice data with VAT calculations
    """
    data = {}
    
    try:
        # Invoice number patterns
        invoice_patterns = [
            r"(Invoice\s+Number|Invoice\s+No|Invoice\s+#|Inv\s+No)[:\-]?\s*([\w\d\-\/]+)",
            r"(Number|No)[:\-]?\s*([\w\d\-\/]+)",
            r"INV[:\-]?\s*([\w\d\-\/]+)",
        ]
        
        # Date patterns
        date_patterns = [
            r"(Date|Invoice\s+Date)[:\-]?\s*([\d]{1,2}[\/\.-][\d]{1,2}[\/\.-][\d]{2,4})",
            r"(Date|Invoice\s+Date)[:\-]?\s*([\d]{2,4}[\/\.-][\d]{1,2}[\/\.-][\d]{1,2})",
            r"(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4})",
        ]
        
        # Supplier patterns
        supplier_patterns = [
            r"(Supplier|From|Bill\s+From|Company)[:\-]?\s*(.+?)(?:\n|$)",
            r"(To|Bill\s+To)[:\-]?\s*(.+?)(?:\n|$)",
        ]
        
        # Enhanced amount patterns for VAT calculations
        subtotal_patterns = [
            r"(Subtotal|Net\s+Amount|Total\s+excl\.?\s*VAT|Amount\s+excl\.?\s*VAT)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
            r"(Subtotal|Net)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
        ]
        
        vat_patterns = [
            r"(VAT|Tax|GST)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
            r"(VAT|Tax|GST)\s*\([^)]*\)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
        ]
        
        vat_rate_patterns = [
            r"(VAT|Tax|GST)\s*\((\d+(?:\.\d+)?)%\)",
            r"(\d+(?:\.\d+)?)%\s*(VAT|Tax|GST)",
        ]
        
        total_patterns = [
            r"(Total|Amount\s+Due|Grand\s+Total|Total\s+incl\.?\s*VAT)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
            r"(Total|Amount)[:\-]?\s*[£$€]?\s*([\d,]+\.\d{2})",
            r"[£$€]\s*([\d,]+\.\d{2})",
        ]

        # Extract invoice number
        for pattern in invoice_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data["invoice_number"] = match.group(2) if len(match.groups()) > 1 else match.group(1)
                break

        # Extract date
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                # Try to standardize date format
                try:
                    # Handle various date formats
                    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%m/%d/%Y", "%m/%d/%y", "%d-%m-%Y", "%Y-%m-%d"]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            data["invoice_date"] = parsed_date.strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    else:
                        data["invoice_date"] = date_str
                except:
                    data["invoice_date"] = date_str
                break

        # Extract supplier name
        for pattern in supplier_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                supplier = match.group(2).split("\n")[0].strip()
                # Clean up supplier name
                supplier = re.sub(r'[^\w\s\-&\.]', '', supplier)
                if len(supplier) > 2:  # Avoid very short names
                    data["supplier_name"] = supplier
                    break

        # Extract subtotal (amount excluding VAT)
        subtotal = 0.0
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amt_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                amt_str = amt_str.replace(",", "").replace("£", "").replace("$", "").replace("€", "")
                try:
                    subtotal = float(amt_str)
                    data["subtotal"] = subtotal
                    break
                except ValueError:
                    continue

        # Extract VAT amount
        vat_amount = 0.0
        for pattern in vat_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amt_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                amt_str = amt_str.replace(",", "").replace("£", "").replace("$", "").replace("€", "")
                try:
                    vat_amount = float(amt_str)
                    data["vat"] = vat_amount
                    break
                except ValueError:
                    continue

        # Extract VAT rate
        vat_rate = 0.2  # Default 20% VAT rate
        for pattern in vat_rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    rate_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                    vat_rate = float(rate_str) / 100.0
                    data["vat_rate"] = vat_rate
                    break
                except ValueError:
                    continue

        # Extract total amount
        total = 0.0
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amt_str = match.group(2) if len(match.groups()) > 1 else match.group(1)
                amt_str = amt_str.replace(",", "").replace("£", "").replace("$", "").replace("€", "")
                try:
                    total = float(amt_str)
                    data["total_amount"] = total
                    break
                except ValueError:
                    continue

        # ✅ Enhanced VAT and Total Calculations
        # Ensure all values are float
        subtotal = float(data.get("subtotal", 0))
        vat = float(data.get("vat", 0))
        total = float(data.get("total_amount", 0))
        vat_rate = float(data.get("vat_rate", 0.2))

        # Fallback: if VAT not explicitly shown, infer from subtotal and total
        if not vat and total and subtotal:
            vat = round(total - subtotal, 2)
            data["vat"] = vat

        # If total is missing, calculate it
        if not total and subtotal:
            total = round(subtotal + vat, 2)
            data["total_amount"] = total

        # If subtotal is missing but we have total and VAT
        if not subtotal and total and vat:
            subtotal = round(total - vat, 2)
            data["subtotal"] = subtotal

        # If VAT is missing but we have subtotal and total
        if not vat and subtotal and total:
            vat = round(total - subtotal, 2)
            data["vat"] = vat

        # Store calculated values
        data["subtotal"] = subtotal
        data["vat"] = vat
        data["total_incl_vat"] = total
        data["vat_rate"] = vat_rate

        # ✅ Extract and process line items
        line_items = extract_line_items_from_text(text, vat_rate)
        data["line_items"] = line_items

        # Calculate confidence based on extracted fields
        confidence = 0.0
        if data.get("invoice_number") and data.get("invoice_number") != "Unknown":
            confidence += 0.2
        if data.get("invoice_date"):
            confidence += 0.15
        if data.get("supplier_name") and data.get("supplier_name") != "Unknown":
            confidence += 0.2
        if data.get("total_amount") and data.get("total_amount") > 0:
            confidence += 0.15
        if data.get("subtotal") and data.get("subtotal") > 0:
            confidence += 0.1
        if data.get("vat") and data.get("vat") > 0:
            confidence += 0.1
        if data.get("line_items") and len(data.get("line_items", [])) > 0:
            confidence += 0.1
            
        # Ensure confidence is between 0 and 1
        data["confidence"] = max(0.1, min(1.0, confidence))

        logger.info(f"Parsed invoice data with VAT calculations: {data}")

    except Exception as e:
        logger.error(f"Error parsing invoice text: {str(e)}")
        data["confidence"] = 0.1

    return data

def extract_line_items_from_text(text: str, vat_rate: float = 0.2) -> List[Dict]:
    """
    Extract line items from invoice text with VAT calculations.
    
    Args:
        text: Raw OCR text from invoice
        vat_rate: VAT rate as decimal (e.g., 0.2 for 20%)
        
    Returns:
        List of line item dictionaries with VAT calculations
    """
    line_items = []
    
    try:
        # Split text into lines
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Look for patterns like: "Item Name    2    £45.99    £91.98"
            # or "Description    Qty    Price    Total"
            parts = line.split()
            
            if len(parts) >= 4:
                try:
                    # Try to extract quantity and prices
                    numbers = []
                    words = []
                    
                    for part in parts:
                        # Remove currency symbols and commas
                        clean_part = part.replace('£', '').replace('$', '').replace(',', '')
                        try:
                            num = float(clean_part)
                            numbers.append(num)
                        except ValueError:
                            words.append(part)
                    
                    if len(numbers) >= 2:
                        # Assume last number is total, second to last is unit price
                        line_total = numbers[-1]
                        unit_price = numbers[-2]
                        
                        # Calculate quantity
                        if unit_price > 0:
                            quantity = round(line_total / unit_price, 2)
                        else:
                            quantity = 1
                        
                        # Description is everything before the numbers
                        description = ' '.join(words)
                        
                        if description and len(description) > 2:
                            # ✅ Calculate VAT-inclusive prices
                            unit_price_excl_vat = unit_price
                            unit_price_incl_vat = round(unit_price * (1 + vat_rate), 2)
                            line_total_incl_vat = round(line_total * (1 + vat_rate), 2)
                            
                            line_items.append({
                                "description": description,
                                "quantity": quantity,
                                "unit_price_excl_vat": unit_price_excl_vat,
                                "unit_price_incl_vat": unit_price_incl_vat,
                                "line_total_excl_vat": line_total,
                                "line_total_incl_vat": line_total_incl_vat,
                                "flagged": False  # Could be enhanced with business rules
                            })
                except (ValueError, IndexError):
                    continue
        
        return line_items
        
    except Exception as e:
        logger.error(f"Error extracting line items: {str(e)}")
        return []

def extract_invoice_metadata(ocr_text: str) -> dict:
    """
    Extract invoice metadata from OCR text with VAT calculations.
    This function is used by the upload pipeline.
    
    Args:
        ocr_text: Raw OCR text from invoice
        
    Returns:
        Dictionary with extracted metadata including VAT calculations
    """
    # Use the enhanced parse_invoice_text function
    parsed_data = parse_invoice_text(ocr_text)
    
    # Return with fallback values for missing fields
    return {
        "invoice_number": parsed_data.get("invoice_number", "Unknown"),
        "supplier_name": parsed_data.get("supplier_name", "Unknown"),
        "invoice_date": parsed_data.get("invoice_date", datetime.now().strftime("%Y-%m-%d")),
        "total_amount": parsed_data.get("total_amount", 0.0),
        "subtotal": parsed_data.get("subtotal", 0.0),
        "vat": parsed_data.get("vat", 0.0),
        "vat_rate": parsed_data.get("vat_rate", 0.2),
        "total_incl_vat": parsed_data.get("total_incl_vat", 0.0),
        "line_items": parsed_data.get("line_items", []),
    } 