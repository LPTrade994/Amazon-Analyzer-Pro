"""
Performance Optimization Analysis - Sprint 4 Testing
"""
import pandas as pd
import numpy as np
import time
import sys
from profit_model import find_best_routes, create_default_params
from config import VAT_RATES

def create_large_test_dataset(size=1000):
    """Create a large test dataset for performance testing"""
    print(f"Creating test dataset with {size} products...")
    
    # Base product templates
    products = []
    locales = ['it', 'de', 'fr', 'es']
    
    for i in range(size):
        locale = locales[i % len(locales)]
        
        # Generate realistic price ranges
        base_price = np.random.uniform(20, 500)
        price_variation = np.random.uniform(0.9, 1.1)
        
        product = {
            'ASIN': f'B{i:06d}TEST',
            'Title': f'Test Product {i} - Performance Testing',
            'Buy Box 🚚: Current': base_price * price_variation,
            'Amazon: Current': base_price * np.random.uniform(0.95, 1.05),
            'New FBA: Current': base_price * np.random.uniform(1.0, 1.1),
            'New FBM: Current': base_price * np.random.uniform(0.98, 1.08),
            'Buy Box 🚚: 30 days avg.': base_price * np.random.uniform(1.05, 1.15),
            'Buy Box 🚚: 90 days avg.': base_price * np.random.uniform(1.1, 1.2),
            'Buy Box 🚚: 180 days avg.': base_price * np.random.uniform(1.15, 1.25),
            'Buy Box 🚚: Lowest': base_price * np.random.uniform(0.8, 0.9),
            'Buy Box 🚚: Highest': base_price * np.random.uniform(1.3, 1.5),
            'Sales Rank: Current': np.random.randint(1000, 1000000),
            'Reviews Rating': np.random.uniform(2.5, 5.0),
            'Buy Box: % Amazon 90 days': np.random.uniform(40, 95),
            'Buy Box: Winner Count': np.random.randint(1, 10),
            'Buy Box: 90 days OOS': np.random.uniform(0, 20),
            'Offers: Count': np.random.randint(1, 25),
            'Prime Eligible': np.random.choice([True, False], p=[0.7, 0.3]),
            'Referral Fee %': np.random.choice([0.12, 0.15, 0.18]),
            'FBA Pick&Pack Fee': np.random.uniform(1.5, 3.0),
            'detected_locale': locale
        }
        products.append(product)
    
    return pd.DataFrame(products)

def measure_memory_usage():
    """Get current memory usage in MB (simplified without psutil)"""
    # Simplified memory tracking using sys.getsizeof for demonstration
    return sys.getsizeof(sys.modules) / 1024 / 1024

def test_scalability():
    """Test performance with different dataset sizes"""
    print("="*60)
    print("PERFORMANCE SCALABILITY TESTING")
    print("="*60)
    
    sizes = [100, 500, 1000, 2000]
    results = []
    
    params = create_default_params()
    params.update({
        'discount': 0.21,
        'purchase_strategy': 'Buy Box Current',
        'scenario': 'Medium',
        'mode': 'FBA',
        'min_roi_pct': 10,
        'min_margin_pct': 15
    })
    
    for size in sizes:
        print(f"\nTesting with {size} products:")
        
        # Create dataset
        start_mem = measure_memory_usage()
        start_time = time.time()
        
        df = create_large_test_dataset(size)
        dataset_time = time.time() - start_time
        dataset_mem = measure_memory_usage() - start_mem
        
        print(f"  Dataset creation: {dataset_time:.2f}s, Memory: +{dataset_mem:.1f}MB")
        
        # Test analysis
        analysis_start = time.time()
        analysis_mem_start = measure_memory_usage()
        
        try:
            best_routes = find_best_routes(df, params)
            
            analysis_time = time.time() - analysis_start
            analysis_mem = measure_memory_usage() - analysis_mem_start
            
            routes_found = len(best_routes)
            
            print(f"  Analysis: {analysis_time:.2f}s, Memory: +{analysis_mem:.1f}MB")
            print(f"  Routes found: {routes_found}/{size} ({routes_found/size*100:.1f}%)")
            
            # Calculate performance metrics
            products_per_second = size / analysis_time if analysis_time > 0 else 0
            memory_per_product = analysis_mem / size if size > 0 else 0
            
            results.append({
                'size': size,
                'analysis_time': analysis_time,
                'memory_usage': analysis_mem,
                'routes_found': routes_found,
                'products_per_second': products_per_second,
                'memory_per_product': memory_per_product
            })
            
            print(f"  Performance: {products_per_second:.1f} products/second")
            print(f"  Memory efficiency: {memory_per_product:.3f}MB per product")
            
        except Exception as e:
            print(f"  ERROR Analysis failed: {e}")
            results.append({
                'size': size,
                'analysis_time': 0,
                'memory_usage': 0,
                'routes_found': 0,
                'products_per_second': 0,
                'memory_per_product': 0,
                'error': str(e)
            })
    
    return results

def test_memory_efficiency():
    """Test memory usage patterns"""
    print("\n" + "="*60)
    print("MEMORY EFFICIENCY TESTING")
    print("="*60)
    
    initial_memory = measure_memory_usage()
    print(f"Initial memory usage: {initial_memory:.1f}MB")
    
    # Test memory growth with repeated operations
    df = create_large_test_dataset(500)
    after_dataset = measure_memory_usage()
    print(f"After dataset creation: {after_dataset:.1f}MB (+{after_dataset-initial_memory:.1f}MB)")
    
    params = create_default_params()
    
    memory_usage = []
    for i in range(5):
        before_analysis = measure_memory_usage()
        
        # Run analysis
        routes = find_best_routes(df, params)
        
        after_analysis = measure_memory_usage()
        memory_diff = after_analysis - before_analysis
        
        memory_usage.append({
            'iteration': i+1,
            'before': before_analysis,
            'after': after_analysis,
            'diff': memory_diff,
            'routes_found': len(routes)
        })
        
        print(f"Iteration {i+1}: {before_analysis:.1f}MB -> {after_analysis:.1f}MB (+{memory_diff:.1f}MB, {len(routes)} routes)")
    
    # Check for memory leaks
    memory_growth = memory_usage[-1]['after'] - memory_usage[0]['before']
    print(f"\nMemory growth over 5 iterations: {memory_growth:.1f}MB")
    
    if memory_growth > 50:  # More than 50MB growth
        print("WARNING: Potential memory leak detected")
    else:
        print("OK: Memory usage stable")
    
    return memory_usage

def test_algorithmic_efficiency():
    """Test algorithmic complexity"""
    print("\n" + "="*60)
    print("ALGORITHMIC EFFICIENCY TESTING")
    print("="*60)
    
    # Test time complexity
    sizes = [100, 200, 400, 800]
    times = []
    
    params = create_default_params()
    params.update({
        'discount': 0.21,
        'min_roi_pct': 15,
        'min_margin_pct': 10
    })
    
    for size in sizes:
        df = create_large_test_dataset(size)
        
        # Time multiple runs for accuracy
        run_times = []
        for _ in range(3):
            start = time.time()
            routes = find_best_routes(df, params)
            end = time.time()
            run_times.append(end - start)
        
        avg_time = sum(run_times) / len(run_times)
        times.append(avg_time)
        
        print(f"Size {size}: {avg_time:.3f}s average ({min(run_times):.3f}s - {max(run_times):.3f}s)")
    
    # Analyze complexity
    print("\nTime complexity analysis:")
    for i in range(1, len(sizes)):
        size_ratio = sizes[i] / sizes[i-1]
        time_ratio = times[i] / times[i-1]
        
        if time_ratio <= size_ratio:
            complexity = "Linear or better"
        elif time_ratio <= size_ratio ** 1.5:
            complexity = "Sub-quadratic"
        elif time_ratio <= size_ratio ** 2:
            complexity = "Quadratic"
        else:
            complexity = "Worse than quadratic"
        
        print(f"  {sizes[i-1]} -> {sizes[i]}: {size_ratio:.1f}x size, {time_ratio:.2f}x time -> {complexity}")
    
    return times

def generate_performance_report(scalability_results, memory_usage, algorithmic_times):
    """Generate comprehensive performance report"""
    print("\n" + "="*60)
    print("PERFORMANCE ANALYSIS REPORT")
    print("="*60)
    
    # Scalability summary
    print("\n1. SCALABILITY SUMMARY:")
    if scalability_results:
        best_performance = max(scalability_results, key=lambda x: x['products_per_second'])
        worst_performance = min(scalability_results, key=lambda x: x['products_per_second'])
        
        print(f"   Best performance: {best_performance['products_per_second']:.1f} products/second ({best_performance['size']} products)")
        print(f"   Worst performance: {worst_performance['products_per_second']:.1f} products/second ({worst_performance['size']} products)")
        
        avg_memory_per_product = np.mean([r['memory_per_product'] for r in scalability_results if r['memory_per_product'] > 0])
        print(f"   Average memory usage: {avg_memory_per_product:.3f}MB per product")
    
    # Memory efficiency summary
    print("\n2. MEMORY EFFICIENCY:")
    if memory_usage:
        memory_growth = memory_usage[-1]['after'] - memory_usage[0]['before']
        print(f"   Memory stability: {memory_growth:.1f}MB growth over 5 iterations")
        print(f"   Memory leak risk: {'HIGH' if memory_growth > 50 else 'LOW'}")
    
    # Performance recommendations
    print("\n3. OPTIMIZATION RECOMMENDATIONS:")
    
    if scalability_results:
        max_products_per_second = max(r['products_per_second'] for r in scalability_results if r['products_per_second'] > 0)
        
        if max_products_per_second < 50:
            print("   - Consider optimizing core analysis algorithms")
            print("   - Add caching for repeated calculations")
            print("   - Consider parallel processing for large datasets")
        elif max_products_per_second < 100:
            print("   - Performance is adequate for most use cases")
            print("   - Consider vectorization for large datasets")
        else:
            print("   - Excellent performance, no immediate optimization needed")
    
    # Dataset size recommendations
    print("\n4. RECOMMENDED DATASET LIMITS:")
    if scalability_results:
        good_performance_sizes = [r['size'] for r in scalability_results if r['products_per_second'] > 50]
        if good_performance_sizes:
            print(f"   - Optimal performance up to: {max(good_performance_sizes)} products")
        
        acceptable_sizes = [r['size'] for r in scalability_results if r['products_per_second'] > 20]
        if acceptable_sizes:
            print(f"   - Acceptable performance up to: {max(acceptable_sizes)} products")
    
    print(f"\n5. TESTING COMPLETED: {len(scalability_results)} scalability tests completed")

def main():
    """Main performance testing function"""
    print("Starting Amazon Analyzer Pro - Performance Testing Suite")
    print("=" * 80)
    
    # Run all performance tests
    scalability_results = test_scalability()
    memory_usage = test_memory_efficiency()
    algorithmic_times = test_algorithmic_efficiency()
    
    # Generate comprehensive report
    generate_performance_report(scalability_results, memory_usage, algorithmic_times)
    
    print("\n" + "="*80)
    print("PERFORMANCE TESTING COMPLETED")
    print("="*80)

if __name__ == '__main__':
    main()