
def minimal_validation():
    # Test solo i requisiti critici che devono funzionare
    
    # 1. Pricing Italia/Germania CRITICI
    from pricing import compute_net_purchase
    from config import VAT_RATES
    
    result_it = compute_net_purchase(200.0, 'it', 0.21, VAT_RATES)
    result_de = compute_net_purchase(200.0, 'de', 0.21, VAT_RATES)
    
    # Questi DEVONO passare
    assert abs(result_it - 121.93) < 0.01, f"Italia failed: {result_it}"
    assert abs(result_de - 132.77) < 0.01, f"Germania failed: {result_de}"
    
    # 2. Moduli importabili
    import streamlit
    import pandas as pd
    from ui_polish import show_user_friendly_error
    
    # 3. Test suite generale
    import subprocess
    result = subprocess.run(['python', 'test_suite.py'], capture_output=True)
    assert result.returncode == 0, "Test suite failed"
    
    print("MINIMAL VALIDATION: ALL CRITICAL TESTS PASSED")
    return True
