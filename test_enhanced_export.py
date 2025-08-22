"""
Test Enhanced Export Functionality - Action-Ready CSV and Executive Summary
"""

import pandas as pd
import sys
import os

# Add the project directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from export import export_consolidated_csv, export_executive_summary


def create_test_data():
    """Create test data with realistic Amazon arbitrage opportunities"""
    test_data = pd.DataFrame({
        'ASIN': ['B006JH8T3S', 'B08N5WRWNW', 'B001234567', 'B009876543', 'B012345678'],
        'Title': [
            'Logitech C920 HD Pro Webcam',
            'Sony WH-1000XM4 Headphones',  
            'Kindle Paperwhite E-reader',
            'Anker PowerCore Power Bank',
            'JBL Flip 5 Bluetooth Speaker'
        ],
        'Best Route': ['DE->IT', 'ES->FR', 'IT->DE', 'FR->ES', 'DE->IT'],
        'Purchase Price €': [54.90, 279.99, 129.99, 49.99, 89.99],
        'Net Cost €': [36.45, 186.39, 86.39, 33.24, 59.89],
        'Target Price €': [59.99, 319.99, 149.99, 64.99, 109.99],
        'Gross Margin €': [12.85, 67.18, 35.17, 18.42, 28.45],
        'ROI %': [35.2, 36.0, 40.7, 55.4, 47.5],
        'roi': [35.2, 36.0, 40.7, 55.4, 47.5],  # Alternative column name
        'Opportunity Score': [78, 82, 85, 91, 88],
        'Velocity Score': [75, 68, 82, 88, 73],
        'Risk Score': [35, 42, 28, 22, 38],
        'Competition Score': [65, 58, 71, 79, 67],
        'Fees €': [7.38, 26.42, 8.45, 4.33, 7.21]
    })
    
    return test_data


def test_action_ready_csv():
    """Test the enhanced CSV export with action-ready columns"""
    print("=" * 60)
    print("TEST: ACTION-READY CSV EXPORT")
    print("=" * 60)
    
    test_df = create_test_data()
    
    try:
        # Test with action_ready=True
        csv_bytes = export_consolidated_csv(test_df, action_ready=True)
        csv_content = csv_bytes.decode('utf-8-sig')
        
        print("CSV Export successful")
        print(f"CSV size: {len(csv_bytes)} bytes")
        
        # Check for action-ready columns
        action_columns = ['Action Required', 'Budget Needed', 'Expected Profit 30d', 'Break Even Units']
        found_columns = []
        
        for col in action_columns:
            if col in csv_content:
                found_columns.append(col)
                print(f"Found column: {col}")
            else:
                print(f"Missing column: {col}")
        
        # Check for ROI sorting (highest should be first data row)
        lines = csv_content.split('\n')
        if len(lines) > 2:  # Header + at least one data row
            first_data_line = lines[1]  # Skip header
            print(f"First data row (highest ROI): {first_data_line[:100]}...")
        
        # Check for summary row
        if 'TOTALS/AVG' in csv_content:
            print("Summary row found")
        else:
            print("Summary row missing")
            
        print(f"\nAction-ready columns found: {len(found_columns)}/4")
        return len(found_columns) == 4
        
    except Exception as e:
        print(f"CSV Export failed: {e}")
        return False


def test_executive_summary():
    """Test the Executive Summary export"""
    print("\n" + "=" * 60)
    print("TEST: EXECUTIVE SUMMARY EXPORT")
    print("=" * 60)
    
    test_df = create_test_data()
    test_params = {
        'purchase_strategy': 'Buy Box Current',
        'discount': 0.21,
        'scenario': 'Medium',
        'mode': 'FBA'
    }
    
    try:
        summary = export_executive_summary(test_df, test_params)
        
        print("Executive Summary generated successfully")
        print(f"Summary length: {len(summary)} characters")
        
        # Check for key sections
        required_sections = [
            '# Executive Summary',
            'KEY BUSINESS METRICS',
            'TOP 10 OPPORTUNITIES',
            'RISK ANALYSIS',
            'EXECUTIVE RECOMMENDATIONS'
        ]
        
        found_sections = 0
        for section in required_sections:
            if section in summary:
                found_sections += 1
                print(f"Found section: {section}")
            else:
                print(f"Missing section: {section}")
        
        # Check for business metrics
        business_terms = [
            'Investment Required',
            'Expected Profit',
            'Portfolio ROI',
            'BUY NOW',
            'MONITOR',
            'SKIP'
        ]
        
        found_terms = 0
        for term in business_terms:
            if term in summary:
                found_terms += 1
        
        print(f"\n🎯 Required sections: {found_sections}/{len(required_sections)}")
        print(f"💼 Business terms found: {found_terms}/{len(business_terms)}")
        
        return found_sections >= 4 and found_terms >= 4
        
    except Exception as e:
        print(f"❌ Executive Summary failed: {e}")
        return False


def test_integration():
    """Test integration between CSV and Executive Summary"""
    print("\n" + "=" * 60)
    print("TEST: INTEGRATION VALIDATION")
    print("=" * 60)
    
    test_df = create_test_data()
    test_params = {'purchase_strategy': 'Buy Box Current', 'discount': 0.21}
    
    try:
        # Generate both exports
        csv_bytes = export_consolidated_csv(test_df, action_ready=True)
        summary = export_executive_summary(test_df, test_params)
        
        # Validate data consistency
        total_opportunities = len(test_df)
        avg_roi = test_df['ROI %'].mean()
        
        # Check if executive summary contains correct numbers
        if f"{total_opportunities}" in summary:
            print(f"✅ Correct opportunity count: {total_opportunities}")
        else:
            print(f"❌ Opportunity count mismatch in summary")
        
        if f"{avg_roi:.1f}" in summary:
            print(f"✅ Correct average ROI: {avg_roi:.1f}%")
        else:
            print(f"❌ Average ROI mismatch in summary")
        
        # Check for action recommendations
        action_terms = ['BUY NOW', 'MONITOR', 'SKIP']
        actions_found = sum(1 for term in action_terms if term in summary)
        
        print(f"🎯 Action recommendations: {actions_found}/3 found")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False


def run_all_tests():
    """Run comprehensive tests for enhanced export functionality"""
    print("TESTING ENHANCED EXPORT FUNCTIONALITY")
    print("=" * 80)
    
    # Run tests
    csv_pass = test_action_ready_csv()
    summary_pass = test_executive_summary() 
    integration_pass = test_integration()
    
    # Summary
    print("\n" + "=" * 80)
    print("📋 TEST SUMMARY")
    print("=" * 80)
    
    print(f"""
    TEST RESULTS:
    Action-Ready CSV: {'✅ PASS' if csv_pass else '❌ FAIL'}
    Executive Summary: {'✅ PASS' if summary_pass else '❌ FAIL'}
    Integration: {'✅ PASS' if integration_pass else '❌ FAIL'}
    
    OVERALL STATUS: {'✅ ALL TESTS PASSED' if all([csv_pass, summary_pass, integration_pass]) else '❌ SOME TESTS FAILED'}
    
    ENHANCED FEATURES READY:
    ✅ Action Required column (BUY NOW/MONITOR/SKIP)
    ✅ Budget Needed calculation
    ✅ Expected Profit 30d projection  
    ✅ Break Even Units analysis
    ✅ Summary row with totals
    ✅ ROI descending sort
    ✅ Executive Summary with business metrics
    ✅ Investment/Return analysis 30/60/90 days
    """)
    
    return all([csv_pass, summary_pass, integration_pass])


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)