#!/usr/bin/env python3
"""
Test supplier discount service
"""

import sys
import os
import tempfile
import sqlite3
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.discount_service import DiscountService, SupplierDiscount
from db_manager_unified import DatabaseManager

def test_create_discount():
    """Test creating a discount rule"""
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Initialize database with migrations
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        # Create service
        service = DiscountService()
        service.db_manager = db_manager
        
        # Test creating discount
        discount = service.create_discount(
            supplier_id="TEST_SUPPLIER",
            scope="supplier",
            kind="percent",
            value=15.0,
            evidence_ref="test_evidence"
        )
        
        assert discount is not None
        assert discount.supplier_id == "TEST_SUPPLIER"
        assert discount.scope == "supplier"
        assert discount.kind == "percent"
        assert discount.value == 15.0
        assert discount.evidence_ref == "test_evidence"
        
        print("✅ Create discount test passed")
        
    finally:
        os.unlink(db_path)

def test_update_discount():
    """Test updating a discount rule"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        service = DiscountService()
        service.db_manager = db_manager
        
        # Create discount
        discount = service.create_discount(
            supplier_id="TEST_SUPPLIER",
            scope="supplier",
            kind="percent",
            value=10.0
        )
        
        # Update discount
        updated = service.update_discount(discount.id, value=20.0, scope="category")
        
        assert updated is not None
        assert updated.value == 20.0
        assert updated.scope == "category"
        
        print("✅ Update discount test passed")
        
    finally:
        os.unlink(db_path)

def test_enforce_discount_rules():
    """Test discount rule enforcement and validation"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        service = DiscountService()
        service.db_manager = db_manager
        
        # Test invalid scope
        try:
            service.create_discount("TEST", "invalid", "percent", 10.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test invalid kind
        try:
            service.create_discount("TEST", "supplier", "invalid", 10.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        # Test negative value
        try:
            service.create_discount("TEST", "supplier", "percent", -10.0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
        
        print("✅ Discount rule enforcement test passed")
        
    finally:
        os.unlink(db_path)

def test_find_applicable_discount():
    """Test finding applicable discount with priority"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        service = DiscountService()
        service.db_manager = db_manager
        
        # Create supplier-level discount
        service.create_discount("TEST_SUPPLIER", "supplier", "percent", 10.0)
        
        # Create category-level discount
        service.create_discount("TEST_SUPPLIER", "category", "percent", 15.0)
        
        # Create SKU-level discount
        service.create_discount("TEST_SUPPLIER", "sku", "percent", 20.0)
        
        # Test priority: SKU > category > supplier
        discount = service.find_applicable_discount("TEST_SUPPLIER", sku="TEST_SKU")
        assert discount.scope == "sku"
        assert discount.value == 20.0
        
        discount = service.find_applicable_discount("TEST_SUPPLIER", category="TEST_CATEGORY")
        assert discount.scope == "category"
        assert discount.value == 15.0
        
        discount = service.find_applicable_discount("TEST_SUPPLIER")
        assert discount.scope == "supplier"
        assert discount.value == 10.0
        
        print("✅ Find applicable discount test passed")
        
    finally:
        os.unlink(db_path)

def test_delete_discount():
    """Test deleting a discount rule"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        db_manager = DatabaseManager(db_path)
        db_manager.run_migrations()
        
        service = DiscountService()
        service.db_manager = db_manager
        
        # Create discount
        discount = service.create_discount("TEST_SUPPLIER", "supplier", "percent", 10.0)
        
        # Delete discount
        success = service.delete_discount(discount.id)
        assert success
        
        # Verify deleted
        retrieved = service.get_discount(discount.id)
        assert retrieved is None
        
        print("✅ Delete discount test passed")
        
    finally:
        os.unlink(db_path)

if __name__ == "__main__":
    test_create_discount()
    test_update_discount()
    test_enforce_discount_rules()
    test_find_applicable_discount()
    test_delete_discount()
    print("All supplier discount tests passed!") 