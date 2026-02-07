"""
Test script for Phase 3: Complete SEO Optimization
Demonstrates end-to-end SEO optimization with content generation and validation
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.seo_optimization_service import SEOOptimizationService

async def test_seo_optimization():
    """Test complete SEO optimization workflow"""
    
    print("=" * 80)
    print("PHASE 3: COMPLETE SEO OPTIMIZATION TEST")
    print("=" * 80)
    print()
    
    # Sample data
    current_title = "Freeze Dried Strawberries - Healthy Snack for Kids"
    current_bullets = [
        "Made with real strawberries for authentic taste",
        "Perfect healthy snack for children and adults",
        "Resealable bag keeps fruit fresh and crunchy"
    ]
    
    sample_keywords = [
        {'keyword': 'freeze dried strawberries', 'Search Volume': 1500, 'category': 'relevant'},
        {'keyword': 'freeze dried fruit', 'Search Volume': 2000, 'category': 'relevant'},
        {'keyword': 'organic freeze dried strawberries', 'Search Volume': 600, 'category': 'design_specific'},
        {'keyword': 'strawberry slices', 'Search Volume': 900, 'category': 'design_specific'},
        {'keyword': 'dried strawberries', 'Search Volume': 1800, 'category': 'relevant'},
        {'keyword': 'freeze dried snacks', 'Search Volume': 1100, 'category': 'relevant'},
        {'keyword': 'healthy fruit snacks', 'Search Volume': 950, 'category': 'relevant'},
        {'keyword': 'crunchy strawberries', 'Search Volume': 500, 'category': 'relevant'},
        {'keyword': 'strawberry chips', 'Search Volume': 850, 'category': 'relevant'},
        {'keyword': 'dehydrated strawberries', 'Search Volume': 650, 'category': 'relevant'},
        {'keyword': 'freeze dried berries', 'Search Volume': 1300, 'category': 'relevant'},
    ]
    
    product_info = {
        'brand': 'Nature\'s Best',
        'category': 'Grocery & Gourmet Food'
    }
    
    print("CURRENT LISTING:")
    print("-" * 80)
    print(f"Title: {current_title}")
    print(f"Character Count: {len(current_title)}")
    print("\nBullet Points:")
    for i, bullet in enumerate(current_bullets, 1):
        print(f"{i}. {bullet}")
    print()
    
    # Run optimization
    print("\nRUNNING SEO OPTIMIZATION...")
    print("-" * 80)
    
    service = SEOOptimizationService()
    result = await service.optimize_listing(
        current_title,
        current_bullets,
        sample_keywords,
        product_info
    )
    
    if not result['success']:
        print("❌ Optimization failed!")
        return
    
    print("✓ Optimization complete!\n")
    
    # Display results
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS")
    print("=" * 80)
    
    # Current vs Optimized - Side by Side
    print("\n📊 SIDE-BY-SIDE COMPARISON")
    print("-" * 80)
    
    print("\n🔵 CURRENT TITLE:")
    print(f"   {result['current']['title']}")
    print(f"   Characters: {result['current']['analysis']['title']['character_count']}")
    print(f"   Keywords: {result['current']['analysis']['title']['keyword_count']}")
    print(f"   Search Volume: {result['current']['analysis']['title']['total_search_volume']:,}")
    
    print("\n🟢 OPTIMIZED TITLE:")
    print(f"   {result['optimized']['title']}")
    print(f"   Characters: {result['optimized']['title_details']['character_count']}")
    print(f"   Keywords: {len(result['optimized']['title_details']['keywords_used'])}")
    print(f"   Search Volume: {result['keyword_selection']['title_keywords']['total_search_volume']:,}")
    
    print("\n   Keywords Used:")
    for kw in result['optimized']['title_details']['keywords_used']:
        print(f"     • {kw}")
    
    print("\n🔵 CURRENT BULLET POINTS:")
    for i, bullet in enumerate(result['current']['bullets'], 1):
        print(f"   {i}. {bullet}")
        print(f"      Characters: {len(bullet)}")
    print(f"   Total Search Volume: {result['current']['analysis']['bullets']['total_search_volume']:,}")
    
    print("\n🟢 OPTIMIZED BULLET POINTS:")
    for i, bullet in enumerate(result['optimized']['bullets'], 1):
        print(f"   {i}. {bullet}")
        print(f"      Characters: {len(bullet)}")
        if i <= len(result['optimized']['bullets_details']['keywords_per_bullet']):
            keywords = result['optimized']['bullets_details']['keywords_per_bullet'][i-1]
            if keywords:
                print(f"      Keywords: {', '.join(keywords)}")
    print(f"   Total Search Volume: {result['keyword_selection']['bullet_keywords']['total_search_volume']:,}")
    
    # Improvements
    print("\n\n📈 IMPROVEMENTS")
    print("-" * 80)
    improvements = result['improvements']
    
    print(f"\nSearch Volume:")
    print(f"  Current:   {improvements['search_volume']['current']:,}")
    print(f"  Optimized: {improvements['search_volume']['optimized']:,}")
    print(f"  Change:    +{improvements['search_volume']['improvement']:,} ({improvements['search_volume']['improvement_percent']}%)")
    
    print(f"\nKeyword Count:")
    print(f"  Current:   {improvements['keyword_count']['current']}")
    print(f"  Optimized: {improvements['keyword_count']['optimized']}")
    print(f"  Change:    +{improvements['keyword_count']['improvement']}")
    
    print(f"\nRoot Coverage:")
    print(f"  Current:   {improvements['root_coverage']['current']} roots")
    print(f"  Optimized: {improvements['root_coverage']['optimized']} roots")
    print(f"  Change:    +{improvements['root_coverage']['improvement']} roots")
    
    if improvements['summary']:
        print(f"\nSummary:")
        for improvement in improvements['summary']:
            print(f"  ✓ {improvement}")
    
    # Validation
    print("\n\n✅ AMAZON GUIDELINES VALIDATION")
    print("-" * 80)
    
    current_val = result['current']['validation']
    optimized_val = result['optimized']['validation']
    
    print(f"\nCurrent Listing:")
    print(f"  Compliant: {'✓ Yes' if current_val['is_compliant'] else '✗ No'}")
    print(f"  Issues: {current_val['total_issues']}")
    print(f"  Warnings: {current_val['total_warnings']}")
    
    if current_val['title']['issues']:
        print(f"\n  Title Issues:")
        for issue in current_val['title']['issues']:
            print(f"    • {issue}")
    
    if current_val['bullets']['issues']:
        print(f"\n  Bullet Issues:")
        for issue in current_val['bullets']['issues'][:5]:  # Show first 5
            print(f"    • {issue}")
    
    print(f"\nOptimized Listing:")
    print(f"  Compliant: {'✓ Yes' if optimized_val['is_compliant'] else '✗ No'}")
    print(f"  Issues: {optimized_val['total_issues']}")
    print(f"  Warnings: {optimized_val['total_warnings']}")
    
    if optimized_val['title']['issues']:
        print(f"\n  Title Issues:")
        for issue in optimized_val['title']['issues']:
            print(f"    • {issue}")
    
    if optimized_val['bullets']['issues']:
        print(f"\n  Bullet Issues:")
        for issue in optimized_val['bullets']['issues'][:5]:
            print(f"    • {issue}")
    
    # Design-Specific Detection
    print("\n\n🎯 DESIGN-SPECIFIC KEYWORD HANDLING")
    print("-" * 80)
    
    design_detection = result['keyword_selection'].get('design_detection')
    if design_detection:
        print(f"\nDesign-Specific Keywords Present: {design_detection['has_design_specific']}")
        if design_detection['found_in_title']:
            print(f"Found in Title: {', '.join(design_detection['found_in_title'])}")
        if design_detection['found_in_bullets']:
            print(f"Found in Bullets: {', '.join(design_detection['found_in_bullets'])}")
        print(f"\nReasoning: {design_detection['reasoning']}")
    
    print(f"\nInclude Design-Specific in Optimization: {result['keyword_selection']['include_design_specific']}")
    
    # Top Roots
    print("\n\n🔑 TOP KEYWORD ROOTS")
    print("-" * 80)
    
    for i, root in enumerate(result['root_analysis']['top_roots'][:5], 1):
        ds_marker = " [DESIGN-SPECIFIC]" if root['is_design_specific'] else ""
        print(f"{i}. '{root['root']}'{ds_marker}")
        print(f"   Total Search Volume: {root['total_search_volume']:,}")
        print(f"   Keywords: {root['keyword_count']}")
    
    print()
    print("=" * 80)
    print("PHASE 3 TEST COMPLETE")
    print("=" * 80)
    print()
    print("✓ Content analyzed")
    print("✓ Keywords selected")
    print("✓ Title optimized")
    print("✓ Bullet points optimized")
    print("✓ Amazon guidelines validated")
    print("✓ Improvements calculated")

if __name__ == "__main__":
    asyncio.run(test_seo_optimization())
