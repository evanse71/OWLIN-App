#!/usr/bin/env python3
"""
Script to create test product data for the Product Trends page
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

def create_test_product_data():
    """Create test invoice line items to demonstrate Product Trends page"""
    
    # Connect to database
    db_path = os.path.join("data", "owlin.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get existing invoice IDs
    cursor.execute("SELECT id FROM invoices LIMIT 5")
    invoice_ids = [row[0] for row in cursor.fetchall()]
    
    if not invoice_ids:
        print("❌ No invoices found in database. Please upload some invoices first.")
        conn.close()
        return
    
    print(f"✅ Found {len(invoice_ids)} invoices to add line items to")
    
    # Test products with realistic data
    test_products = [
        {
            "name": "Fresh Milk",
            "base_price": 1.20,
            "volatility": 0.15,
            "trend": "increasing"
        },
        {
            "name": "Organic Carrots",
            "base_price": 0.85,
            "volatility": 0.25,
            "trend": "stable"
        },
        {
            "name": "Premium Beef",
            "base_price": 8.50,
            "volatility": 0.30,
            "trend": "increasing"
        },
        {
            "name": "Whole Grain Bread",
            "base_price": 1.45,
            "volatility": 0.10,
            "trend": "stable"
        },
        {
            "name": "Free Range Eggs",
            "base_price": 2.80,
            "volatility": 0.20,
            "trend": "increasing"
        }
    ]
    
    # Generate historical data for the past 12 months
    start_date = datetime.now() - timedelta(days=365)
    current_date = start_date
    
    line_items_created = 0
    
    for product in test_products:
        print(f"📦 Creating data for: {product['name']}")
        
        # Create 12 months of data
        for month in range(12):
            # Calculate date for this month
            month_date = start_date + timedelta(days=month * 30)
            
            # Add some randomness to the price
            base_price = product['base_price']
            if product['trend'] == 'increasing':
                # Gradual price increase
                trend_factor = 1 + (month * 0.02)  # 2% increase per month
            elif product['trend'] == 'decreasing':
                # Gradual price decrease
                trend_factor = 1 - (month * 0.01)  # 1% decrease per month
            else:
                # Stable with small fluctuations
                trend_factor = 1 + (random.uniform(-0.05, 0.05))
            
            # Add volatility
            volatility_factor = 1 + random.uniform(-product['volatility'], product['volatility'])
            
            final_price = base_price * trend_factor * volatility_factor
            
            # Create 2-4 line items per month for this product
            for item_count in range(random.randint(2, 4)):
                # Select a random invoice
                invoice_id = random.choice(invoice_ids)
                
                # Random quantity between 1 and 50
                quantity = random.randint(1, 50)
                
                # Calculate total price
                total_price = final_price * quantity
                
                # Insert line item
                cursor.execute("""
                    INSERT INTO invoice_line_items 
                    (invoice_id, item_description, quantity, unit_price, total_price, source, confidence, flagged)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    invoice_id,
                    product['name'],
                    quantity,
                    round(final_price, 2),
                    round(total_price, 2),
                    'test_data',
                    0.95,
                    0  # Not flagged
                ))
                
                line_items_created += 1
        
        print(f"   ✅ Created 12 months of data for {product['name']}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Successfully created {line_items_created} line items across {len(test_products)} products!")
    print("📊 The Product Trends page should now show data when you refresh it.")
    print("\n📋 Products added:")
    for product in test_products:
        print(f"   • {product['name']} (trend: {product['trend']})")

if __name__ == "__main__":
    create_test_product_data() 