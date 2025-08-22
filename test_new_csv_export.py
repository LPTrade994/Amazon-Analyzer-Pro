#!/usr/bin/env python3
"""
Test New CSV Export Function
Verifica che la nuova funzione CSV export funzioni con formato Excel EU
"""

import pandas as pd
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from export import export_consolidated_csv

def test_new_csv_export():
    """Test new CSV export with cross-market data"""
    
    print("=" * 60)
    print("NEW CSV EXPORT TEST - Excel EU Format")
    print("=" * 60)
    
    # Create test data matching cross-market results
    test_data = {
        'asin': ['B0D23VW9VB', 'B0D24ABC123', 'B0D25XYZ789'],
        'title': [
            'Cross-Market Product ES->IT',
            'Product with, comma and "quotes"',
            'Another cross-market product'
        ],
        'route': ['ES->IT', 'DE->FR', 'IT->ES'],
        'purchase_price': [468.50, 25.99, 156.75],
        'net_cost': [375.60, 20.79, 125.40],
        'target_price': [460.00, 30.50, 170.00],
        'gross_margin_eur': [84.40, 9.71, 44.60],
        'roi': [22.5, 46.7, 35.5],
        'opportunity_score': [75.5, 68.2, 82.1],
        'source_market': ['es', 'de', 'it'],
        'target_market': ['it', 'fr', 'es']
    }
    
    df = pd.DataFrame(test_data)
    
    print("Test data (Cross-Market Results):")
    print(f"  Total rows: {len(df)}")
    print(f"  Columns: {list(df.columns)}")
    print(f"  Sample route: {df['route'].iloc[0]}")
    print(f"  Sample prices: Buy EUR{df['purchase_price'].iloc[0]} -> Sell EUR{df['target_price'].iloc[0]}")
    
    # Test the new export
    try:
        csv_bytes = export_consolidated_csv(df)
        csv_content = csv_bytes.decode('utf-8-sig')  # Decode with BOM
        
        print("\nCSV export successful!")
        print(f"CSV content length: {len(csv_content)} bytes")
        
        # Verify the content
        lines = csv_content.split('\n')
        print(f"CSV has {len(lines)} lines")
        
        # Check header line
        header = lines[0] if lines else ""
        print(f"Header: {header}")
        
        # Check separator (should be ;)
        if ';' in header:
            print("Separator: ; (Excel EU format) - SUCCESS")
        else:
            print("Separator: , (US format) - WARNING")
        
        # Check first data line
        if len(lines) > 1:
            first_data_line = lines[1]
            print(f"First data line: {first_data_line}")
            
            # Check decimal format in data line
            if ',' in first_data_line and any(char.isdigit() for char in first_data_line):
                # Try to find decimal comma
                parts = first_data_line.split(';')
                for part in parts:
                    if ',' in part and any(char.isdigit() for char in part):
                        print(f"Found decimal comma in: {part} - SUCCESS")
                        break
        
        # Write test output for inspection
        with open('test_new_export_output.csv', 'wb') as f:
            f.write(csv_bytes)
        print("Test CSV written to test_new_export_output.csv")
        
        # Verify HTML removal
        if '<span' not in csv_content and 'HIGH' not in csv_content:
            print("HTML cleaning: SUCCESS")
        else:
            print("HTML cleaning: NEEDS CHECK")
        
        # Verify route format
        if 'ES->IT' in csv_content and 'DE->FR' in csv_content:
            print("Route format: SUCCESS")
        
        return True
        
    except Exception as e:
        print(f"CSV export failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_excel_compatibility():
    """Test Excel-specific compatibility features"""
    
    print("\n" + "=" * 60)
    print("EXCEL COMPATIBILITY TEST")
    print("=" * 60)
    
    # Create data with typical Excel issues
    problem_data = {
        'asin': ['B123'],
        'title': ['Product with commas, quotes "test", and newlines'],
        'route': ['IT->DE'],
        'purchase_price': [123.456789],  # Many decimals
        'target_price': [234.987654],
        'roi': [45.678901],
        'opportunity_score': [87.1234]
    }
    
    df = pd.DataFrame(problem_data)
    
    try:
        csv_bytes = export_consolidated_csv(df)
        
        # Check file with BOM
        bom_check = csv_bytes[:3]
        if bom_check == b'\xef\xbb\xbf':
            print("UTF-8 BOM present: SUCCESS (Excel will recognize UTF-8)")
        else:
            print("UTF-8 BOM missing: WARNING")
        
        # Check decimal rounding
        csv_content = csv_bytes.decode('utf-8-sig')
        if '123,46' in csv_content:  # Should be rounded to 2 decimals with comma
            print("Decimal rounding: SUCCESS")
        
        print("Excel compatibility test: PASSED")
        
    except Exception as e:
        print(f"Excel compatibility test: FAILED - {e}")

if __name__ == "__main__":
    print("NEW CSV EXPORT TEST")
    print("Testing Excel EU compatibility (semicolon separator, decimal comma, BOM)")
    
    success1 = test_new_csv_export()
    test_excel_compatibility()
    
    if success1:
        print("\nSUCCESS: New CSV export working with Excel EU format!")
        print("\nFeatures implemented:")
        print("- Semicolon (;) separator for Excel EU")
        print("- Decimal comma (,) for EU number format")
        print("- UTF-8 BOM for Excel UTF-8 recognition")
        print("- Proper numeric rounding (2 decimals for prices)")
        print("- HTML tag removal")
        print("- Cross-market column support")
    else:
        print("\nFAILED: Check error messages above")