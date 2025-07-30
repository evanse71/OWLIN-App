"""
Supplier Scoring Module for Owlin Agent

Evaluates supplier performance across invoices and deliveries to help
GMs and Finance users make data-driven supplier management decisions.
"""

import logging
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

def calculate_supplier_scores(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Calculate performance scores for all suppliers.
    
    Analyzes supplier performance across invoices, deliveries, and mismatches
    to provide actionable insights for supplier management.
    
    Args:
        conn: SQLite database connection
        
    Returns:
        List of supplier score dictionaries:
        [
            {
                "supplier_name": str,           # Supplier name
                "match_rate": float,            # % of invoices with delivery notes
                "mismatch_rate": float,         # % of line items flagged
                "average_confidence": float,    # Average OCR confidence
                "delivery_accuracy": float,     # % of deliveries without issues
                "total_invoices": int,          # Number of scanned invoices
                "total_deliveries": int,        # Number of deliveries
                "total_mismatches": int,        # Number of mismatches found
                "average_invoice_value": float, # Average invoice value
                "performance_trend": str,       # "improving", "declining", "stable"
                "risk_level": str,              # "low", "medium", "high"
                "last_activity": str,           # Date of last invoice
                "score_breakdown": dict         # Detailed scoring components
            }
        ]
    """
    logger.info("📊 Calculating supplier performance scores")
    
    try:
        # Get all suppliers
        suppliers = _get_all_suppliers(conn)
        logger.info(f"📋 Found {len(suppliers)} suppliers to analyze")
        
        supplier_scores = []
        
        for supplier in suppliers:
            score = _calculate_single_supplier_score(supplier, conn)
            if score:
                supplier_scores.append(score)
        
        # Sort by performance (best first)
        supplier_scores.sort(key=lambda x: x.get('overall_score', 0), reverse=True)
        
        logger.info(f"✅ Calculated scores for {len(supplier_scores)} suppliers")
        return supplier_scores
        
    except Exception as e:
        logger.error(f"❌ Error calculating supplier scores: {e}")
        return []

def _get_all_suppliers(conn: sqlite3.Connection) -> List[str]:
    """
    Get all unique supplier names from the database.
    
    Args:
        conn: Database connection
        
    Returns:
        List of supplier names
    """
    cursor = conn.cursor()
    
    # Try different table structures to find suppliers
    suppliers = set()
    
    # Check invoices table
    try:
        cursor.execute("""
            SELECT DISTINCT supplier_name 
            FROM invoices 
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
        """)
        suppliers.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError:
        pass
    
    # Check parsed_invoices table
    try:
        cursor.execute("""
            SELECT DISTINCT supplier_name 
            FROM parsed_invoices 
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
        """)
        suppliers.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError:
        pass
    
    # Check uploads table
    try:
        cursor.execute("""
            SELECT DISTINCT supplier_name 
            FROM uploads 
            WHERE supplier_name IS NOT NULL AND supplier_name != ''
        """)
        suppliers.update([row[0] for row in cursor.fetchall()])
    except sqlite3.OperationalError:
        pass
    
    return list(suppliers)

def _calculate_single_supplier_score(supplier_name: str, conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
    """
    Calculate performance score for a single supplier.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Supplier score dictionary or None if insufficient data
    """
    try:
        logger.debug(f"🔍 Analyzing supplier: {supplier_name}")
        
        # Get supplier invoices
        invoices = _get_supplier_invoices(supplier_name, conn)
        if not invoices:
            logger.debug(f"⚠️ No invoices found for {supplier_name}")
            return None
        
        # Calculate metrics
        match_rate = _calculate_match_rate(supplier_name, conn)
        mismatch_rate = _calculate_mismatch_rate(supplier_name, conn)
        average_confidence = _calculate_average_confidence(supplier_name, conn)
        delivery_accuracy = _calculate_delivery_accuracy(supplier_name, conn)
        total_invoices = len(invoices)
        total_deliveries = _count_deliveries(supplier_name, conn)
        total_mismatches = _count_mismatches(supplier_name, conn)
        average_invoice_value = _calculate_average_invoice_value(invoices)
        performance_trend = _calculate_performance_trend(supplier_name, conn)
        risk_level = _calculate_risk_level(match_rate, mismatch_rate, delivery_accuracy)
        last_activity = _get_last_activity(supplier_name, conn)
        
        # Calculate overall score
        overall_score = _calculate_overall_score(
            match_rate, mismatch_rate, average_confidence, 
            delivery_accuracy, total_invoices
        )
        
        # Create score breakdown
        score_breakdown = {
            "delivery_compliance": match_rate,
            "billing_accuracy": 100 - mismatch_rate,
            "data_quality": average_confidence,
            "delivery_quality": delivery_accuracy,
            "volume_score": min(total_invoices / 10, 100)  # Cap at 100 for 10+ invoices
        }
        
        return {
            "supplier_name": supplier_name,
            "match_rate": round(match_rate, 1),
            "mismatch_rate": round(mismatch_rate, 1),
            "average_confidence": round(average_confidence, 1),
            "delivery_accuracy": round(delivery_accuracy, 1),
            "total_invoices": total_invoices,
            "total_deliveries": total_deliveries,
            "total_mismatches": total_mismatches,
            "average_invoice_value": round(average_invoice_value, 2),
            "performance_trend": performance_trend,
            "risk_level": risk_level,
            "last_activity": last_activity,
            "overall_score": round(overall_score, 1),
            "score_breakdown": score_breakdown
        }
        
    except Exception as e:
        logger.error(f"❌ Error calculating score for {supplier_name}: {e}")
        return None

def _get_supplier_invoices(supplier_name: str, conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Get all invoices for a supplier.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        List of invoice dictionaries
    """
    cursor = conn.cursor()
    invoices = []
    
    # Try different table structures
    queries = [
        """
        SELECT invoice_id, supplier_name, invoice_date, total_amount, 
               delivery_note_attached, confidence, created_at
        FROM invoices 
        WHERE supplier_name = ?
        ORDER BY invoice_date DESC
        """,
        """
        SELECT invoice_id, supplier_name, invoice_date, total_amount, 
               delivery_note_attached, confidence, created_at
        FROM parsed_invoices 
        WHERE supplier_name = ?
        ORDER BY invoice_date DESC
        """,
        """
        SELECT invoice_id, supplier_name, invoice_date, total_amount, 
               delivery_note_attached, confidence, created_at
        FROM uploads 
        WHERE supplier_name = ?
        ORDER BY invoice_date DESC
        """
    ]
    
    for query in queries:
        try:
            cursor.execute(query, (supplier_name,))
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    invoices.append({
                        "invoice_id": row[0],
                        "supplier_name": row[1],
                        "invoice_date": row[2],
                        "total_amount": row[3],
                        "delivery_note_attached": row[4],
                        "confidence": row[5],
                        "created_at": row[6]
                    })
                break
        except sqlite3.OperationalError:
            continue
    
    return invoices

def _calculate_match_rate(supplier_name: str, conn: sqlite3.Connection) -> float:
    """
    Calculate the percentage of invoices with delivery notes.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Match rate percentage (0-100)
    """
    cursor = conn.cursor()
    
    # Count invoices with delivery notes
    queries = [
        """
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN delivery_note_attached = 1 THEN 1 ELSE 0 END) as matched
        FROM invoices 
        WHERE supplier_name = ?
        """,
        """
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN delivery_note_attached = 1 THEN 1 ELSE 0 END) as matched
        FROM parsed_invoices 
        WHERE supplier_name = ?
        """,
        """
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN delivery_note_attached = 1 THEN 1 ELSE 0 END) as matched
        FROM uploads 
        WHERE supplier_name = ?
        """
    ]
    
    for query in queries:
        try:
            cursor.execute(query, (supplier_name,))
            result = cursor.fetchone()
            if result and result[0] > 0:
                total, matched = result
                return (matched / total) * 100
        except sqlite3.OperationalError:
            continue
    
    return 0.0

def _calculate_mismatch_rate(supplier_name: str, conn: sqlite3.Connection) -> float:
    """
    Calculate the percentage of line items that were flagged as mismatches.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Mismatch rate percentage (0-100)
    """
    cursor = conn.cursor()
    
    try:
        # Get total line items and mismatched items for this supplier
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT im.id) as total_mismatches,
                COUNT(DISTINCT i.invoice_id) as total_invoices
            FROM invoice_mismatches im
            JOIN invoices i ON im.invoice_id = i.invoice_id
            WHERE i.supplier_name = ?
        """, (supplier_name,))
        
        result = cursor.fetchone()
        if result and result[1] > 0:
            total_mismatches, total_invoices = result
            # Estimate line items as 5 per invoice (typical)
            estimated_line_items = total_invoices * 5
            return (total_mismatches / estimated_line_items) * 100
    except sqlite3.OperationalError:
        pass
    
    return 0.0

def _calculate_average_confidence(supplier_name: str, conn: sqlite3.Connection) -> float:
    """
    Calculate average OCR confidence for supplier invoices.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Average confidence percentage (0-100)
    """
    cursor = conn.cursor()
    
    queries = [
        """
        SELECT AVG(confidence) as avg_confidence
        FROM invoices 
        WHERE supplier_name = ? AND confidence IS NOT NULL
        """,
        """
        SELECT AVG(confidence) as avg_confidence
        FROM parsed_invoices 
        WHERE supplier_name = ? AND confidence IS NOT NULL
        """,
        """
        SELECT AVG(confidence) as avg_confidence
        FROM uploads 
        WHERE supplier_name = ? AND confidence IS NOT NULL
        """
    ]
    
    for query in queries:
        try:
            cursor.execute(query, (supplier_name,))
            result = cursor.fetchone()
            if result and result[0] is not None:
                return float(result[0])
        except sqlite3.OperationalError:
            continue
    
    return 0.0

def _calculate_delivery_accuracy(supplier_name: str, conn: sqlite3.Connection) -> float:
    """
    Calculate delivery accuracy based on missing items and delivery issues.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Delivery accuracy percentage (0-100)
    """
    cursor = conn.cursor()
    
    try:
        # Count delivery-related mismatches
        cursor.execute("""
            SELECT COUNT(*) as delivery_issues
            FROM invoice_mismatches im
            JOIN invoices i ON im.invoice_id = i.invoice_id
            WHERE i.supplier_name = ? 
            AND im.mismatch_type IN ('missing_item', 'quantity_mismatch', 'delivery_issue')
        """, (supplier_name,))
        
        delivery_issues = cursor.fetchone()[0] or 0
        
        # Get total deliveries
        total_deliveries = _count_deliveries(supplier_name, conn)
        
        if total_deliveries > 0:
            accuracy = ((total_deliveries - delivery_issues) / total_deliveries) * 100
            return max(0, accuracy)
    except sqlite3.OperationalError:
        pass
    
    return 100.0  # Default to 100% if no data

def _count_deliveries(supplier_name: str, conn: sqlite3.Connection) -> int:
    """
    Count total deliveries for a supplier.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Number of deliveries
    """
    cursor = conn.cursor()
    
    queries = [
        """
        SELECT COUNT(*) 
        FROM invoices 
        WHERE supplier_name = ? AND delivery_note_attached = 1
        """,
        """
        SELECT COUNT(*) 
        FROM parsed_invoices 
        WHERE supplier_name = ? AND delivery_note_attached = 1
        """,
        """
        SELECT COUNT(*) 
        FROM uploads 
        WHERE supplier_name = ? AND delivery_note_attached = 1
        """
    ]
    
    for query in queries:
        try:
            cursor.execute(query, (supplier_name,))
            result = cursor.fetchone()
            if result:
                return result[0]
        except sqlite3.OperationalError:
            continue
    
    return 0

def _count_mismatches(supplier_name: str, conn: sqlite3.Connection) -> int:
    """
    Count total mismatches for a supplier.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Number of mismatches
    """
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT COUNT(*) 
            FROM invoice_mismatches im
            JOIN invoices i ON im.invoice_id = i.invoice_id
            WHERE i.supplier_name = ?
        """, (supplier_name,))
        
        result = cursor.fetchone()
        return result[0] if result else 0
    except sqlite3.OperationalError:
        return 0

def _calculate_average_invoice_value(invoices: List[Dict[str, Any]]) -> float:
    """
    Calculate average invoice value.
    
    Args:
        invoices: List of invoice dictionaries
        
    Returns:
        Average invoice value
    """
    if not invoices:
        return 0.0
    
    total_value = sum(invoice.get('total_amount', 0) for invoice in invoices)
    return total_value / len(invoices)

def _calculate_performance_trend(supplier_name: str, conn: sqlite3.Connection) -> str:
    """
    Calculate performance trend based on recent vs historical data.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Trend: "improving", "declining", or "stable"
    """
    cursor = conn.cursor()
    
    try:
        # Compare recent 30 days vs previous 30 days
        recent_date = datetime.now() - timedelta(days=30)
        
        cursor.execute("""
            SELECT 
                AVG(CASE WHEN invoice_date >= ? THEN confidence ELSE NULL END) as recent_confidence,
                AVG(CASE WHEN invoice_date < ? THEN confidence ELSE NULL END) as historical_confidence
            FROM invoices 
            WHERE supplier_name = ? AND invoice_date IS NOT NULL
        """, (recent_date.strftime('%Y-%m-%d'), recent_date.strftime('%Y-%m-%d'), supplier_name))
        
        result = cursor.fetchone()
        if result and result[0] is not None and result[1] is not None:
            recent_avg = result[0]
            historical_avg = result[1]
            
            if recent_avg > historical_avg + 5:
                return "improving"
            elif recent_avg < historical_avg - 5:
                return "declining"
            else:
                return "stable"
    except sqlite3.OperationalError:
        pass
    
    return "stable"

def _calculate_risk_level(match_rate: float, mismatch_rate: float, delivery_accuracy: float) -> str:
    """
    Calculate risk level based on performance metrics.
    
    Args:
        match_rate: Delivery note match rate
        mismatch_rate: Line item mismatch rate
        delivery_accuracy: Delivery accuracy percentage
        
    Returns:
        Risk level: "low", "medium", or "high"
    """
    risk_score = 0
    
    # Add risk points based on poor performance
    if match_rate < 70:
        risk_score += 2
    if mismatch_rate > 15:
        risk_score += 2
    if delivery_accuracy < 80:
        risk_score += 2
    if match_rate < 50:
        risk_score += 1
    if mismatch_rate > 25:
        risk_score += 1
    if delivery_accuracy < 60:
        risk_score += 1
    
    if risk_score >= 4:
        return "high"
    elif risk_score >= 2:
        return "medium"
    else:
        return "low"

def _get_last_activity(supplier_name: str, conn: sqlite3.Connection) -> str:
    """
    Get the date of the last invoice for a supplier.
    
    Args:
        supplier_name: Name of the supplier
        conn: Database connection
        
    Returns:
        Last activity date as string
    """
    cursor = conn.cursor()
    
    queries = [
        """
        SELECT MAX(invoice_date) 
        FROM invoices 
        WHERE supplier_name = ?
        """,
        """
        SELECT MAX(invoice_date) 
        FROM parsed_invoices 
        WHERE supplier_name = ?
        """,
        """
        SELECT MAX(invoice_date) 
        FROM uploads 
        WHERE supplier_name = ?
        """
    ]
    
    for query in queries:
        try:
            cursor.execute(query, (supplier_name,))
            result = cursor.fetchone()
            if result and result[0]:
                return result[0]
        except sqlite3.OperationalError:
            continue
    
    return "Unknown"

def _calculate_overall_score(match_rate: float, mismatch_rate: float, 
                           average_confidence: float, delivery_accuracy: float, 
                           total_invoices: int) -> float:
    """
    Calculate overall supplier score.
    
    Args:
        match_rate: Delivery note match rate
        mismatch_rate: Line item mismatch rate
        average_confidence: Average OCR confidence
        delivery_accuracy: Delivery accuracy percentage
        total_invoices: Number of invoices
        
    Returns:
        Overall score (0-100)
    """
    # Weighted scoring system
    weights = {
        'match_rate': 0.25,
        'billing_accuracy': 0.30,
        'data_quality': 0.20,
        'delivery_accuracy': 0.25
    }
    
    billing_accuracy = max(0, 100 - mismatch_rate)
    
    score = (
        (match_rate * weights['match_rate']) +
        (billing_accuracy * weights['billing_accuracy']) +
        (average_confidence * weights['data_quality']) +
        (delivery_accuracy * weights['delivery_accuracy'])
    )
    
    # Bonus for high volume suppliers
    if total_invoices >= 20:
        score += 5
    elif total_invoices >= 10:
        score += 2
    
    return min(100, max(0, score))

def get_supplier_summary(supplier_scores: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of all supplier scores.
    
    Args:
        supplier_scores: List of supplier score dictionaries
        
    Returns:
        Summary dictionary
    """
    if not supplier_scores:
        return {
            "total_suppliers": 0,
            "average_score": 0.0,
            "high_risk_suppliers": 0,
            "improving_suppliers": 0,
            "declining_suppliers": 0
        }
    
    total_suppliers = len(supplier_scores)
    average_score = sum(s.get('overall_score', 0) for s in supplier_scores) / total_suppliers
    high_risk = len([s for s in supplier_scores if s.get('risk_level') == 'high'])
    improving = len([s for s in supplier_scores if s.get('performance_trend') == 'improving'])
    declining = len([s for s in supplier_scores if s.get('performance_trend') == 'declining'])
    
    return {
        "total_suppliers": total_suppliers,
        "average_score": round(average_score, 1),
        "high_risk_suppliers": high_risk,
        "improving_suppliers": improving,
        "declining_suppliers": declining,
        "stable_suppliers": total_suppliers - improving - declining
    }

def get_supplier_recommendations(supplier_scores: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate recommendations for supplier management.
    
    Args:
        supplier_scores: List of supplier score dictionaries
        
    Returns:
        List of recommendation dictionaries
    """
    recommendations = []
    
    for supplier in supplier_scores:
        supplier_name = supplier.get('supplier_name', 'Unknown')
        risk_level = supplier.get('risk_level', 'low')
        performance_trend = supplier.get('performance_trend', 'stable')
        
        if risk_level == 'high':
            recommendations.append({
                "supplier_name": supplier_name,
                "priority": "high",
                "action": "immediate_attention",
                "message": f"High-risk supplier requiring immediate attention. Consider contract review or replacement.",
                "metrics": {
                    "match_rate": supplier.get('match_rate', 0),
                    "mismatch_rate": supplier.get('mismatch_rate', 0),
                    "delivery_accuracy": supplier.get('delivery_accuracy', 0)
                }
            })
        elif risk_level == 'medium' and performance_trend == 'declining':
            recommendations.append({
                "supplier_name": supplier_name,
                "priority": "medium",
                "action": "monitor_closely",
                "message": f"Performance declining. Monitor closely and consider intervention.",
                "metrics": {
                    "match_rate": supplier.get('match_rate', 0),
                    "mismatch_rate": supplier.get('mismatch_rate', 0),
                    "delivery_accuracy": supplier.get('delivery_accuracy', 0)
                }
            })
        elif supplier.get('match_rate', 0) < 70:
            recommendations.append({
                "supplier_name": supplier_name,
                "priority": "medium",
                "action": "improve_delivery",
                "message": f"Low delivery note compliance. Request improved delivery documentation.",
                "metrics": {
                    "match_rate": supplier.get('match_rate', 0)
                }
            })
    
    return recommendations


if __name__ == "__main__":
    # Test the supplier scoring engine
    logging.basicConfig(level=logging.INFO)
    
    # Create test database connection
    import tempfile
    import os
    
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
            ("INV-001", "Bidfood", "2024-12-01", 150.00, 1, 85.0, "2024-12-01"),
            ("INV-002", "Bidfood", "2024-12-02", 200.00, 0, 90.0, "2024-12-02"),
            ("INV-003", "Bidfood", "2024-12-03", 175.00, 1, 88.0, "2024-12-03"),
            ("INV-004", "Sysco", "2024-12-01", 300.00, 1, 92.0, "2024-12-01"),
            ("INV-005", "Sysco", "2024-12-02", 250.00, 1, 89.0, "2024-12-02"),
        ]
        
        test_mismatches = [
            (1, "INV-001", "Beef Sirloin", "overcharge", 85.0, "2024-12-01"),
            (2, "INV-002", "Chicken Breast", "missing_item", 90.0, "2024-12-02"),
            (3, "INV-004", "Lamb Chops", "price_increase", 88.0, "2024-12-01"),
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
        
        # Test supplier scoring
        scores = calculate_supplier_scores(conn)
        
        print("📊 Supplier Scoring Test Results:")
        print(f"Found {len(scores)} suppliers")
        
        for i, score in enumerate(scores, 1):
            print(f"\n{i}. {score['supplier_name']}")
            print(f"   Overall Score: {score['overall_score']:.1f}")
            print(f"   Match Rate: {score['match_rate']:.1f}%")
            print(f"   Mismatch Rate: {score['mismatch_rate']:.1f}%")
            print(f"   Delivery Accuracy: {score['delivery_accuracy']:.1f}%")
            print(f"   Risk Level: {score['risk_level']}")
            print(f"   Performance Trend: {score['performance_trend']}")
        
        # Test summary
        summary = get_supplier_summary(scores)
        print(f"\n📈 Summary:")
        print(f"   Total Suppliers: {summary['total_suppliers']}")
        print(f"   Average Score: {summary['average_score']:.1f}")
        print(f"   High Risk: {summary['high_risk_suppliers']}")
        
        # Test recommendations
        recommendations = get_supplier_recommendations(scores)
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   - {rec['supplier_name']}: {rec['message']}")
        
        conn.close()
        
    finally:
        # Clean up
        os.unlink(temp_db.name)
        print("\n✅ Test completed successfully") 