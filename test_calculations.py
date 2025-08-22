"""
Test Calculations Module - Validate ROI and Profit Mathematics

This module contains comprehensive tests to validate the accuracy of:
- Net cost calculations with VAT and discounts
- Cross-market revenue calculations 
- Amazon fees (referral + FBA)
- Hidden costs (shipping, returns, storage, misc)
- Final ROI and profit calculations

Run this module to verify mathematical accuracy before production use.
"""

import pandas as pd
import sys
import os

# Add the project directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import VAT_RATES, HIDDEN_COSTS
from profit_model import compute_route_metrics, compute_fees
from pricing import select_purchase_price, compute_net_purchase


def test_roi_calculation():
    """
    Test case with real Logitech C920 numbers
    Expected ROI should be around 25% (realistic range 20-30%)
    """
    print("=" * 60)
    print("TEST CASE 1: LOGITECH C920 (DE->IT)")
    print("=" * 60)
    
    # Input data
    purchase_price = 54.90  # DE price
    vat_de = 0.19
    discount = 0.21
    
    # Target market
    target_price = 59.99  # IT price
    vat_it = 0.22
    referral_fee_pct = 0.15
    fba_fee = 2.50
    
    # STEP 1: Calculate Net Cost (with VAT removal and discount)
    price_ex_vat = purchase_price / (1 + vat_de)
    net_cost = price_ex_vat * (1 - discount)
    
    # STEP 2: Calculate Revenue (ex VAT for Italy)
    revenue_ex_vat = target_price / (1 + vat_it)
    
    # STEP 3: Calculate Amazon Fees
    referral_fee = revenue_ex_vat * referral_fee_pct
    total_fees = referral_fee + fba_fee
    
    # STEP 4: Add Hidden Costs (from config) 
    hidden_shipping = HIDDEN_COSTS['shipping_avg']
    hidden_misc = HIDDEN_COSTS['misc_costs']
    hidden_returns = target_price * HIDDEN_COSTS['returns_rate']
    hidden_storage = target_price * HIDDEN_COSTS['storage_rate']
    
    total_hidden = hidden_shipping + hidden_misc + hidden_returns + hidden_storage
    
    # STEP 5: Calculate Final Profit and ROI
    total_cost = net_cost + 2.0 + total_hidden  # +2.0 for inbound logistics
    net_revenue = revenue_ex_vat - total_fees
    profit = net_revenue - total_cost
    roi = (profit / total_cost) * 100
    
    # STEP 6: Legacy ROI (without hidden costs) for comparison
    legacy_cost = net_cost + 2.0
    legacy_profit = revenue_ex_vat - total_fees - legacy_cost
    legacy_roi = (legacy_profit / legacy_cost) * 100
    
    print(f"""
    PURCHASE ANALYSIS:
    Original Price (DE): €{purchase_price}
    Price ex-VAT (19%): €{price_ex_vat:.2f}
    Net Cost (21% discount): €{net_cost:.2f}
    
    REVENUE ANALYSIS:
    Target Price (IT): €{target_price}
    Revenue ex-VAT (22%): €{revenue_ex_vat:.2f}
    
    FEES BREAKDOWN:
    Referral Fee (15%): €{referral_fee:.2f}
    FBA Fee: €{fba_fee:.2f}
    Total Amazon Fees: €{total_fees:.2f}
    
    HIDDEN COSTS:
    Shipping: €{hidden_shipping:.2f}
    Misc: €{hidden_misc:.2f}
    Returns (3%): €{hidden_returns:.2f}
    Storage (1.5%): €{hidden_storage:.2f}
    Total Hidden: €{total_hidden:.2f}
    
    FINAL CALCULATION:
    Total Cost: €{total_cost:.2f}
    Net Revenue: €{net_revenue:.2f}
    Profit: €{profit:.2f}
    ROI: {roi:.1f}%
    
    COMPARISON:
    Legacy ROI (no hidden costs): {legacy_roi:.1f}%
    New ROI (with hidden costs): {roi:.1f}%
    Difference: {legacy_roi - roi:.1f}%
    
    VALIDATION:
    Expected ROI Range: 10-20%
    Calculated ROI: {roi:.1f}%
    PASS: {10 <= roi <= 20}
    """)
    
    return roi, 10 <= roi <= 20


def test_system_integration():
    """
    Test using actual system functions to ensure integration works
    """
    print("=" * 60)
    print("TEST CASE 2: SYSTEM INTEGRATION")
    print("=" * 60)
    
    # Create mock data row
    test_row = pd.Series({
        'ASIN': 'B006JH8T3S',
        'Title': 'Logitech C920 HD Pro Webcam',
        'Buy Box 🚚: Current': 54.90,
        'Amazon: Current': 52.90,
        'New FBA: Current': 55.90,
        'Referral Fee %': 0.15,
        'FBA Pick&Pack Fee': 2.50,
        'Return Rate': 5.0,
        'Reviews: Rating': 4.5,
        'Total Offer Count': 8
    })
    
    # Test parameters
    params = {
        'purchase_strategy': 'Buy Box Current',
        'scenario': 'Medium',
        'mode': 'FBA',
        'discount': 0.21,
        'inbound_logistics': 2.0,
        'vat_rates': VAT_RATES,
        'scoring_weights': {'profit': 0.5, 'velocity': 0.3, 'competition': 0.2},
        'min_roi_pct': 10.0,
        'min_margin_pct': 15.0
    }
    
    try:
        # Test the actual system calculation
        route_metrics = compute_route_metrics(
            test_row, 
            'de',
            'it', 
            params,
            custom_target_price=59.99
        )
        
        print(f"""
        SYSTEM INTEGRATION TEST:
        Source: DE
        Target: IT
        Purchase Price: €{route_metrics['purchase_price']:.2f}
        Net Cost: €{route_metrics['net_cost']:.2f}
        Target Price: €{route_metrics['target_price']:.2f}
        Total Cost: €{route_metrics['total_cost']:.2f}
        Net Profit: €{route_metrics['net_profit']:.2f}
        ROI: {route_metrics['roi']:.1f}%
        
        COST BREAKDOWN:
        Product Cost: €{route_metrics['cost_breakdown']['product_cost']:.2f}
        Inbound Logistics: €{route_metrics['cost_breakdown']['inbound_logistics']:.2f}
        Shipping: €{route_metrics['cost_breakdown']['shipping']:.2f}
        Returns Loss: €{route_metrics['cost_breakdown']['returns_loss']:.2f}
        Storage: €{route_metrics['cost_breakdown']['storage']:.2f}
        Misc: €{route_metrics['cost_breakdown']['misc']:.2f}
        Amazon Fees: €{route_metrics['cost_breakdown']['amazon_fees']:.2f}
        
        VALIDATION:
        System ROI: {route_metrics['roi']:.1f}%
        Expected Range: 8-15%
        PASS: {8 <= route_metrics['roi'] <= 15}
        """)
        
        return route_metrics['roi'], 8 <= route_metrics['roi'] <= 15
        
    except Exception as e:
        print(f"SYSTEM INTEGRATION ERROR: {e}")
        return 0, False


def test_edge_cases():
    """
    Test edge cases that might break the system
    """
    print("=" * 60)
    print("TEST CASE 3: EDGE CASES")
    print("=" * 60)
    
    edge_cases = [
        {
            'name': 'Very Low Price',
            'purchase': 5.99,
            'target': 8.99,
            'expected_roi_range': (10, 50)
        },
        {
            'name': 'High Price Product',
            'purchase': 299.99,
            'target': 349.99,
            'expected_roi_range': (5, 25)
        },
        {
            'name': 'Minimal Margin',
            'purchase': 49.99,
            'target': 51.99,
            'expected_roi_range': (-10, 10)  # Might be negative
        }
    ]
    
    results = []
    
    for case in edge_cases:
        print(f"\n--- {case['name']} ---")
        
        # Quick calculation
        net_cost = (case['purchase'] / 1.19) * 0.79  # DE VAT + 21% discount
        revenue = case['target'] / 1.22  # IT VAT
        fees = revenue * 0.15 + 2.5  # 15% referral + 2.5 FBA
        hidden = 5 + 2 + (case['target'] * 0.03) + (case['target'] * 0.015)  # Hidden costs
        total_cost = net_cost + 2 + hidden
        profit = revenue - fees - total_cost
        roi = (profit / total_cost) * 100
        
        print(f"Purchase: €{case['purchase']:.2f}")
        print(f"Target: €{case['target']:.2f}")
        print(f"Calculated ROI: {roi:.1f}%")
        print(f"Expected Range: {case['expected_roi_range'][0]}-{case['expected_roi_range'][1]}%")
        
        in_range = case['expected_roi_range'][0] <= roi <= case['expected_roi_range'][1]
        print(f"PASS: {in_range}")
        
        results.append({
            'case': case['name'],
            'roi': roi,
            'pass': in_range
        })
    
    return results


def test_csv_sample():
    """
    Test with sample CSV data to validate against real dataset
    """
    print("=" * 60)
    print("TEST CASE 4: CSV SAMPLE VALIDATION")
    print("=" * 60)
    
    # Sample products with known good data
    sample_products = [
        {
            'name': 'Electronics - Medium Price',
            'asin': 'B08N5WRWNW',
            'buy_box_current': 79.99,
            'amazon_current': 75.99,
            'target_estimate': 89.99,
            'referral_pct': 0.08,  # Electronics typically 8%
            'fba_fee': 3.5
        },
        {
            'name': 'Books - Low Price',
            'asin': 'B001234567',
            'buy_box_current': 15.99,
            'amazon_current': 14.99,
            'target_estimate': 18.99,
            'referral_pct': 0.15,  # Books typically 15%
            'fba_fee': 2.0
        },
        {
            'name': 'Tools - High Price',
            'asin': 'B009876543',
            'buy_box_current': 199.99,
            'amazon_current': 189.99,
            'target_estimate': 229.99,
            'referral_pct': 0.15,  # Tools typically 15%
            'fba_fee': 5.0
        }
    ]
    
    results = []
    suspicious_count = 0
    
    for product in sample_products:
        print(f"\n--- {product['name']} ---")
        
        # Quick ROI calculation
        purchase = product['buy_box_current']
        target = product['target_estimate']
        
        net_cost = (purchase / 1.19) * 0.79
        revenue = target / 1.22
        fees = revenue * product['referral_pct'] + product['fba_fee']
        hidden = 5 + 2 + (target * 0.03) + (target * 0.015)
        total_cost = net_cost + 2 + hidden
        profit = revenue - fees - total_cost
        roi = (profit / total_cost) * 100
        
        print(f"ASIN: {product['asin']}")
        print(f"Purchase: €{purchase:.2f}")
        print(f"Target: €{target:.2f}")
        print(f"ROI: {roi:.1f}%")
        
        # Flag suspicious ROI
        if roi > 50:
            print(f"WARNING: ROI > 50% - Verify manually!")
            suspicious_count += 1
        elif roi > 35:
            print(f"CAUTION: High ROI - Double check numbers")
        elif roi < 5:
            print(f"LOW: ROI < 5% - Likely unprofitable")
        else:
            print(f"NORMAL: ROI in reasonable range")
        
        results.append({
            'name': product['name'],
            'asin': product['asin'],
            'roi': roi,
            'suspicious': roi > 50
        })
    
    print(f"\n--- SUMMARY ---")
    print(f"Total products tested: {len(sample_products)}")
    print(f"Suspicious ROI (>50%): {suspicious_count}")
    print(f"Average ROI: {sum(r['roi'] for r in results) / len(results):.1f}%")
    
    return results, suspicious_count


def run_all_tests():
    """
    Run all test cases and provide summary
    """
    print("STARTING COMPREHENSIVE ROI CALCULATION TESTS")
    print("=" * 80)
    
    # Test 1: Manual calculation
    roi1, pass1 = test_roi_calculation()
    
    # Test 2: System integration
    roi2, pass2 = test_system_integration()
    
    # Test 3: Edge cases
    edge_results = test_edge_cases()
    
    # Test 4: CSV sample
    csv_results, suspicious_count = test_csv_sample()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    print(f"""
    TEST RESULTS:
    Manual Calculation: {'PASS' if pass1 else 'FAIL'} (ROI: {roi1:.1f}%)
    System Integration: {'PASS' if pass2 else 'FAIL'} (ROI: {roi2:.1f}%)
    Edge Cases: {sum(1 for r in edge_results if r['pass'])}/{len(edge_results)} PASSED
    CSV Samples: {len(csv_results) - suspicious_count}/{len(csv_results)} NORMAL
    
    RECOMMENDATIONS:
    - ROI calculations appear {'accurate' if pass1 and pass2 else 'PROBLEMATIC'}
    - {suspicious_count} products need manual verification (ROI >50%)
    - System ready for {'production' if pass1 and pass2 else 'debugging'}
    """)
    
    return {
        'manual_test': (roi1, pass1),
        'integration_test': (roi2, pass2),
        'edge_cases': edge_results,
        'csv_results': csv_results,
        'suspicious_count': suspicious_count,
        'overall_pass': pass1 and pass2
    }


if __name__ == "__main__":
    # Run tests when module is executed directly
    results = run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_pass'] else 1)