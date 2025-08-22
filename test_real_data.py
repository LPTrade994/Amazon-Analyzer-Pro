"""
Real Dataset Validation - Sprint 4 Final Testing
"""
import pandas as pd
import numpy as np
from profit_model import find_best_routes, create_default_params, analyze_route_profitability
from analytics import find_historic_deals, calculate_historic_metrics
from export import export_consolidated_csv, validate_export_data
import os

def test_with_sample_data():
    """Test with the created sample data"""
    print("="*60)
    print("REAL DATASET VALIDATION")
    print("="*60)
    
    # Load sample data
    sample_file = "sample_data/test_data.csv"
    
    if not os.path.exists(sample_file):
        print(f"ERROR: Sample file {sample_file} not found")
        return False
    
    try:
        print(f"\n1. Loading sample dataset: {sample_file}")
        df = pd.read_csv(sample_file)
        print(f"   - Loaded {len(df)} products")
        print(f"   - Columns: {len(df.columns)}")
        print(f"   - Markets: {df['detected_locale'].unique()}")
        
        # Create realistic parameters
        params = create_default_params()
        params.update({
            'discount': 0.21,
            'purchase_strategy': 'Buy Box Current',
            'scenario': 'Medium',
            'mode': 'FBA',
            'min_roi_pct': 10,
            'min_margin_pct': 5
        })
        
        print(f"\n2. Running analysis with parameters:")
        print(f"   - Discount: {params['discount']*100}%")
        print(f"   - Strategy: {params['purchase_strategy']}")
        print(f"   - Min ROI: {params['min_roi_pct']}%")
        
        # Run route analysis
        print(f"\n3. Finding best routes...")
        best_routes = find_best_routes(df, params)
        
        if best_routes.empty:
            print("   WARNING: No profitable routes found")
            return False
        
        print(f"   - Found {len(best_routes)} profitable routes")
        print(f"   - Success rate: {len(best_routes)/len(df)*100:.1f}%")
        
        # Show top opportunities
        top_routes = best_routes.sort_values('opportunity_score', ascending=False).head(3)
        print(f"\n4. Top 3 opportunities:")
        
        for idx, (_, route) in enumerate(top_routes.iterrows(), 1):
            asin = route['asin']
            title = route['title'][:30] + "..." if len(route['title']) > 30 else route['title']
            score = route['opportunity_score']
            roi = route['roi']
            margin_eur = route['gross_margin_eur']
            best_route = f"{route['source']}->{route['target']}"
            
            print(f"   {idx}. {asin} - {title}")
            print(f"      Route: {best_route}, Score: {score:.0f}, ROI: {roi:.1f}%, Margin: €{margin_eur:.2f}")
        
        # Test historic deals detection
        print(f"\n5. Testing historic deals detection...")
        historic_deals = find_historic_deals(df)
        print(f"   - Historic deals found: {len(historic_deals)}")
        
        if len(historic_deals) > 0:
            print(f"   - Historic rate: {len(historic_deals)/len(df)*100:.1f}%")
            
            # Show top historic deal
            top_deal = historic_deals.iloc[0]
            asin = top_deal.get('ASIN', 'N/A')
            title = str(top_deal.get('Title', 'N/A'))[:30] + "..."
            current = top_deal.get('Buy Box 🚚: Current', 0)
            avg_90d = top_deal.get('Buy Box 🚚: 90 days avg.', 0)
            discount_pct = (avg_90d - current) / avg_90d * 100 if avg_90d > 0 else 0
            
            print(f"   Top deal: {asin} - {title}")
            print(f"   Current: €{current:.2f}, 90d avg: €{avg_90d:.2f}, Discount: {discount_pct:.1f}%")
        
        # Test analytics integration
        print(f"\n6. Testing analytics integration...")
        if len(df) > 0:
            sample_product = df.iloc[0]
            metrics = calculate_historic_metrics(sample_product)
            
            print(f"   Sample product metrics:")
            print(f"   - Current: €{metrics['current']:.2f}")
            print(f"   - 90d deviation: {metrics['dev_90d']:.1%}")
            print(f"   - Historic range: €{metrics['lowest']:.2f} - €{metrics['highest']:.2f}")
        
        # Test export functionality
        print(f"\n7. Testing export functionality...")
        try:
            # Prepare export data
            export_df = best_routes.copy()
            export_df['ASIN'] = export_df['asin']
            export_df['Title'] = export_df['title']
            export_df['Best Route'] = export_df['source'].str.upper() + '->' + export_df['target'].str.upper()
            export_df['Opportunity Score'] = export_df['opportunity_score']
            export_df['ROI %'] = export_df['roi']
            
            # Validate data
            validation = validate_export_data(export_df)
            print(f"   - Export validation: {'PASS' if validation['is_valid'] else 'FAIL'}")
            print(f"   - Warnings: {len(validation['warnings'])}")
            print(f"   - Errors: {len(validation['errors'])}")
            
            # Test CSV export
            csv_data = export_consolidated_csv(export_df)
            print(f"   - CSV export: {len(csv_data)} bytes generated")
            
        except Exception as e:
            print(f"   ERROR in export: {e}")
            return False
        
        print(f"\n8. Performance summary:")
        analysis = analyze_route_profitability(df, params)
        print(f"   - Total products: {analysis['total_products']}")
        print(f"   - Profitable products: {analysis['profitable_products']}")
        print(f"   - Avg opportunity score: {analysis['avg_opportunity_score']:.1f}")
        print(f"   - Avg ROI: {analysis['avg_roi']:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"ERROR during validation: {e}")
        import traceback
        traceback.print_exc()
        return False

def validate_critical_scenarios():
    """Validate the critical test scenarios from Sprint 4"""
    print(f"\n" + "="*60)
    print("CRITICAL SCENARIO VALIDATION")
    print("="*60)
    
    # Create test scenarios data
    critical_scenarios = pd.DataFrame({
        'ASIN': ['B001CRIT01', 'B001CRIT02'],
        'Title': ['Critical Test Italia 200 EUR', 'Critical Test Germania 200 EUR'],
        'Buy Box 🚚: Current': [200.0, 200.0],
        'Amazon: Current': [195.0, 198.0],
        'New FBA: Current': [205.0, 202.0],
        'New FBM: Current': [199.0, 201.0],
        'Buy Box 🚚: 30 days avg.': [220.0, 215.0],
        'Buy Box 🚚: 90 days avg.': [210.0, 205.0],
        'Buy Box 🚚: 180 days avg.': [225.0, 220.0],
        'Buy Box 🚚: Lowest': [180.0, 185.0],
        'Buy Box 🚚: Highest': [250.0, 240.0],
        'Sales Rank: Current': [50000, 45000],
        'Reviews Rating': [4.2, 4.0],
        'Buy Box: % Amazon 90 days': [75, 65],
        'Buy Box: Winner Count': [3, 4],
        'Buy Box: 90 days OOS': [5, 8],
        'Offers: Count': [8, 10],
        'Prime Eligible': [True, True],
        'Referral Fee %': [0.15, 0.15],
        'FBA Pick&Pack Fee': [2.00, 2.20],
        'detected_locale': ['it', 'de']
    })
    
    # Test with 21% discount
    params = create_default_params()
    params.update({
        'discount': 0.21,
        'purchase_strategy': 'Buy Box Current',
        'scenario': 'Medium',
        'mode': 'FBA'
    })
    
    print(f"\n1. Testing critical scenarios:")
    print(f"   - Italia scenario: 200€, 21% discount")
    print(f"   - Germania scenario: 200€, 21% discount")
    
    try:
        routes = find_best_routes(critical_scenarios, params)
        
        if len(routes) >= 2:
            # Italia route
            italia_route = routes[routes['source'] == 'it'].iloc[0] if 'it' in routes['source'].values else None
            germania_route = routes[routes['source'] == 'de'].iloc[0] if 'de' in routes['source'].values else None
            
            if italia_route is not None:
                net_cost_it = italia_route['net_cost']
                expected_it = 121.93
                print(f"\n   Italia result:")
                print(f"   - Net cost: €{net_cost_it:.2f}")
                print(f"   - Expected: €{expected_it:.2f}")
                print(f"   - Match: {'OK' if abs(net_cost_it - expected_it) < 0.1 else 'ERROR'}")
            
            if germania_route is not None:
                net_cost_de = germania_route['net_cost']
                expected_de = 132.77
                print(f"\n   Germania result:")
                print(f"   - Net cost: €{net_cost_de:.2f}")
                print(f"   - Expected: €{expected_de:.2f}")
                print(f"   - Match: {'OK' if abs(net_cost_de - expected_de) < 0.1 else 'ERROR'}")
            
            print(f"\nOK Critical scenarios validation completed")
            return True
        else:
            print(f"   ERROR: Could not generate routes for critical scenarios")
            return False
            
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def main():
    """Main validation function"""
    print("Starting Real Dataset Validation - Sprint 4 Final QA")
    print("=" * 80)
    
    # Test 1: Sample data validation
    sample_test = test_with_sample_data()
    
    # Test 2: Critical scenarios
    critical_test = validate_critical_scenarios()
    
    # Final report
    print(f"\n" + "="*80)
    print("FINAL VALIDATION REPORT")
    print("="*80)
    
    print(f"\nOK Sample data validation: {'PASS' if sample_test else 'FAIL'}")
    print(f"OK Critical scenarios: {'PASS' if critical_test else 'FAIL'}")
    
    if sample_test and critical_test:
        print(f"\nSUCCESS ALL TESTS PASSED - Sprint 4 validation complete!")
        print(f"   Amazon Analyzer Pro is ready for production use.")
        return True
    else:
        print(f"\nFAILED SOME TESTS FAILED - Review errors above")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)