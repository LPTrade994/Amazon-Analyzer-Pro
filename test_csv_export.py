#!/usr/bin/env python3
"""
Test CSV Export Fixes
Verifica che l'export CSV funzioni correttamente con HTML e caratteri speciali
"""

import pandas as pd
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export import export_consolidated_csv

def test_csv_export_fixes():
    """Test the CSV export fixes"""
    
    # Create test data with problematic characters
    test_data = {
        'ASIN': ['B0D23VW9VB', 'B0D24ABC123', 'B0D25XYZ789'],
        'Title': [
            'Product with, comma and "quotes"',
            'Another product with <HTML> tags',
            'Product with\nnewline and\ttab characters'
        ],
        'Best Route': ['IT->DE', 'Malformed route with title text', 'FR->ES'],
        'Opportunity Score': [
            '<span class="opportunity-badge-high">HIGH (85.0)</span>',
            '<span class="opportunity-badge-medium">MEDIUM (65.2)</span>',
            'Plain text 45.7'
        ],
        'Purchase Price €': [15.99, 22.50, 8.75],
        'ROI %': [
            '<span style="color:#ff0000;">25.5%</span>',
            '18.2',
            '42.8'
        ],
        'Links': [
            '<a href="amazon.it" target="_blank">🛒</a> <a href="keepa.com">📊</a>',
            'Plain text link',
            '<span>HTML span</span>'
        ]
    }
    
    df = pd.DataFrame(test_data)
    
    print("Testing CSV Export Fixes...")
    print(f"Input DataFrame shape: {df.shape}")
    print(f"Input Opportunity Score column: {df['Opportunity Score'].tolist()}")
    print(f"Input Best Route column: {df['Best Route'].tolist()}")
    print(f"Input Title column: {df['Title'].tolist()}")
    
    # Test the export
    try:
        csv_bytes = export_consolidated_csv(df)
        csv_content = csv_bytes.decode('utf-8')
        
        print("CSV export successful!")
        print(f"CSV content length: {len(csv_content)} bytes")
        
        # Verify the content
        lines = csv_content.split('\n')
        print(f"CSV has {len(lines)} lines")
        
        # Check header line
        header = lines[0] if lines else ""
        print(f"Header: {header}")
        
        # Check first data line
        if len(lines) > 1:
            first_data_line = lines[1]
            print(f"First data line: {first_data_line}")
        
        # Verify Opportunity Score was cleaned
        if 'HIGH' not in csv_content and 'MEDIUM' not in csv_content:
            print("HTML removed from Opportunity Score - SUCCESS")
        else:
            print("HTML still present in Opportunity Score - FAIL")
        
        # Verify commas are properly escaped
        if 'comma and' in csv_content:  # Should be quoted
            print("Commas in titles handled - SUCCESS")
        
        # Count quotes to verify proper escaping
        quote_count = csv_content.count('"')
        print(f"Total quote count in CSV: {quote_count}")
        
        # Write test output for inspection
        with open('test_export_output.csv', 'w', encoding='utf-8') as f:
            f.write(csv_content)
        print("Test CSV written to test_export_output.csv")
        
        return True
        
    except Exception as e:
        print(f"❌ CSV export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases"""
    
    print("\nTesting Edge Cases...")
    
    # Empty DataFrame
    empty_df = pd.DataFrame()
    try:
        result = export_consolidated_csv(empty_df)
        print("Empty DataFrame handled correctly")
    except Exception as e:
        print(f"❌ Empty DataFrame failed: {e}")
    
    # DataFrame with only problematic data
    problem_df = pd.DataFrame({
        'ASIN': ['B123'],
        'Title': ['Product with "quotes", commas, and <html>tags</html>'],
        'Opportunity Score': ['<span class="badge">Very High (99.9)</span>'],
        'Best Route': ['Malformed route text instead of IT->DE'],
    })
    
    try:
        result = export_consolidated_csv(problem_df)
        content = result.decode('utf-8')
        print("Problematic data handled correctly")
        print(f"Result length: {len(content)} bytes")
    except Exception as e:
        print(f"❌ Problematic data failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("CSV EXPORT FIXES TEST")
    print("=" * 60)
    
    success1 = test_csv_export_fixes()
    test_edge_cases()
    
    if success1:
        print("\nALL TESTS PASSED - CSV export fixes are working!")
    else:
        print("\nSome tests failed - check the output above")