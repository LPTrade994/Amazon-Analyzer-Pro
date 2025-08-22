"""
Simple test for enhanced export functionality without Unicode issues
"""

import pandas as pd
import sys
import os

# Add the project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from export import export_consolidated_csv, export_executive_summary


def main():
    print("=" * 60)
    print("TESTING ENHANCED EXPORT FUNCTIONALITY")
    print("=" * 60)
    
    # Create test data
    test_data = pd.DataFrame({
        'ASIN': ['B006JH8T3S', 'B08N5WRWNW'],
        'Title': ['Logitech C920 HD Pro Webcam', 'Sony WH-1000XM4 Headphones'],
        'Best Route': ['DE->IT', 'ES->FR'],
        'Purchase Price €': [54.90, 279.99],
        'Net Cost €': [36.45, 186.39],
        'Target Price €': [59.99, 319.99],
        'Gross Margin €': [12.85, 67.18],
        'ROI %': [35.2, 36.0],
        'roi': [35.2, 36.0],
        'Opportunity Score': [78, 82],
        'Velocity Score': [75, 68],
        'Risk Score': [35, 42],
        'Fees €': [7.38, 26.42]
    })
    
    print("Test data created with {} rows".format(len(test_data)))
    
    # Test CSV export
    try:
        csv_bytes = export_consolidated_csv(test_data, action_ready=True)
        csv_content = csv_bytes.decode('utf-8-sig')
        
        print("CSV Export: SUCCESS")
        print("CSV size: {} bytes".format(len(csv_bytes)))
        
        # Check for action-ready columns
        action_columns = ['Action Required', 'Budget Needed', 'Expected Profit 30d', 'Break Even Units']
        found_columns = [col for col in action_columns if col in csv_content]
        print("Action columns found: {}/{}".format(len(found_columns), len(action_columns)))
        
        # Check for summary row
        if 'TOTALS/AVG' in csv_content:
            print("Summary row: FOUND")
        else:
            print("Summary row: MISSING")
            
    except Exception as e:
        print("CSV Export: FAILED - {}".format(e))
    
    # Test Executive Summary
    try:
        params = {'purchase_strategy': 'Buy Box Current', 'discount': 0.21}
        summary = export_executive_summary(test_data, params)
        
        print("Executive Summary: SUCCESS")
        print("Summary length: {} characters".format(len(summary)))
        
        # Check for key sections
        key_sections = ['Executive Summary', 'BUSINESS METRICS', 'OPPORTUNITIES', 'RISK ANALYSIS']
        found_sections = [section for section in key_sections if section in summary]
        print("Key sections found: {}/{}".format(len(found_sections), len(key_sections)))
        
    except Exception as e:
        print("Executive Summary: FAILED - {}".format(e))
    
    print("=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()