"""
Email Generator Module for Owlin Agent

Creates clear, pre-written email templates that GMs or Finance users can send 
to suppliers when there are issues with an invoice (e.g. short delivery, 
pricing mismatch, or missing items). These templates reduce effort and 
ensure consistency.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_supplier_email(
    supplier_name: str, 
    invoice_number: str, 
    flagged_items: list, 
    venue_name: str, 
    suggested_credits: list = []
) -> str:
    """
    Generate a professional email template for supplier communication.
    
    Args:
        supplier_name: Name of the supplier (e.g. "Brakes Catering")
        invoice_number: Invoice number (e.g. "INV-73318")
        flagged_items: List of dictionaries with item issues
        venue_name: Name of the venue (e.g. "Royal Oak Hotel")
        suggested_credits: Optional list of credit suggestions
        
    Returns:
        Formatted email body as string
    """
    logger.info(f"📧 Generating supplier email for {supplier_name} - {invoice_number}")
    
    try:
        # Create email header
        email_body = _create_email_header(supplier_name, invoice_number, venue_name)
        
        # Add introduction
        email_body += _create_introduction(flagged_items)
        
        # Add issue details
        email_body += _create_issue_details(flagged_items, suggested_credits)
        
        # Add closing
        email_body += _create_closing()
        
        # Add signature
        email_body += _create_signature(venue_name)
        
        logger.info(f"✅ Email generated successfully for {supplier_name}")
        return email_body
        
    except Exception as e:
        logger.error(f"❌ Error generating email: {e}")
        return _get_fallback_email(supplier_name, invoice_number, venue_name)

def _create_email_header(supplier_name: str, invoice_number: str, venue_name: str) -> str:
    """
    Create the email header with subject and greeting.
    
    Args:
        supplier_name: Name of the supplier
        invoice_number: Invoice number
        venue_name: Name of the venue
        
    Returns:
        Email header string
    """
    header = f"Subject: Invoice Query - {invoice_number} ({venue_name})\n\n"
    header += f"Hi {supplier_name},\n\n"
    return header

def _create_introduction(flagged_items: list) -> str:
    """
    Create the introduction paragraph.
    
    Args:
        flagged_items: List of flagged items
        
    Returns:
        Introduction string
    """
    item_count = len(flagged_items)
    
    if item_count == 1:
        intro = f"We've reviewed invoice {flagged_items[0].get('invoice_number', 'the invoice')} and found the following issue:\n\n"
    else:
        intro = f"We've reviewed the invoice and found the following {item_count} issues:\n\n"
    
    return intro

def _create_issue_details(flagged_items: list, suggested_credits: list) -> str:
    """
    Create the detailed issue list with credit suggestions.
    
    Args:
        flagged_items: List of flagged items
        suggested_credits: List of credit suggestions
        
    Returns:
        Issue details string
    """
    details = ""
    
    # Create a mapping of item names to credit suggestions
    credit_map = {}
    for credit in suggested_credits:
        item_name = credit.get('item_name', '')
        if item_name:
            credit_map[item_name.lower()] = credit
    
    for i, item in enumerate(flagged_items, 1):
        item_name = item.get('item', 'Unknown Item')
        issue = item.get('issue', 'Issue detected')
        
        # Format the issue description
        issue_description = _format_issue_description(item)
        
        # Add credit suggestion if available
        credit_text = ""
        item_key = item_name.lower()
        if item_key in credit_map:
            credit = credit_map[item_key]
            credit_amount = credit.get('credit_amount_incl_vat', 0)
            if credit_amount > 0:
                credit_text = f" → Suggested credit: £{credit_amount:.2f} incl. VAT"
        elif 'credit_amount_incl_vat' in item:
            credit_amount = item['credit_amount_incl_vat']
            if credit_amount > 0:
                credit_text = f" → Suggested credit: £{credit_amount:.2f} incl. VAT"
        
        details += f"- {item_name}: {issue_description}{credit_text}\n"
    
    return details

def _format_issue_description(item: dict) -> str:
    """
    Format the issue description based on the issue type.
    
    Args:
        item: Item dictionary with issue details
        
    Returns:
        Formatted issue description
    """
    issue = item.get('issue', '').lower()
    
    if 'short delivery' in issue or 'quantity' in issue:
        expected = item.get('quantity_expected', 0)
        received = item.get('quantity_received', 0)
        if expected and received is not None:
            return f"Short delivery (expected {expected}, received {received})"
        else:
            return "Short delivery"
    
    elif 'overcharge' in issue or 'price' in issue:
        unit_price = item.get('unit_price', 0)
        avg_price = item.get('average_price', 0)
        if unit_price and avg_price:
            return f"Price above average (charged £{unit_price:.2f}, expected ~£{avg_price:.2f})"
        else:
            return "Price above average"
    
    elif 'missing' in issue:
        return "Item not received"
    
    elif 'damaged' in issue:
        return "Item damaged"
    
    elif 'wrong item' in issue or 'incorrect' in issue:
        return "Incorrect item received"
    
    else:
        return issue

def _create_closing() -> str:
    """
    Create the closing paragraph.
    
    Returns:
        Closing string
    """
    closing = "\nPlease confirm the credit note or adjustment for these items.\n\n"
    return closing

def _create_signature(venue_name: str) -> str:
    """
    Create the email signature.
    
    Args:
        venue_name: Name of the venue
        
    Returns:
        Signature string
    """
    signature = f"Best regards,\n[User's Name]\n{venue_name}"
    return signature

def generate_credit_email(
    supplier_name: str,
    invoice_number: str,
    credit_suggestions: list,
    venue_name: str
) -> str:
    """
    Generate a credit-specific email template.
    
    Args:
        supplier_name: Name of the supplier
        invoice_number: Invoice number
        credit_suggestions: List of credit suggestions
        venue_name: Name of the venue
        
    Returns:
        Credit email body as string
    """
    logger.info(f"💰 Generating credit email for {supplier_name} - {invoice_number}")
    
    try:
        # Calculate total credit
        total_credit_excl_vat = sum(s.get('credit_amount_excl_vat', 0) for s in credit_suggestions)
        total_credit_incl_vat = sum(s.get('credit_amount_incl_vat', 0) for s in credit_suggestions)
        
        # Create email header
        email_body = f"Subject: Credit Request - {invoice_number} ({venue_name})\n\n"
        email_body += f"Hi {supplier_name},\n\n"
        
        # Add introduction
        email_body += f"Following our review of invoice {invoice_number}, we're requesting a credit for the following items:\n\n"
        
        # Add credit details
        for suggestion in credit_suggestions:
            item_name = suggestion.get('item_name', 'Unknown Item')
            reason = suggestion.get('reason', 'Issue detected')
            credit_amount = suggestion.get('credit_amount_incl_vat', 0)
            
            email_body += f"- {item_name}: {reason} → £{credit_amount:.2f} incl. VAT\n"
        
        # Add total
        email_body += f"\nTotal credit requested: £{total_credit_incl_vat:.2f} incl. VAT\n\n"
        
        # Add closing
        email_body += "Please confirm the credit note or adjustment.\n\n"
        email_body += f"Best regards,\n[User's Name]\n{venue_name}"
        
        logger.info(f"✅ Credit email generated successfully for {supplier_name}")
        return email_body
        
    except Exception as e:
        logger.error(f"❌ Error generating credit email: {e}")
        return _get_fallback_email(supplier_name, invoice_number, venue_name)

def generate_delivery_email(
    supplier_name: str,
    invoice_number: str,
    missing_items: list,
    venue_name: str
) -> str:
    """
    Generate a delivery-specific email template.
    
    Args:
        supplier_name: Name of the supplier
        invoice_number: Invoice number
        missing_items: List of missing items
        venue_name: Name of the venue
        
    Returns:
        Delivery email body as string
    """
    logger.info(f"📦 Generating delivery email for {supplier_name} - {invoice_number}")
    
    try:
        # Create email header
        email_body = f"Subject: Missing Delivery Items - {invoice_number} ({venue_name})\n\n"
        email_body += f"Hi {supplier_name},\n\n"
        
        # Add introduction
        email_body += f"We received delivery for invoice {invoice_number} but the following items were missing:\n\n"
        
        # Add missing items
        for item in missing_items:
            item_name = item.get('item', 'Unknown Item')
            quantity_expected = item.get('quantity_expected', 0)
            quantity_received = item.get('quantity_received', 0)
            
            if quantity_expected and quantity_received is not None:
                email_body += f"- {item_name}: Expected {quantity_expected}, received {quantity_received}\n"
            else:
                email_body += f"- {item_name}: Not received\n"
        
        # Add closing
        email_body += "\nPlease arrange for these items to be delivered as soon as possible.\n\n"
        email_body += f"Best regards,\n[User's Name]\n{venue_name}"
        
        logger.info(f"✅ Delivery email generated successfully for {supplier_name}")
        return email_body
        
    except Exception as e:
        logger.error(f"❌ Error generating delivery email: {e}")
        return _get_fallback_email(supplier_name, invoice_number, venue_name)

def generate_price_query_email(
    supplier_name: str,
    invoice_number: str,
    price_issues: list,
    venue_name: str
) -> str:
    """
    Generate a price query email template.
    
    Args:
        supplier_name: Name of the supplier
        invoice_number: Invoice number
        price_issues: List of price issues
        venue_name: Name of the venue
        
    Returns:
        Price query email body as string
    """
    logger.info(f"💰 Generating price query email for {supplier_name} - {invoice_number}")
    
    try:
        # Create email header
        email_body = f"Subject: Price Query - {invoice_number} ({venue_name})\n\n"
        email_body += f"Hi {supplier_name},\n\n"
        
        # Add introduction
        email_body += f"We've reviewed invoice {invoice_number} and noticed some pricing discrepancies:\n\n"
        
        # Add price issues
        for issue in price_issues:
            item_name = issue.get('item', 'Unknown Item')
            current_price = issue.get('unit_price', 0)
            expected_price = issue.get('average_price', 0)
            percentage_increase = issue.get('percentage_increase', 0)
            
            if current_price and expected_price:
                email_body += f"- {item_name}: £{current_price:.2f} (vs expected ~£{expected_price:.2f}, {percentage_increase:.1f}% increase)\n"
            else:
                email_body += f"- {item_name}: Price increase detected\n"
        
        # Add closing
        email_body += "\nCould you please confirm these prices or provide an explanation for the increases?\n\n"
        email_body += f"Best regards,\n[User's Name]\n{venue_name}"
        
        logger.info(f"✅ Price query email generated successfully for {supplier_name}")
        return email_body
        
    except Exception as e:
        logger.error(f"❌ Error generating price query email: {e}")
        return _get_fallback_email(supplier_name, invoice_number, venue_name)

def format_email_for_ui(email_body: str, email_type: str = "general") -> dict:
    """
    Format email for UI display with metadata.
    
    Args:
        email_body: Email body text
        email_type: Type of email (general, credit, delivery, price)
        
    Returns:
        Formatted dictionary for UI
    """
    # Extract subject line if present
    subject = ""
    body = email_body
    
    if email_body.startswith("Subject:"):
        lines = email_body.split('\n')
        subject = lines[0].replace("Subject: ", "")
        body = '\n'.join(lines[2:])  # Skip subject and empty line
    
    formatted = {
        "email_body": body,
        "subject": subject,
        "email_type": email_type,
        "word_count": len(body.split()),
        "line_count": len(body.split('\n')),
        "has_credits": "credit" in body.lower() or "£" in body,
        "has_prices": "price" in body.lower() or "£" in body,
        "has_delivery": "delivery" in body.lower() or "received" in body.lower(),
        "copy_text": body,
        "subject_copy_text": subject
    }
    
    return formatted

def validate_email_content(email_body: str) -> dict:
    """
    Validate email content for completeness and professionalism.
    
    Args:
        email_body: Email body text
        
    Returns:
        Validation results dictionary
    """
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": []
    }
    
    # Check for required elements
    if not email_body:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Email body is empty")
    
    if "Hi " not in email_body:
        validation_result["warnings"].append("Missing greeting")
    
    if "Best regards" not in email_body:
        validation_result["warnings"].append("Missing closing")
    
    # Check for professional tone
    unprofessional_words = ["urgent", "immediately", "asap", "problem", "error", "wrong"]
    for word in unprofessional_words:
        if word.lower() in email_body.lower():
            validation_result["warnings"].append(f"Consider replacing '{word}' with more professional language")
    
    # Check length
    word_count = len(email_body.split())
    if word_count < 20:
        validation_result["warnings"].append("Email may be too brief")
    elif word_count > 500:
        validation_result["warnings"].append("Email may be too long")
    
    # Check for currency formatting
    if "£" in email_body:
        # Check for proper currency formatting
        import re
        currency_pattern = r'£\d+\.\d{2}'
        if not re.search(currency_pattern, email_body):
            validation_result["warnings"].append("Currency amounts should be formatted as £X.XX")
    
    logger.info(f"✅ Email validation: {validation_result['is_valid']} ({len(validation_result['warnings'])} warnings)")
    return validation_result

def _get_fallback_email(supplier_name: str, invoice_number: str, venue_name: str) -> str:
    """
    Generate a fallback email when the main generation fails.
    
    Args:
        supplier_name: Name of the supplier
        invoice_number: Invoice number
        venue_name: Name of the venue
        
    Returns:
        Fallback email string
    """
    fallback = f"Subject: Invoice Query - {invoice_number} ({venue_name})\n\n"
    fallback += f"Hi {supplier_name},\n\n"
    fallback += f"We've reviewed invoice {invoice_number} and found some issues that need attention.\n\n"
    fallback += "Please contact us to discuss the details.\n\n"
    fallback += f"Best regards,\n[User's Name]\n{venue_name}"
    
    return fallback


if __name__ == "__main__":
    # Test the email generator
    logging.basicConfig(level=logging.INFO)
    
    # Test data
    supplier_name = "Brakes Catering"
    invoice_number = "INV-73318"
    venue_name = "Royal Oak Hotel"
    
    flagged_items = [
        {
            "item": "Coca-Cola 330ml",
            "issue": "Short delivery",
            "quantity_expected": 24,
            "quantity_received": 20
        },
        {
            "item": "Tomato Paste 2kg",
            "issue": "Overcharged",
            "unit_price": 4.25,
            "average_price": 3.95
        }
    ]
    
    suggested_credits = [
        {
            "item_name": "Coca-Cola 330ml",
            "credit_amount_excl_vat": 3.0,
            "credit_amount_incl_vat": 3.6,
            "reason": "Short delivery of 4 units at £0.75 each"
        },
        {
            "item_name": "Tomato Paste 2kg",
            "credit_amount_excl_vat": 0.60,
            "credit_amount_incl_vat": 0.72,
            "reason": "Price above average"
        }
    ]
    
    print("📧 Email Generator Test Results:")
    
    # Test general supplier email
    email = generate_supplier_email(supplier_name, invoice_number, flagged_items, venue_name, suggested_credits)
    print("\n1. General Supplier Email:")
    print(email)
    
    # Test credit email
    credit_email = generate_credit_email(supplier_name, invoice_number, suggested_credits, venue_name)
    print("\n2. Credit Email:")
    print(credit_email)
    
    # Test delivery email
    missing_items = [
        {
            "item": "Chicken Breast",
            "quantity_expected": 10,
            "quantity_received": 0
        }
    ]
    delivery_email = generate_delivery_email(supplier_name, invoice_number, missing_items, venue_name)
    print("\n3. Delivery Email:")
    print(delivery_email)
    
    # Test price query email
    price_issues = [
        {
            "item": "Beef Sirloin",
            "unit_price": 25.00,
            "average_price": 20.00,
            "percentage_increase": 25.0
        }
    ]
    price_email = generate_price_query_email(supplier_name, invoice_number, price_issues, venue_name)
    print("\n4. Price Query Email:")
    print(price_email)
    
    # Test formatting
    formatted = format_email_for_ui(email, "general")
    print(f"\n5. UI Formatting:")
    print(f"   Subject: {formatted['subject']}")
    print(f"   Word count: {formatted['word_count']}")
    print(f"   Has credits: {formatted['has_credits']}")
    
    # Test validation
    validation = validate_email_content(email)
    print(f"\n6. Validation:")
    print(f"   Valid: {validation['is_valid']}")
    print(f"   Warnings: {validation['warnings']}")
    
    print("\n✅ Test completed successfully") 