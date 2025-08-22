"""
Test Export Functionality - Sprint 4 Testing
"""
import pandas as pd
import json
from export import export_consolidated_csv, export_watchlist_json, create_summary_report, validate_export_data

def test_export_functionality():
    """Test all export functions with sample data"""
    print("="*60)
    print("TESTING EXPORT FUNCTIONALITY")
    print("="*60)
    
    # Create sample test data
    test_data = {
        'ASIN': ['B001TEST01', 'B001TEST02', 'B001TEST03'],
        'Title': ['Test Product Italia', 'Test Product Germania', 'Test Product Francia'],
        'Best Route': ['IT->IT', 'DE->IT', 'FR->IT'],
        'Purchase Price €': [200.0, 200.0, 150.0],
        'Net Cost €': [121.93, 132.77, 106.25],
        'Target Price €': [200.0, 200.0, 150.0],
        'Fees €': ['€30.00', '€30.00', '€22.50'],
        'Gross Margin €': [48.07, 37.23, 21.25],
        'Gross Margin %': [24.0, 18.6, 14.2],
        'ROI %': [39.4, 28.0, 20.0],
        'Opportunity Score': [85, 72, 65],
        'velocity_score': [75, 68, 60],
        'risk_score': [25, 35, 40],
        'is_historic_deal': [True, False, True]
    }
    
    df = pd.DataFrame(test_data)
    
    # Test 1: CSV Export
    print("\n1. Testing CSV Export...")
    try:
        csv_data = export_consolidated_csv(df)
        print(f"OK CSV Export successful - Size: {len(csv_data)} bytes")
        
        # Verify CSV content
        csv_str = csv_data.decode('utf-8')
        lines = csv_str.split('\n')
        print(f"   - Lines: {len(lines)}")
        print(f"   - Header: {lines[0][:100]}...")
        
    except Exception as e:
        print(f"ERROR CSV Export failed: {e}")
    
    # Test 2: Watchlist JSON Export
    print("\n2. Testing Watchlist JSON Export...")
    try:
        selected_asins = ['B001TEST01', 'B001TEST03']
        params = {
            'discount': 0.21,
            'purchase_strategy': 'Buy Box Current',
            'scenario': 'Medium',
            'mode': 'FBA'
        }
        
        json_data = export_watchlist_json(selected_asins, df, params)
        json_obj = json.loads(json_data)
        
        print(f"OK JSON Export successful")
        print(f"   - Items in watchlist: {len(json_obj['watchlist'])}")
        print(f"   - Valid items: {json_obj['summary']['valid_items']}")
        print(f"   - Historic deals: {json_obj['summary']['historic_deals_count']}")
        
    except Exception as e:
        print(f"ERROR JSON Export failed: {e}")
    
    # Test 3: Summary Report
    print("\n3. Testing Summary Report...")
    try:
        params = {
            'discount': 0.21,
            'purchase_strategy': 'Buy Box Current',
            'scenario': 'Medium',
            'mode': 'FBA'
        }
        
        report = create_summary_report(df, params)
        lines = report.split('\n')
        
        print(f"OK Report generation successful")
        print(f"   - Report lines: {len(lines)}")
        print(f"   - Contains header: {'Amazon Analyzer Pro' in report}")
        print(f"   - Contains parameters: {'Parametri Analisi' in report}")
        print(f"   - Contains top opportunities: {'Top 10 Opportunità' in report}")
        
    except Exception as e:
        print(f"ERROR Report generation failed: {e}")
    
    # Test 4: Data Validation
    print("\n4. Testing Data Validation...")
    try:
        validation = validate_export_data(df)
        
        print(f"OK Validation successful")
        print(f"   - Is valid: {validation['is_valid']}")
        print(f"   - Warnings: {len(validation['warnings'])}")
        print(f"   - Errors: {len(validation['errors'])}")
        print(f"   - Total rows: {validation['stats']['total_rows']}")
        print(f"   - Total columns: {validation['stats']['total_columns']}")
        
        if validation['warnings']:
            for warning in validation['warnings']:
                print(f"   - Warning: {warning}")
                
        if validation['errors']:
            for error in validation['errors']:
                print(f"   - Error: {error}")
        
    except Exception as e:
        print(f"ERROR Validation failed: {e}")
    
    # Test 5: Edge Cases
    print("\n5. Testing Edge Cases...")
    
    # Empty DataFrame
    empty_df = pd.DataFrame()
    try:
        csv_empty = export_consolidated_csv(empty_df)
        validation_empty = validate_export_data(empty_df)
        
        print(f"OK Empty DataFrame handled correctly")
        print(f"   - Empty CSV size: {len(csv_empty)} bytes")
        print(f"   - Empty validation valid: {validation_empty['is_valid']}")
        
    except Exception as e:
        print(f"ERROR Empty DataFrame test failed: {e}")
    
    # Missing columns DataFrame
    try:
        minimal_df = pd.DataFrame({
            'ASIN': ['TEST'],
            'Title': ['Test Product']
        })
        
        validation_minimal = validate_export_data(minimal_df)
        print(f"OK Minimal DataFrame validation: Valid={validation_minimal['is_valid']}")
        
    except Exception as e:
        print(f"ERROR Minimal DataFrame test failed: {e}")
    
    print("\n" + "="*60)
    print("EXPORT TESTING COMPLETED")
    print("="*60)

if __name__ == '__main__':
    test_export_functionality()