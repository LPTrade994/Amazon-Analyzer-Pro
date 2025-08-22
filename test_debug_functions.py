#!/usr/bin/env python3
"""
Test Debug Functions
Verifica che le funzioni di debug funzionino correttamente
"""

import pandas as pd
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pricing import select_purchase_price, select_target_price

def test_pricing_functions():
    """Test pricing functions with debug output"""
    
    print("=" * 60)
    print("TESTING PRICING FUNCTIONS WITH DEBUG")
    print("=" * 60)
    
    # Create test data
    test_row = pd.Series({
        'ASIN': 'B0D23VW9VB',
        'Buy Box 🚚: Current': 25.99,
        'Amazon: Current': 27.50,
        'New FBA: Current': 24.99,
        'source_market': 'de',
        'Title': 'Test Product'
    })
    
    print("Test data:")
    print(f"  ASIN: {test_row['ASIN']}")
    print(f"  Buy Box Current: €{test_row['Buy Box 🚚: Current']}")
    print(f"  Amazon Current: €{test_row['Amazon: Current']}")
    print(f"  Source Market: {test_row['source_market']}")
    
    print("\n" + "-" * 40)
    print("TESTING select_purchase_price():")
    print("-" * 40)
    
    # Test purchase price selection (this will show debug output)
    try:
        price = select_purchase_price(test_row, "Buy Box Current")
        print(f"Result: €{price}")
    except Exception as e:
        print(f"Error in select_purchase_price: {e}")
    
    print("\n" + "-" * 40)
    print("TESTING select_target_price():")
    print("-" * 40)
    
    # Test target price selection (this will show debug output)
    try:
        target_price = select_target_price(test_row, 'it', 'Medium')
        print(f"Result: €{target_price}")
    except Exception as e:
        print(f"Error in select_target_price: {e}")
    
    return True

def test_zero_price_scenarios():
    """Test scenarios that lead to zero prices"""
    
    print("\n" + "=" * 60)
    print("TESTING ZERO PRICE SCENARIOS")
    print("=" * 60)
    
    # Test with missing price columns
    empty_row = pd.Series({
        'ASIN': 'B123MISSING',
        'Title': 'Product with no prices',
        'source_market': 'it'
    })
    
    print("Testing with missing price columns:")
    try:
        price = select_purchase_price(empty_row, "Buy Box Current")
        print(f"Purchase price result: €{price} (expected: 0.0)")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test with zero/invalid prices
    invalid_row = pd.Series({
        'ASIN': 'B123INVALID',
        'Buy Box 🚚: Current': 0,  # Zero price
        'Amazon: Current': None,   # None price
        'New FBA: Current': 'invalid',  # Invalid price
        'source_market': 'fr'
    })
    
    print("\nTesting with invalid price values:")
    try:
        price = select_purchase_price(invalid_row, "Buy Box Current")
        print(f"Purchase price result: €{price} (expected: 0.0)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("DEBUG FUNCTIONS TEST")
    print("Note: This will show debug output when used within Streamlit context")
    print("In non-Streamlit context, debug statements are suppressed")
    
    success1 = test_pricing_functions()
    test_zero_price_scenarios()
    
    if success1:
        print("\nAll debug function tests completed")
        print("\nNEXT STEPS:")
        print("1. Run the Streamlit app: streamlit run app.py")
        print("2. Upload your multi-market CSV files")
        print("3. Check the debug output to identify where pricing fails")
        print("4. Look specifically for:")
        print("   - Are price columns found correctly?")
        print("   - Are price values valid numbers?") 
        print("   - Are all market routes being tested?")
        print("   - Where does the price become 0?")
    else:
        print("\nSome tests failed")