import unittest
import pandas as pd
from pricing import compute_net_purchase, select_purchase_price, select_target_price, calculate_profit_metrics


class TestPricing(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.vat_rates = {
            'IT': 0.22,
            'DE': 0.19,
            'FR': 0.20,
            'ES': 0.21
        }
    
    def test_italia_vat_calculation(self):
        """
        Test Italia: prezzo 200€, sconto 21%
        - Sconto: 200 * 0.21 = 42€
        - No IVA: 200 / 1.22 = 163.93€  
        - Costo finale: 163.93 - 42 = 121.93€
        """
        price_gross = 200.0
        source_locale = 'it'
        discount_pct = 0.21
        
        result = compute_net_purchase(price_gross, source_locale, discount_pct, self.vat_rates)
        expected = 121.93
        
        print(f"Test Italia - Expected: {expected:.2f}€, Got: {result:.2f}€")
        self.assertTrue(abs(result - expected) < 0.01, 
                       f"Italia test failed: expected {expected:.2f}, got {result:.2f}")
    
    def test_germania_vat_calculation(self):
        """
        Test Germania: prezzo 200€, sconto 21%, IVA 19%
        - No IVA: 200 / 1.19 = 168.07€
        - Costo finale: 168.07 * (1-0.21) = 132.77€
        """
        price_gross = 200.0
        source_locale = 'de'
        discount_pct = 0.21
        
        result = compute_net_purchase(price_gross, source_locale, discount_pct, self.vat_rates)
        expected = 132.77
        
        print(f"Test Germania - Expected: {expected:.2f}€, Got: {result:.2f}€")
        self.assertTrue(abs(result - expected) < 0.01,
                       f"Germania test failed: expected {expected:.2f}, got {result:.2f}")
    
    def test_francia_vat_calculation(self):
        """
        Test Francia: prezzo 150€, sconto 15%, IVA 20%
        - No IVA: 150 / 1.20 = 125.00€
        - Costo finale: 125.00 * (1-0.15) = 106.25€
        """
        price_gross = 150.0
        source_locale = 'fr'
        discount_pct = 0.15
        
        result = compute_net_purchase(price_gross, source_locale, discount_pct, self.vat_rates)
        expected = 106.25
        
        print(f"Test Francia - Expected: {expected:.2f}€, Got: {result:.2f}€")
        self.assertTrue(abs(result - expected) < 0.01,
                       f"Francia test failed: expected {expected:.2f}, got {result:.2f}")
    
    def test_spagna_vat_calculation(self):
        """
        Test Spagna: prezzo 100€, sconto 25%, IVA 21%
        - No IVA: 100 / 1.21 = 82.64€
        - Costo finale: 82.64 * (1-0.25) = 61.98€
        """
        price_gross = 100.0
        source_locale = 'es'
        discount_pct = 0.25
        
        result = compute_net_purchase(price_gross, source_locale, discount_pct, self.vat_rates)
        expected = 61.98
        
        print(f"Test Spagna - Expected: {expected:.2f}€, Got: {result:.2f}€")
        self.assertTrue(abs(result - expected) < 0.01,
                       f"Spagna test failed: expected {expected:.2f}, got {result:.2f}")
    
    def test_edge_cases(self):
        """Test edge cases"""
        # Zero price
        result = compute_net_purchase(0.0, 'it', 0.21, self.vat_rates)
        self.assertEqual(result, 0.0)
        
        # Negative price
        result = compute_net_purchase(-10.0, 'it', 0.21, self.vat_rates)
        self.assertEqual(result, 0.0)
        
        # Zero discount
        result = compute_net_purchase(100.0, 'it', 0.0, self.vat_rates)
        expected = 100.0 / 1.22  # Only VAT removal for Italy
        self.assertTrue(abs(result - expected) < 0.01)
    
    def create_sample_data(self):
        """Create sample data for testing select functions"""
        return pd.DataFrame({
            'ASIN': ['B001', 'B002', 'B003'],
            'Title': ['Product 1', 'Product 2', 'Product 3'],
            'Buy Box 🚚: Current': [50.0, 0.0, 75.0],
            'Amazon: Current': [55.0, 40.0, 0.0],
            'New FBA: Current': [60.0, 45.0, 80.0],
            'New FBM: Current': [58.0, 42.0, 78.0],
            'Referral Fee %': [0.15, 0.12, 0.18],
            'FBA Pick&Pack Fee': [2.0, 1.5, 2.5],
            'detected_locale': ['it', 'de', 'fr']
        })
    
    def test_select_purchase_price(self):
        """Test select_purchase_price function"""
        df = self.create_sample_data()
        
        # Test Buy Box Current strategy
        result = select_purchase_price(df.iloc[0], "Buy Box Current")
        self.assertEqual(result, 50.0)
        
        # Test fallback when Buy Box is 0
        result = select_purchase_price(df.iloc[1], "Buy Box Current")
        self.assertEqual(result, 0.0)
        
        # Test Amazon Current strategy
        result = select_purchase_price(df.iloc[1], "Amazon Current")
        self.assertEqual(result, 40.0)
        
        # Test New FBA Current strategy
        result = select_purchase_price(df.iloc[2], "New FBA Current")
        self.assertEqual(result, 80.0)
        
        print("select_purchase_price tests passed")
    
    def test_select_target_price(self):
        """Test select_target_price function"""
        df = self.create_sample_data()
        
        # Test current scenario (no adjustment)
        result = select_target_price(df.iloc[0], 'it', 'current')
        self.assertEqual(result, 50.0)  # Buy Box price
        
        # Test conservative scenario (5% discount)
        result = select_target_price(df.iloc[0], 'it', 'conservative')
        expected = 50.0 * 0.95
        self.assertEqual(result, expected)
        
        # Test aggressive scenario (5% premium)
        result = select_target_price(df.iloc[0], 'it', 'aggressive')
        expected = 50.0 * 1.05
        self.assertEqual(result, expected)
        
        print("select_target_price tests passed")
    
    def test_comprehensive_calculation(self):
        """Test comprehensive profit calculation"""
        df = self.create_sample_data()
        row = df.iloc[0]  # Italian product
        
        metrics = calculate_profit_metrics(
            row=row,
            purchase_strategy="Buy Box Current",
            target_locale='it',
            scenario='current',
            discount_pct=0.21,
            vat_rates=self.vat_rates
        )
        
        # Verify key metrics are calculated
        self.assertIn('purchase_price_gross', metrics)
        self.assertIn('net_purchase_cost', metrics)
        self.assertIn('target_selling_price', metrics)
        self.assertIn('gross_profit', metrics)
        self.assertIn('profit_margin', metrics)
        self.assertIn('roi', metrics)
        
        # Verify specific values
        self.assertEqual(metrics['purchase_price_gross'], 50.0)
        self.assertEqual(metrics['target_selling_price'], 50.0)
        
        print("Comprehensive calculation test passed")
        print(f"Metrics: {metrics}")


def run_detailed_calculations():
    """Run detailed step-by-step calculations to verify logic"""
    print("\n" + "="*60)
    print("DETAILED VAT CALCULATION VERIFICATION")
    print("="*60)
    
    vat_rates = {'IT': 0.22, 'DE': 0.19, 'FR': 0.20, 'ES': 0.21}
    
    # Test Italia
    print("\n1. ITALIA TEST:")
    print("   Prezzo lordo: 200.00€")
    print("   Sconto: 21%")
    discount_amount = 200.0 * 0.21
    price_no_vat = 200.0 / 1.22
    net_cost = price_no_vat - discount_amount
    print(f"   Step 1 - Sconto amount: 200.00 * 0.21 = {discount_amount:.2f}€")
    print(f"   Step 2 - Prezzo no IVA: 200.00 / 1.22 = {price_no_vat:.2f}€")
    print(f"   Step 3 - Costo finale: {price_no_vat:.2f} - {discount_amount:.2f} = {net_cost:.2f}€")
    
    # Test Germania  
    print("\n2. GERMANIA TEST:")
    print("   Prezzo lordo: 200.00€")
    print("   Sconto: 21%, IVA: 19%")
    price_no_vat_de = 200.0 / 1.19
    net_cost_de = price_no_vat_de * (1 - 0.21)
    print(f"   Step 1 - Prezzo no IVA: 200.00 / 1.19 = {price_no_vat_de:.2f}€")
    print(f"   Step 2 - Costo finale: {price_no_vat_de:.2f} * (1-0.21) = {net_cost_de:.2f}€")
    
    # Test Francia
    print("\n3. FRANCIA TEST:")
    print("   Prezzo lordo: 150.00€")
    print("   Sconto: 15%, IVA: 20%")
    price_no_vat_fr = 150.0 / 1.20
    net_cost_fr = price_no_vat_fr * (1 - 0.15)
    print(f"   Step 1 - Prezzo no IVA: 150.00 / 1.20 = {price_no_vat_fr:.2f}€")
    print(f"   Step 2 - Costo finale: {price_no_vat_fr:.2f} * (1-0.15) = {net_cost_fr:.2f}€")
    
    # Test Spagna
    print("\n4. SPAGNA TEST:")
    print("   Prezzo lordo: 100.00€")
    print("   Sconto: 25%, IVA: 21%")
    price_no_vat_es = 100.0 / 1.21
    net_cost_es = price_no_vat_es * (1 - 0.25)
    print(f"   Step 1 - Prezzo no IVA: 100.00 / 1.21 = {price_no_vat_es:.2f}€")
    print(f"   Step 2 - Costo finale: {price_no_vat_es:.2f} * (1-0.25) = {net_cost_es:.2f}€")


if __name__ == '__main__':
    # Run detailed calculations first
    run_detailed_calculations()
    
    print("\n" + "="*60)
    print("RUNNING UNIT TESTS")
    print("="*60)
    
    # Run unit tests
    unittest.main(verbosity=2)