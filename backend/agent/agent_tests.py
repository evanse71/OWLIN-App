"""
Comprehensive Test Suite for Owlin Agent

Tests all agent modules and scenarios to ensure proper functionality
and catch potential issues before deployment.
"""

import logging
import sys
import os
from typing import Dict, List, Any
from datetime import datetime

# Add current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import agent modules
from agent_core import run_owlin_agent, get_agent_info
from confidence_scoring import score_confidence
from price_checker import check_price_mismatches, get_price_summary
from delivery_pairing import check_delivery_pairing, get_delivery_summary
from summary_generator import generate_summary, get_summary_stats
from credit_suggestion_engine import suggest_credit, suggest_credit_for_quantity_mismatch, suggest_credit_for_overcharge, suggest_credit_for_missing_item, validate_credit_suggestion, format_credit_suggestion_for_ui, get_credit_summary
from email_generator import generate_supplier_email, generate_credit_email, generate_delivery_email, generate_price_query_email, format_email_for_ui, validate_email_content
from agent_memory import set_context, get_context, get_context_with_metadata, clear_context, get_all_context, set_invoice_context, get_active_invoice, set_flagged_item_context, get_flagged_item_context, set_supplier_context, get_supplier_context, set_user_role_context, get_user_role_context, add_conversation_history, get_conversation_history, set_workflow_state, get_workflow_state, clear_workflow_state, set_preference, get_preference, get_all_preferences, set_temporary_context, cleanup_expired_context, get_memory_stats, export_user_context, import_user_context, clear_all_memory
from supplier_scoring import calculate_supplier_scores, get_supplier_summary, get_supplier_recommendations
from role_aware_suggestions import get_role_aware_suggestions, format_suggestions_for_ui, get_suggestion_priority
from matching_explainer import explain_match_status, get_match_confidence_level, format_match_summary
from role_comment_helper import get_role_comment, get_action_permissions, get_available_actions, get_restricted_actions, format_comment_for_ui

logger = logging.getLogger(__name__)

class OwlinAgentTester:
    """
    Comprehensive test suite for the Owlin Agent.
    """
    
    def __init__(self):
        """Initialize the test suite."""
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        
    def run_all_tests(self) -> bool:
        """
        Run all tests and return overall success.
        
        Returns:
            True if all tests pass, False otherwise
        """
        logger.info("🧪 Starting Owlin Agent Test Suite")
        logger.info("=" * 50)
        
        # Test individual modules
        self._test_confidence_scoring()
        self._test_price_checker()
        self._test_delivery_pairing()
        self._test_summary_generator()
        self._test_credit_suggestion_engine()
        self._test_supplier_scoring()
        self._test_role_aware_suggestions()
        self._test_matching_explainer()
        self._test_role_comment_helper()
        self._test_email_generator()
        self._test_agent_memory()
        
        # Test integration scenarios
        self._test_integration_scenarios()
        
        # Test edge cases
        self._test_edge_cases()
        
        # Test error handling
        self._test_error_handling()
        
        # Print results
        self._print_results()
        
        return self.failed_tests == 0
    
    def _test_confidence_scoring(self):
        """Test confidence scoring module."""
        logger.info("📊 Testing Confidence Scoring Module")
        
        # Test 1: Good invoice
        good_metadata = {
            "supplier_name": "Quality Foods Ltd",
            "invoice_number": "INV-2024-001",
            "invoice_date": "2024-12-01",
            "total_amount": 150.00,
            "subtotal": 125.00,
            "vat": 25.00,
            "vat_rate": 20.0
        }
        
        good_line_items = [
            {
                "item": "Beef Sirloin",
                "quantity": 5.0,
                "unit_price_excl_vat": 20.00,
                "line_total_excl_vat": 100.00
            },
            {
                "item": "Chicken Breast",
                "quantity": 2.5,
                "unit_price_excl_vat": 10.00,
                "line_total_excl_vat": 25.00
            }
        ]
        
        result = score_confidence(good_metadata, good_line_items, 85.0)
        self._assert_test(
            "Good invoice confidence scoring",
            result['score'] > 65.0 and result['manual_review_required'] == False,
            f"Expected score > 65, got {result['score']}"
        )
        
        # Test 2: Poor invoice
        poor_metadata = {
            "supplier_name": "Unknown",
            "invoice_number": "Unknown",
            "invoice_date": "",
            "total_amount": 0.0,
            "subtotal": 0.0,
            "vat": 0.0,
            "vat_rate": 0.0
        }
        
        poor_line_items = []
        
        result = score_confidence(poor_metadata, poor_line_items, 25.0)
        self._assert_test(
            "Poor invoice confidence scoring",
            result['score'] < 30.0 and result['manual_review_required'] == True,
            f"Expected score < 30, got {result['score']}"
        )
    
    def _test_price_checker(self):
        """Test price checker module."""
        logger.info("💰 Testing Price Checker Module")
        
        # Sample line items
        line_items = [
            {
                "item": "Beef Sirloin",
                "quantity": 5.0,
                "unit_price_excl_vat": 22.00,  # Increased price
                "line_total_excl_vat": 110.00
            },
            {
                "item": "Chicken Breast",
                "quantity": 2.5,
                "unit_price_excl_vat": 8.50,   # Decreased price
                "line_total_excl_vat": 21.25
            }
        ]
        
        # Sample historical prices
        historical_prices = {
            "Beef Sirloin": [18.50, 19.00, 20.50, 21.00, 20.00],  # Average: 19.80
            "Chicken Breast": [9.50, 10.00, 10.50, 11.00, 10.25], # Average: 10.25
        }
        
        # Test price mismatch detection
        flags = check_price_mismatches(line_items, historical_prices)
        self._assert_test(
            "Price mismatch detection",
            len(flags) > 0,
            f"Expected price flags, got {len(flags)}"
        )
        
        # Test price summary
        summary = get_price_summary(line_items, historical_prices)
        self._assert_test(
            "Price summary generation",
            summary['items_checked'] == 2 and summary['items_with_history'] == 2,
            f"Expected 2 items checked with history, got {summary['items_checked']}/{summary['items_with_history']}"
        )
    
    def _test_delivery_pairing(self):
        """Test delivery pairing module."""
        logger.info("📦 Testing Delivery Pairing Module")
        
        # Test case 1: Missing delivery note for perishable goods
        line_items = [
            {
                "item": "Beef Sirloin",
                "quantity": 5.0,
                "unit_price_excl_vat": 20.00,
                "line_total_excl_vat": 100.00
            },
            {
                "item": "Fresh Vegetables",
                "quantity": 10.0,
                "unit_price_excl_vat": 2.50,
                "line_total_excl_vat": 25.00
            }
        ]
        
        metadata = {
            "supplier_name": "Quality Foods Ltd",
            "invoice_date": "2024-12-01",
            "total_amount": 150.00
        }
        
        flags = check_delivery_pairing(False, line_items, metadata)
        self._assert_test(
            "Missing delivery note detection",
            len(flags) > 0,
            f"Expected delivery flags, got {len(flags)}"
        )
        
        # Test delivery summary
        summary = get_delivery_summary(False, line_items, metadata)
        self._assert_test(
            "Delivery summary generation",
            summary['should_have_delivery'] == True and summary['delivery_missing'] == True,
            f"Expected delivery required and missing, got {summary['should_have_delivery']}/{summary['delivery_missing']}"
        )
    
    def _test_summary_generator(self):
        """Test summary generator module."""
        logger.info("📝 Testing Summary Generator Module")
        
        # Sample flags
        flags = [
            {
                "type": "missing_delivery_note",
                "severity": "warning",
                "field": "delivery_note",
                "message": "No delivery note found for this invoice",
                "suggested_action": "Request delivery note from supplier"
            },
            {
                "type": "critical_price_increase",
                "severity": "critical",
                "field": "line_items[0].unit_price",
                "message": "Critical price increase: Beef Sirloin is 25.0% above average",
                "suggested_action": "Contact supplier immediately"
            }
        ]
        
        metadata = {
            "supplier_name": "Quality Foods Ltd",
            "invoice_date": "2024-12-01",
            "total_amount": 150.00
        }
        
        line_items = [
            {
                "item": "Beef Sirloin",
                "quantity": 5.0,
                "unit_price_excl_vat": 20.00,
                "line_total_excl_vat": 100.00
            }
        ]
        
        # Test summary generation
        summary = generate_summary(flags, 65.0, metadata, line_items)
        self._assert_test(
            "Summary generation",
            len(summary) > 0,
            f"Expected summary messages, got {len(summary)}"
        )
        
        # Test summary stats
        stats = get_summary_stats(flags)
        self._assert_test(
            "Summary statistics",
            stats['total_flags'] == 2 and stats['critical_flags'] == 1 and stats['warning_flags'] == 1,
            f"Expected 2 total flags (1 critical, 1 warning), got {stats['total_flags']} ({stats['critical_flags']} critical, {stats['warning_flags']} warning)"
        )
    
    def _test_credit_suggestion_engine(self):
        """Test credit suggestion engine module."""
        logger.info("💳 Testing Credit Suggestion Engine Module")
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Short Delivery",
                "item": {
                    "item": "Coca-Cola 330ml",
                    "quantity_expected": 24,
                    "quantity_received": 20,
                    "unit_price_excl_vat": 0.75,
                    "vat_rate": 20.0
                },
                "pricing_history": [0.70, 0.72, 0.74, 0.75]
            },
            {
                "name": "Overcharge",
                "item": {
                    "item": "Beef Sirloin",
                    "quantity_expected": 5,
                    "quantity_received": 5,
                    "unit_price_excl_vat": 25.00,
                    "vat_rate": 20.0
                },
                "pricing_history": [18.50, 19.00, 20.50, 21.00, 20.00]
            },
            {
                "name": "Missing Item",
                "item": {
                    "item": "Chicken Breast",
                    "quantity_expected": 10,
                    "quantity_received": 0,
                    "unit_price_excl_vat": 12.00,
                    "vat_rate": 20.0
                },
                "pricing_history": [11.50, 12.00, 12.50]
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            # Test basic credit suggestion
            suggestion = suggest_credit(scenario['item'], scenario['pricing_history'])
            self._assert_test(
                f"Credit suggestion for {scenario['name']}",
                suggestion['credit_amount_excl_vat'] >= 0,
                f"Expected non-negative credit amount for {scenario['name']}, got {suggestion['credit_amount_excl_vat']}"
            )
            
            # Test validation
            validation = validate_credit_suggestion(suggestion)
            self._assert_test(
                f"Credit validation for {scenario['name']}",
                validation['is_valid'] == True,
                f"Expected valid credit suggestion for {scenario['name']}, got {validation['is_valid']}"
            )
            
            # Test UI formatting
            formatted = format_credit_suggestion_for_ui(suggestion)
            self._assert_test(
                f"Credit UI formatting for {scenario['name']}",
                'display_color' in formatted and 'copy_text' in formatted,
                f"Expected formatted credit suggestion for {scenario['name']}, got {list(formatted.keys())}"
            )
            
            # Test specific functions
            if scenario['name'] == "Short Delivery":
                quantity_suggestion = suggest_credit_for_quantity_mismatch(
                    scenario['item'], 24, 20
                )
                self._assert_test(
                    f"Quantity mismatch credit for {scenario['name']}",
                    quantity_suggestion['credit_amount_excl_vat'] > 0,
                    f"Expected positive credit for quantity mismatch, got {quantity_suggestion['credit_amount_excl_vat']}"
                )
            
            elif scenario['name'] == "Overcharge":
                overcharge_suggestion = suggest_credit_for_overcharge(
                    scenario['item'], scenario['pricing_history']
                )
                self._assert_test(
                    f"Overcharge credit for {scenario['name']}",
                    overcharge_suggestion['credit_amount_excl_vat'] > 0,
                    f"Expected positive credit for overcharge, got {overcharge_suggestion['credit_amount_excl_vat']}"
                )
            
            elif scenario['name'] == "Missing Item":
                missing_suggestion = suggest_credit_for_missing_item(scenario['item'])
                self._assert_test(
                    f"Missing item credit for {scenario['name']}",
                    missing_suggestion['credit_amount_excl_vat'] > 0,
                    f"Expected positive credit for missing item, got {missing_suggestion['credit_amount_excl_vat']}"
                )
        
        # Test summary
        all_suggestions = [
            suggest_credit(scenario['item'], scenario['pricing_history'])
            for scenario in test_scenarios
        ]
        
        summary = get_credit_summary(all_suggestions)
        self._assert_test(
            "Credit summary generation",
            summary['total_suggestions'] == 3 and summary['total_credit_excl_vat'] > 0,
            f"Expected 3 suggestions and positive total credit, got {summary['total_suggestions']}/{summary['total_credit_excl_vat']}"
        )
    
    def _test_supplier_scoring(self):
        """Test supplier scoring module."""
        logger.info("🏭 Testing Supplier Scoring Module")
        
        # Create test database connection
        import tempfile
        import os
        import sqlite3
        
        # Create temporary database for testing
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        try:
            conn = sqlite3.connect(temp_db.name)
            
            # Create test tables
            conn.execute("""
                CREATE TABLE invoices (
                    invoice_id TEXT PRIMARY KEY,
                    supplier_name TEXT,
                    invoice_date TEXT,
                    total_amount REAL,
                    delivery_note_attached INTEGER,
                    confidence REAL,
                    created_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE invoice_mismatches (
                    id INTEGER PRIMARY KEY,
                    invoice_id TEXT,
                    item_name TEXT,
                    mismatch_type TEXT,
                    confidence_score REAL,
                    detection_timestamp TEXT
                )
            """)
            
            # Insert test data
            test_invoices = [
                ("INV-TEST-001", "Bidfood", "2024-12-01", 150.00, 1, 85.0, "2024-12-01"),
                ("INV-TEST-002", "Bidfood", "2024-12-02", 200.00, 0, 90.0, "2024-12-02"),
                ("INV-TEST-003", "Sysco", "2024-12-01", 300.00, 1, 92.0, "2024-12-01"),
            ]
            
            test_mismatches = [
                (1, "INV-TEST-001", "Beef Sirloin", "overcharge", 85.0, "2024-12-01"),
                (2, "INV-TEST-002", "Chicken Breast", "missing_item", 90.0, "2024-12-02"),
            ]
            
            for invoice in test_invoices:
                conn.execute("""
                    INSERT INTO invoices (
                        invoice_id, supplier_name, invoice_date, total_amount,
                        delivery_note_attached, confidence, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, invoice)
            
            for mismatch in test_mismatches:
                conn.execute("""
                    INSERT INTO invoice_mismatches (
                        id, invoice_id, item_name, mismatch_type, confidence_score, detection_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, mismatch)
            
            conn.commit()
            
            # Test supplier scores
            scores = calculate_supplier_scores(conn)
            self._assert_test(
                "Supplier scoring generation",
                len(scores) == 2,
                f"Expected 2 supplier scores, got {len(scores)}"
            )
            
            # Test supplier summary
            summary = get_supplier_summary(scores)
            self._assert_test(
                "Supplier summary generation",
                summary['total_suppliers'] == 2 and summary['average_score'] > 0,
                f"Expected 2 suppliers and positive average score, got {summary['total_suppliers']}/{summary['average_score']}"
            )
            
            # Test supplier recommendations
            recommendations = get_supplier_recommendations(scores)
            self._assert_test(
                "Supplier recommendations generation",
                len(recommendations) >= 0,  # May or may not have recommendations
                f"Expected recommendations list, got {len(recommendations)}"
            )
            
            conn.close()
            
        finally:
            # Clean up
            os.unlink(temp_db.name)
    
    def _test_role_aware_suggestions(self):
        """Test role-aware suggestions module."""
        logger.info("👥 Testing Role-Aware Suggestions Module")
        
        # Test scenarios
        test_scenarios = [
            {
                "user_role": "Finance",
                "document_status": "needs_review",
                "confidence": 65.0,
                "flagged_issues": [
                    {
                        "type": "price_increase",
                        "severity": "warning",
                        "field": "line_items[0].unit_price",
                        "message": "Price increased 25% above average"
                    },
                    {
                        "type": "missing_delivery_note",
                        "severity": "warning",
                        "field": "delivery_note",
                        "message": "No delivery note found"
                    }
                ]
            },
            {
                "user_role": "Shift Lead",
                "document_status": "scanned",
                "confidence": 85.0,
                "flagged_issues": [
                    {
                        "type": "missing_delivery_note",
                        "severity": "warning",
                        "field": "delivery_note",
                        "message": "No delivery note found"
                    }
                ]
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            # Test role-aware suggestions
            suggestions = get_role_aware_suggestions(
                scenario['user_role'],
                scenario['document_status'],
                scenario['confidence'],
                scenario['flagged_issues']
            )
            
            self._assert_test(
                f"Role-aware suggestions for {scenario['user_role']}",
                len(suggestions) > 0,
                f"Expected suggestions for {scenario['user_role']}, got {len(suggestions)}"
            )
            
            # Test suggestion formatting
            formatted_suggestions = format_suggestions_for_ui(suggestions)
            self._assert_test(
                f"Suggestion formatting for {scenario['user_role']}",
                len(formatted_suggestions) > 0,
                f"Expected formatted suggestions for {scenario['user_role']}, got {len(formatted_suggestions)}"
            )
            
            # Test suggestion priority
            if suggestions:
                priority = get_suggestion_priority(suggestions[0])
                self._assert_test(
                    f"Suggestion priority for {scenario['user_role']}",
                    priority in [1, 2, 3],
                    f"Expected valid priority (1-3), got {priority}"
                )
    
    def _test_matching_explainer(self):
        """Test matching explainer module."""
        logger.info("🔍 Testing Matching Explainer Module")
        
        # Test scenarios
        test_scenarios = [
            {
                "name": "Successful Match",
                "invoice_data": {
                    "invoice_number": "INV-02341",
                    "supplier_name": "Bidfood",
                    "invoice_date": "2025-07-20",
                    "total_amount": 146.75,
                    "total_items": 12
                },
                "delivery_data": {
                    "delivery_note_number": "DN-9871",
                    "supplier_name": "Bidfood",
                    "delivery_date": "2025-07-20",
                    "total_amount": 145.50,
                    "total_items": 13
                },
                "match_score": 0.92,
                "threshold": 0.85
            },
            {
                "name": "Unsuccessful Match",
                "invoice_data": {
                    "invoice_number": "INV-02341",
                    "supplier_name": "Bidfood",
                    "invoice_date": "2025-07-20",
                    "total_amount": 146.75,
                    "total_items": 12
                },
                "delivery_data": {
                    "delivery_note_number": "DN-9871",
                    "supplier_name": "Bidfood",
                    "delivery_date": "2025-07-19",
                    "total_amount": 138.75,
                    "total_items": 10
                },
                "match_score": 0.68,
                "threshold": 0.85
            }
        ]
        
        for i, scenario in enumerate(test_scenarios, 1):
            # Test explain_match_status
            explanation = explain_match_status(
                scenario['invoice_data'],
                scenario['delivery_data'],
                scenario['match_score'],
                scenario['threshold']
            )
            
            self._assert_test(
                f"Match explanation for {scenario['name']}",
                len(explanation) > 0,
                f"Expected explanation for {scenario['name']}, got {len(explanation)}"
            )
            
            # Test get_match_confidence_level
            confidence_level = get_match_confidence_level(scenario['match_score'])
            self._assert_test(
                f"Match confidence level for {scenario['name']}",
                confidence_level in ["Very High", "High", "Medium", "Low", "Very Low"],
                f"Expected valid confidence level, got {confidence_level}"
            )
            
            # Test format_match_summary
            summary = format_match_summary(
                scenario['invoice_data'],
                scenario['delivery_data'],
                scenario['match_score']
            )
            self._assert_test(
                f"Match summary formatting for {scenario['name']}",
                len(summary) > 0,
                f"Expected formatted summary for {scenario['name']}, got {len(summary)}"
            )
    
    def _test_role_comment_helper(self):
        """Test role comment helper module."""
        logger.info("💬 Testing Role Comment Helper Module")
        
        # Test scenarios
        test_scenarios = [
            ("Shift Lead", "quantity_mismatch", "pending"),
            ("Finance", "price_mismatch", "escalated"),
            ("GM", "delivery_missing", "pending"),
            ("Shift Lead", "item_not_received", "flagged"),
            ("Finance", "unexpected_item", "resolved"),
            ("GM", "quantity_mismatch", "escalated")
        ]
        
        for i, (role, issue_type, item_status) in enumerate(test_scenarios, 1):
            # Test get_role_comment
            comment = get_role_comment(role, issue_type, item_status)
            self._assert_test(
                f"Role comment for {role} - {issue_type} ({item_status})",
                len(comment) > 0,
                f"Expected non-empty comment for {role}, got length {len(comment)}"
            )
            
            # Test get_action_permissions
            permissions = get_action_permissions(role, issue_type, item_status)
            self._assert_test(
                f"Action permissions for {role} - {issue_type} ({item_status})",
                len(permissions) > 0,
                f"Expected action permissions for {role}, got {len(permissions)}"
            )
            
            # Test get_available_actions
            available_actions = get_available_actions(role, issue_type, item_status)
            self._assert_test(
                f"Available actions for {role} - {issue_type} ({item_status})",
                isinstance(available_actions, list),
                f"Expected list of available actions for {role}, got {type(available_actions)}"
            )
            
            # Test get_restricted_actions
            restricted_actions = get_restricted_actions(role, issue_type, item_status)
            self._assert_test(
                f"Restricted actions for {role} - {issue_type} ({item_status})",
                isinstance(restricted_actions, list),
                f"Expected list of restricted actions for {role}, got {type(restricted_actions)}"
            )
            
            # Test format_comment_for_ui
            formatted_comment = format_comment_for_ui(comment, role, issue_type, item_status)
            self._assert_test(
                f"Comment formatting for {role} - {issue_type} ({item_status})",
                len(formatted_comment) > 0 and "comment" in formatted_comment,
                f"Expected formatted comment with metadata for {role}, got {len(formatted_comment)}"
            )
    
    def _test_email_generator(self):
        """Test email generator module."""
        logger.info("📧 Testing Email Generator Module")
        
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
        
        missing_items = [
            {
                "item": "Chicken Breast",
                "quantity_expected": 10,
                "quantity_received": 0
            }
        ]
        
        price_issues = [
            {
                "item": "Beef Sirloin",
                "unit_price": 25.00,
                "average_price": 20.00,
                "percentage_increase": 25.0
            }
        ]
        
        # Test generate_supplier_email
        email = generate_supplier_email(supplier_name, invoice_number, flagged_items, venue_name, suggested_credits)
        self._assert_test(
            "Supplier email generation",
            len(email) > 0 and "Hi Brakes Catering" in email,
            f"Expected non-empty email with greeting, got length {len(email)}"
        )
        
        # Test validate_email_content
        validation = validate_email_content(email)
        self._assert_test(
            "Email content validation",
            validation['is_valid'] == True,
            f"Expected valid email content, got {validation['is_valid']}"
        )
        
        # Test format_email_for_ui
        formatted = format_email_for_ui(email, "general")
        self._assert_test(
            "Email formatting for UI",
            'subject' in formatted and 'email_body' in formatted,
            f"Expected formatted email with subject and body, got {list(formatted.keys())}"
        )
        
        # Test generate_credit_email
        credit_email = generate_credit_email(supplier_name, invoice_number, suggested_credits, venue_name)
        self._assert_test(
            "Credit email generation",
            len(credit_email) > 0 and "Credit Request" in credit_email,
            f"Expected non-empty credit email, got length {len(credit_email)}"
        )
        
        # Test validate_email_content for credit email
        credit_validation = validate_email_content(credit_email)
        self._assert_test(
            "Credit email content validation",
            credit_validation['is_valid'] == True,
            f"Expected valid credit email content, got {credit_validation['is_valid']}"
        )
        
        # Test generate_delivery_email
        delivery_email = generate_delivery_email(supplier_name, invoice_number, missing_items, venue_name)
        self._assert_test(
            "Delivery email generation",
            len(delivery_email) > 0 and "Missing Delivery Items" in delivery_email,
            f"Expected non-empty delivery email, got length {len(delivery_email)}"
        )
        
        # Test validate_email_content for delivery email
        delivery_validation = validate_email_content(delivery_email)
        self._assert_test(
            "Delivery email content validation",
            delivery_validation['is_valid'] == True,
            f"Expected valid delivery email content, got {delivery_validation['is_valid']}"
        )
        
        # Test generate_price_query_email
        price_email = generate_price_query_email(supplier_name, invoice_number, price_issues, venue_name)
        self._assert_test(
            "Price query email generation",
            len(price_email) > 0 and "Price Query" in price_email,
            f"Expected non-empty price query email, got length {len(price_email)}"
        )
        
        # Test validate_email_content for price query email
        price_validation = validate_email_content(price_email)
        self._assert_test(
            "Price query email content validation",
            price_validation['is_valid'] == True,
            f"Expected valid price query email content, got {price_validation['is_valid']}"
        )
    
    def _test_agent_memory(self):
        """Test agent memory module."""
        logger.info("🧠 Testing Agent Memory Module")
        
        # Test data
        user_id = "test_user_1"
        
        # Test 1: Basic context operations
        set_context(user_id, "test_key", "test_value")
        retrieved_value = get_context(user_id, "test_key")
        self._assert_test(
            "Set and get context",
            retrieved_value == "test_value",
            f"Expected 'test_value', got {retrieved_value}"
        )
        
        # Test 2: Get context with metadata
        context_with_meta = get_context_with_metadata(user_id, "test_key")
        self._assert_test(
            "Get context with metadata",
            context_with_meta is not None and "value" in context_with_meta,
            f"Expected context with metadata, got {context_with_meta}"
        )
        
        # Test 3: Clear specific context
        clear_context(user_id, "test_key")
        cleared_value = get_context(user_id, "test_key")
        self._assert_test(
            "Clear specific context",
            cleared_value is None,
            f"Expected None after clearing, got {cleared_value}"
        )
        
        # Test 4: Get all context
        set_context(user_id, "key1", "value1")
        set_context(user_id, "key2", "value2")
        all_context = get_all_context(user_id)
        self._assert_test(
            "Get all context",
            len(all_context) >= 2,
            f"Expected at least 2 context items, got {len(all_context)}"
        )
        
        # Test 5: Invoice context
        invoice_data = {
            "supplier_name": "Brakes Catering",
            "total_amount": 146.75,
            "flagged_items": 2
        }
        set_invoice_context(user_id, "INV-73318", invoice_data)
        active_invoice = get_active_invoice(user_id)
        self._assert_test(
            "Set and get invoice context",
            active_invoice == "INV-73318",
            f"Expected 'INV-73318', got {active_invoice}"
        )
        
        # Test 6: Flagged item context
        flagged_item = {
            "item": "Coca-Cola 330ml",
            "issue": "Short delivery",
            "quantity_expected": 24,
            "quantity_received": 20
        }
        set_flagged_item_context(user_id, flagged_item)
        current_item = get_flagged_item_context(user_id)
        self._assert_test(
            "Set and get flagged item context",
            current_item is not None and current_item.get("item") == "Coca-Cola 330ml",
            f"Expected flagged item data, got {current_item}"
        )
        
        # Test 7: Supplier context
        supplier_data = {
            "name": "Bidfood",
            "rating": 4.5,
            "total_invoices": 25
        }
        set_supplier_context(user_id, "Bidfood", supplier_data)
        supplier = get_supplier_context(user_id)
        self._assert_test(
            "Set and get supplier context",
            supplier == "Bidfood",
            f"Expected 'Bidfood', got {supplier}"
        )
        
        # Test 8: User role context
        set_user_role_context(user_id, "Finance")
        role = get_user_role_context(user_id)
        self._assert_test(
            "Set and get user role context",
            role == "Finance",
            f"Expected 'Finance', got {role}"
        )
        
        # Test 9: Conversation history
        add_conversation_history(user_id, "What should I do about this invoice?")
        history = get_conversation_history(user_id)
        self._assert_test(
            "Add and get conversation history",
            len(history) == 1,
            f"Expected 1 conversation entry, got {len(history)}"
        )
        
        # Test 10: Workflow state
        workflow_data = {"current_step": 1, "total_steps": 3}
        set_workflow_state(user_id, "invoice_review", "reviewing_flagged_items", workflow_data)
        workflow = get_workflow_state(user_id)
        self._assert_test(
            "Set and get workflow state",
            workflow is not None and workflow.get("workflow") == "invoice_review",
            f"Expected workflow state, got {workflow}"
        )
        
        # Test 11: Clear workflow state
        clear_workflow_state(user_id)
        cleared_workflow = get_workflow_state(user_id)
        self._assert_test(
            "Clear workflow state",
            cleared_workflow is None,
            f"Expected None after clearing workflow, got {cleared_workflow}"
        )
        
        # Test 12: User preferences
        set_preference(user_id, "email_templates", True)
        set_preference(user_id, "auto_suggestions", False)
        email_templates = get_preference(user_id, "email_templates", False)
        self._assert_test(
            "Set and get preferences",
            email_templates == True,
            f"Expected True for email_templates, got {email_templates}"
        )
        
        # Test 13: Get all preferences
        all_preferences = get_all_preferences(user_id)
        self._assert_test(
            "Get all preferences",
            len(all_preferences) >= 2,
            f"Expected at least 2 preferences, got {len(all_preferences)}"
        )
        
        # Test 14: Temporary context
        set_temporary_context(user_id, "temp_analysis", {"confidence": 85.0}, 60)
        temp_data = get_context(user_id, "temp_analysis")
        self._assert_test(
            "Set temporary context",
            temp_data is not None,
            f"Expected temporary context data, got {temp_data}"
        )
        
        # Test 15: Memory stats
        stats = get_memory_stats()
        self._assert_test(
            "Get memory stats",
            isinstance(stats, dict) and "total_users" in stats,
            f"Expected memory stats dict, got {stats}"
        )
        
        # Test 16: Export user context
        export_data = export_user_context(user_id)
        self._assert_test(
            "Export user context",
            isinstance(export_data, dict) and "user_id" in export_data,
            f"Expected export data dict, got {export_data}"
        )
        
        # Test 17: Import user context
        import_success = import_user_context(user_id, export_data)
        self._assert_test(
            "Import user context",
            import_success == True,
            f"Expected successful import, got {import_success}"
        )
        
        # Test 18: Cleanup expired context
        removed_count = cleanup_expired_context()
        self._assert_test(
            "Cleanup expired context",
            isinstance(removed_count, int),
            f"Expected integer count of removed items, got {removed_count}"
        )
        
        # Test 19: Clear all memory
        clear_all_memory()
        all_context_after_clear = get_all_context(user_id)
        self._assert_test(
            "Clear all memory",
            len(all_context_after_clear) == 0,
            f"Expected empty context after clearing all memory, got {len(all_context_after_clear)} items"
        )
    
    def _test_integration_scenarios(self):
        """Test integration scenarios."""
        logger.info("🔗 Testing Integration Scenarios")
        
        # Scenario 1: High-confidence invoice with price increases
        invoice_data = {
            "metadata": {
                "supplier_name": "Premium Meats Ltd",
                "invoice_number": "INV-2024-002",
                "invoice_date": "2024-12-01",
                "total_amount": 250.00,
                "subtotal": 208.33,
                "vat": 41.67,
                "vat_rate": 20.0
            },
            "line_items": [
                {
                    "item": "Beef Sirloin",
                    "quantity": 8.0,
                    "unit_price_excl_vat": 25.00,  # High price
                    "line_total_excl_vat": 200.00
                },
                {
                    "item": "Lamb Chops",
                    "quantity": 2.0,
                    "unit_price_excl_vat": 25.00,
                    "line_total_excl_vat": 50.00
                }
            ],
            "delivery_note_attached": False,
            "confidence": 85.0
        }
        
        historical_prices = {
            "Beef Sirloin": [18.50, 19.00, 20.50, 21.00, 20.00],  # Average: 19.80
            "Lamb Chops": [22.00, 23.00, 24.00, 25.00, 24.50],    # Average: 23.70
        }
        
        result = run_owlin_agent(invoice_data, historical_prices)
        self._assert_test(
            "Integration scenario 1",
            result['confidence_score'] > 0 and len(result['flags']) > 0 and len(result['summary']) > 0,
            f"Expected valid result, got confidence={result['confidence_score']}, flags={len(result['flags'])}, summary={len(result['summary'])}"
        )
        
        # Scenario 2: Low-confidence invoice with missing data
        poor_invoice_data = {
            "metadata": {
                "supplier_name": "Unknown",
                "invoice_number": "Unknown",
                "invoice_date": "",
                "total_amount": 0.0,
                "subtotal": 0.0,
                "vat": 0.0,
                "vat_rate": 0.0
            },
            "line_items": [],
            "delivery_note_attached": False,
            "confidence": 25.0
        }
        
        result = run_owlin_agent(poor_invoice_data, {})
        self._assert_test(
            "Integration scenario 2",
            result['confidence_score'] < 40.0 and result['manual_review_required'] == True,
            f"Expected low confidence and manual review, got confidence={result['confidence_score']}, manual_review={result['manual_review_required']}"
        )
    
    def _test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        logger.info("🔍 Testing Edge Cases")
        
        # Test empty data
        result = score_confidence({}, [], 0.0)
        self._assert_test(
            "Empty data handling",
            result['score'] == 0.0 and result['manual_review_required'] == True,
            f"Expected 0 score and manual review, got {result['score']}/{result['manual_review_required']}"
        )
        
        # Test very high OCR confidence
        result = score_confidence({"supplier_name": "Test"}, [], 100.0)
        self._assert_test(
            "High OCR confidence",
            result['score'] > 0,
            f"Expected positive score, got {result['score']}"
        )
        
        # Test future date
        from datetime import timedelta
        future_metadata = {
            "supplier_name": "Test Supplier",
            "invoice_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "total_amount": 100.0
        }
        
        flags = check_delivery_pairing(True, [], future_metadata)
        future_date_flags = [f for f in flags if f.get('type') == 'future_delivery_date']
        self._assert_test(
            "Future date detection",
            len(future_date_flags) > 0,
            f"Expected future date flag, got {len(future_date_flags)}"
        )
    
    def _test_error_handling(self):
        """Test error handling and robustness."""
        logger.info("🛡️ Testing Error Handling")
        
        # Test with invalid data types
        try:
            result = score_confidence(None, None, "invalid")
            self._assert_test(
                "Invalid data type handling",
                True,  # Should not raise exception
                "Expected graceful handling of invalid data"
            )
        except Exception as e:
            self._assert_test(
                "Invalid data type handling",
                False,
                f"Unexpected exception: {e}"
            )
        
        # Test with malformed line items
        malformed_items = [
            {"invalid_field": "test"},
            {"item": "", "quantity": "not_a_number"},
            None
        ]
        
        try:
            result = score_confidence({"supplier_name": "Test"}, malformed_items, 50.0)
            self._assert_test(
                "Malformed line items handling",
                True,  # Should not raise exception
                "Expected graceful handling of malformed items"
            )
        except Exception as e:
            self._assert_test(
                "Malformed line items handling",
                False,
                f"Unexpected exception: {e}"
            )
    
    def _assert_test(self, test_name: str, condition: bool, message: str):
        """
        Assert a test condition and record the result.
        
        Args:
            test_name: Name of the test
            condition: Test condition (True = pass, False = fail)
            message: Description of the test result
        """
        if condition:
            logger.info(f"✅ PASS: {test_name}")
            self.passed_tests += 1
            self.test_results.append({"name": test_name, "status": "PASS", "message": message})
        else:
            logger.error(f"❌ FAIL: {test_name} - {message}")
            self.failed_tests += 1
            self.test_results.append({"name": test_name, "status": "FAIL", "message": message})
    
    def _print_results(self):
        """Print test results summary."""
        logger.info("=" * 50)
        logger.info("📊 Test Results Summary")
        logger.info("=" * 50)
        logger.info(f"✅ Passed: {self.passed_tests}")
        logger.info(f"❌ Failed: {self.failed_tests}")
        logger.info(f"📈 Total: {self.passed_tests + self.failed_tests}")
        
        if self.failed_tests > 0:
            logger.info("\n❌ Failed Tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    logger.error(f"  - {result['name']}: {result['message']}")
        
        success_rate = (self.passed_tests / (self.passed_tests + self.failed_tests)) * 100 if (self.passed_tests + self.failed_tests) > 0 else 0
        logger.info(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests == 0:
            logger.info("🎉 All tests passed! Owlin Agent is ready for deployment.")
        else:
            logger.error("⚠️ Some tests failed. Please review the issues above.")


def run_quick_test():
    """
    Run a quick test to verify basic functionality.
    
    Returns:
        True if basic functionality works
    """
    logger.info("🚀 Running Quick Test")
    
    try:
        # Test agent info
        agent_info = get_agent_info()
        if not agent_info or 'name' not in agent_info:
            logger.error("❌ Agent info test failed")
            return False
        
        # Test basic invoice analysis
        sample_invoice = {
            "metadata": {
                "supplier_name": "Test Supplier",
                "invoice_number": "TEST-001",
                "invoice_date": "2024-12-01",
                "total_amount": 100.00,
                "subtotal": 83.33,
                "vat": 16.67,
                "vat_rate": 20.0
            },
            "line_items": [
                {
                    "item": "Test Item",
                    "quantity": 1.0,
                    "unit_price_excl_vat": 83.33,
                    "line_total_excl_vat": 83.33
                }
            ],
            "delivery_note_attached": False,
            "confidence": 80.0
        }
        
        result = run_owlin_agent(sample_invoice, {})
        
        if not result or 'confidence_score' not in result:
            logger.error("❌ Basic invoice analysis test failed")
            return False
        
        logger.info("✅ Quick test passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Quick test failed: {e}")
        return False


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run quick test first
    if run_quick_test():
        # Run full test suite
        tester = OwlinAgentTester()
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! Owlin Agent is ready for production.")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed. Please review the issues above.")
            sys.exit(1)
    else:
        print("\n❌ Quick test failed. Please check the agent setup.")
        sys.exit(1) 