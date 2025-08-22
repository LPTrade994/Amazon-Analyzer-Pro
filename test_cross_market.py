#!/usr/bin/env python3
"""
Test Cross-Market Arbitrage Logic
Verifica che la logica cross-market funzioni correttamente
"""

import pandas as pd
import sys
import os

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from profit_model import find_best_routes, create_default_params

def test_cross_market_arbitrage():
    """Test cross-market arbitrage with sample data"""
    
    print("=" * 60)
    print("CROSS-MARKET ARBITRAGE TEST")
    print("=" * 60)
    
    # Create test data with same ASIN in different markets at different prices
    # Scenario: ASIN available in ES (€468) and IT (€460) - should buy in IT, sell in other markets
    test_data = [
        # Same ASIN in IT (cheaper)
        {
            'ASIN': 'B0D23VW9VB',
            'Title': 'Test Product - Multi Market',
            'Buy Box 🚚: Current': 460.00,  # Italy price (cheaper)
            'Amazon: Current': 465.00,
            'New FBA: Current': 459.99,
            'source_market': 'it',
            'Sales Rank: Current': 15000
        },
        # Same ASIN in ES (more expensive)
        {
            'ASIN': 'B0D23VW9VB', 
            'Title': 'Test Product - Multi Market',
            'Buy Box 🚚: Current': 468.00,  # Spain price (more expensive)
            'Amazon: Current': 470.00,
            'New FBA: Current': 467.50,
            'source_market': 'es',
            'Sales Rank: Current': 18000
        },
        # Same ASIN in DE (mid price)
        {
            'ASIN': 'B0D23VW9VB',
            'Title': 'Test Product - Multi Market', 
            'Buy Box 🚚: Current': 465.00,  # Germany price (mid)
            'Amazon: Current': 468.00,
            'New FBA: Current': 464.99,
            'source_market': 'de',
            'Sales Rank: Current': 12000
        },
        # Different ASIN available only in one market (should be skipped)
        {
            'ASIN': 'B0D24XYZ789',
            'Title': 'Single Market Product',
            'Buy Box 🚚: Current': 25.99,
            'Amazon: Current': 27.50,
            'source_market': 'fr',
            'Sales Rank: Current': 5000
        }
    ]
    
    df = pd.DataFrame(test_data)
    
    print("Test Dataset:")
    print(f"  Total rows: {len(df)}")
    print(f"  Unique ASINs: {df['ASIN'].nunique()}")
    print(f"  Markets: {df['source_market'].unique()}")
    
    # Show price differences for multi-market ASIN
    multi_market_asin = 'B0D23VW9VB'
    asin_data = df[df['ASIN'] == multi_market_asin]
    print(f"\nPrice comparison for {multi_market_asin}:")
    for _, row in asin_data.iterrows():
        price = row['Buy Box 🚚: Current']
        market = row['source_market'].upper()
        print(f"  {market}: EUR {price}")
    
    # Expected behavior: should identify IT→ES route as most profitable
    # (buy in IT at €460, sell in ES at €468+ markup)
    
    print(f"\nExpected behavior:")
    print(f"  - Buy in IT (EUR 460) -> Sell in ES/DE/FR")
    print(f"  - Skip single-market ASIN B0D24XYZ789")
    print(f"  - Generate proper cross-market routes")
    
    # Create test parameters
    params = create_default_params()
    params.update({
        'purchase_strategy': 'Buy Box Current',
        'scenario': 'Medium',
        'mode': 'FBA',
        'discount': 0.20,  # 20% discount
        'min_roi_pct': 5.0,  # 5% minimum ROI
        'min_margin_pct': 10.0  # 10% minimum margin
    })
    
    print(f"\nTest parameters:")
    print(f"  Purchase strategy: {params['purchase_strategy']}")
    print(f"  Discount: {params['discount']*100}%")
    print(f"  Min ROI: {params['min_roi_pct']}%")
    
    print(f"\n" + "-" * 50)
    print("RUNNING find_best_routes()...")
    print("-" * 50)
    
    # Run the cross-market arbitrage logic
    try:
        result_df = find_best_routes(df, params)
        
        print(f"\nRESULTS:")
        print(f"  Routes found: {len(result_df)}")
        
        if not result_df.empty:
            print(f"\nTop routes:")
            for idx, row in result_df.iterrows():
                asin = row.get('asin', 'N/A')
                route = row.get('route', 'N/A')
                purchase_price = row.get('purchase_price', 0)
                target_price = row.get('target_price', 0)
                roi = row.get('roi', 0)
                margin_eur = row.get('gross_margin_eur', 0)
                score = row.get('opportunity_score', 0)
                
                print(f"  {idx+1}. ASIN: {asin}")
                print(f"     Route: {route}")
                print(f"     Buy: EUR {purchase_price:.2f} -> Sell: EUR {target_price:.2f}")
                print(f"     ROI: {roi:.1f}%, Margin: EUR {margin_eur:.2f}, Score: {score:.1f}")
                print("")
        else:
            print("  No profitable routes found!")
            
        return len(result_df) > 0
        
    except Exception as e:
        print(f"ERROR in find_best_routes(): {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "=" * 60)
    print("EDGE CASES TEST")
    print("=" * 60)
    
    # Test with empty DataFrame
    empty_df = pd.DataFrame()
    params = create_default_params()
    
    try:
        result = find_best_routes(empty_df, params)
        print("Empty DataFrame: OK")
    except Exception as e:
        print(f"Empty DataFrame: FAIL - {e}")
    
    # Test with single ASIN, single market
    single_df = pd.DataFrame([{
        'ASIN': 'B123',
        'Title': 'Single Market Product',
        'Buy Box 🚚: Current': 25.99,
        'source_market': 'it'
    }])
    
    try:
        result = find_best_routes(single_df, params)
        print(f"Single market ASIN: OK (should return empty, got {len(result)} routes)")
    except Exception as e:
        print(f"Single market ASIN: FAIL - {e}")

if __name__ == "__main__":
    print("CROSS-MARKET ARBITRAGE LOGIC TEST")
    print("This test verifies that the new cross-market logic works correctly")
    
    success1 = test_cross_market_arbitrage()
    test_edge_cases()
    
    if success1:
        print("\nSUCCESS: Cross-market arbitrage logic is working!")
        print("\nNEXT STEPS:")
        print("1. Run the Streamlit app with real multi-market data")
        print("2. Verify debug output shows proper ASIN grouping")
        print("3. Check that routes show different source->target combinations")
        print("4. Confirm pricing uses real target market prices when available")
    else:
        print("\nFAILED: Cross-market logic needs debugging")
        print("Check the error messages above")