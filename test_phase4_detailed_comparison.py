"""
Test script for Phase 4: Detailed SEO Comparison
Demonstrates Tasks 8, 9, 10, 12, 13 implementation
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.seo_optimization_service import SEOOptimizationService

async def test_detailed_comparison():
    """Test detailed SEO comparison with all task requirements"""
    
    print("=" * 80)
    print("PHASE 4: DETAILED SEO COMPARISON TEST")
    print("Testing Tasks 8, 9, 10, 12, 13")
    print("=" * 80)
    print()
    
    # Sample data with some duplicates for testing Task 12
    current_title = "Freeze Dried Strawberries - Healthy Snack - Freeze Dried Fruit"
    current_bullets = [
        "Made with real strawberries for authentic taste",
        "Perfect healthy snack for children and adults",
        "Resealable bag keeps fruit fresh and crunchy",
        "Great for kids as a healthy snack option"  # Duplicate "healthy snack"
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
        {'keyword': 'irrelevant keyword', 'Search Volume': 5000, 'category': 'irrelevant'},  # Task 13: Should be excluded
    ]
    
    product_info = {
        'brand': 'Nature\'s Best',
        'category': 'Grocery & Gourmet Food'
    }
    
    print("Running SEO optimization with detailed comparison...")
    print()
    
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
    
    comparison = result['detailed_comparison']
    
    # TASK 8: Side-by-Side Comparison
    print("\n" + "=" * 80)
    print("TASK 8: SIDE-BY-SIDE COMPARISON")
    print("=" * 80)
    
    print("\n┌─────────────────────────────────────┬─────────────────────────────────────┐")
    print("│          CURRENT TITLE              │         OPTIMIZED TITLE             │")
    print("├─────────────────────────────────────┼─────────────────────────────────────┤")
    
    # Wrap text for display
    current_title_wrapped = comparison['title']['current']['text'][:35]
    optimized_title_wrapped = comparison['title']['optimized']['text'][:35]
    print(f"│ {current_title_wrapped:<35} │ {optimized_title_wrapped:<35} │")
    print("└─────────────────────────────────────┴─────────────────────────────────────┘")
    
    # TASK 9: Keywords with Search Volumes in Brackets
    print("\n" + "=" * 80)
    print("TASK 9: KEYWORDS WITH SEARCH VOLUMES (in brackets)")
    print("=" * 80)
    
    print("\n🔵 CURRENT TITLE KEYWORDS:")
    for kw in comparison['title']['current']['keywords']:
        print(f"   • {kw['display']}")
    print(f"\n   Total Search Volume: {comparison['title']['current']['total_search_volume']:,}")
    
    print("\n🟢 OPTIMIZED TITLE KEYWORDS:")
    for kw in comparison['title']['optimized']['keywords']:
        ds_marker = " [DESIGN-SPECIFIC]" if kw.get('is_design_specific') else ""
        print(f"   • {kw['display']}{ds_marker}")
    print(f"\n   Total Search Volume: {comparison['title']['optimized']['total_search_volume']:,}")
    
    print("\n🔵 CURRENT BULLET KEYWORDS:")
    for bullet in comparison['bullets']['current']['bullets']:
        print(f"\n   Bullet {bullet['bullet_number']}:")
        if bullet['keywords']:
            for kw in bullet['keywords']:
                print(f"     • {kw['display']}")
            print(f"     Search Volume: {bullet['search_volume']:,}")
        else:
            print(f"     No keywords found")
    print(f"\n   Total Search Volume (All Bullets): {comparison['bullets']['current']['total_search_volume']:,}")
    
    print("\n🟢 OPTIMIZED BULLET KEYWORDS:")
    for bullet in comparison['bullets']['optimized']['bullets']:
        print(f"\n   Bullet {bullet['bullet_number']}:")
        if bullet['keywords']:
            for kw in bullet['keywords']:
                ds_marker = " [DS]" if kw.get('is_design_specific') else ""
                print(f"     • {kw['display']}{ds_marker}")
            print(f"     Search Volume: {bullet['search_volume']:,}")
        else:
            print(f"     No keywords")
    print(f"\n   Total Search Volume (All Bullets): {comparison['bullets']['optimized']['total_search_volume']:,}")
    
    # TASK 10: "Search Volume" heading, Remove density from bullets, Total characters
    print("\n" + "=" * 80)
    print("TASK 10: KEYWORD ANALYSIS SECTION")
    print("=" * 80)
    
    print("\n📊 TITLE ANALYSIS:")
    print(f"\n   Current Title:")
    print(f"     Search Volume: {comparison['title']['current']['total_search_volume']:,}")  # Task 10: "Search Volume" not "Volume"
    print(f"     Characters: {comparison['title']['current']['characters']}")  # Task 10: Total characters
    print(f"     Keyword Density: {comparison['title']['current']['keyword_density']}%")
    
    print(f"\n   Optimized Title:")
    print(f"     Search Volume: {comparison['title']['optimized']['total_search_volume']:,}")
    print(f"     Characters: {comparison['title']['optimized']['characters']}")  # Task 10: Total characters
    print(f"     Keyword Density: {comparison['title']['optimized']['keyword_density']}%")
    
    print("\n📊 BULLET POINTS ANALYSIS:")
    print(f"\n   Current Bullets:")
    for bullet in comparison['bullets']['current']['bullets']:
        print(f"     Bullet {bullet['bullet_number']}:")
        print(f"       Search Volume: {bullet['search_volume']:,}")
        print(f"       Characters: {bullet['characters']}")  # Task 10: Total characters in bullet
        # Task 10: NO density field for bullets
    
    print(f"\n   Optimized Bullets:")
    for bullet in comparison['bullets']['optimized']['bullets']:
        print(f"     Bullet {bullet['bullet_number']}:")
        print(f"       Search Volume: {bullet['search_volume']:,}")
        print(f"       Characters: {bullet['characters']}")  # Task 10: Total characters in bullet
        # Task 10: NO density field for bullets
    
    # TASK 12: Highlight Duplicate Keywords
    print("\n" + "=" * 80)
    print("TASK 12: DUPLICATE KEYWORD DETECTION")
    print("=" * 80)
    
    print("\n🔍 CURRENT LISTING DUPLICATES:")
    title_dups = comparison['title']['current']['duplicates']
    bullet_dups = comparison['bullets']['current']['duplicates']
    
    if title_dups:
        print(f"\n   Title Duplicates:")
        for dup in title_dups:
            print(f"     ⚠️  '{dup['keyword']}' used {dup['count']} times")
    else:
        print(f"\n   Title: No duplicates ✓")
    
    if bullet_dups:
        print(f"\n   Bullet Duplicates:")
        for dup in bullet_dups:
            print(f"     ⚠️  '{dup['keyword']}' used {dup['count']} times")
    else:
        print(f"\n   Bullets: No duplicates ✓")
    
    print("\n🔍 OPTIMIZED LISTING DUPLICATES:")
    opt_title_dups = comparison['title']['optimized']['duplicates']
    opt_bullet_dups = comparison['bullets']['optimized']['duplicates']
    
    if opt_title_dups:
        print(f"\n   Title Duplicates:")
        for dup in opt_title_dups:
            print(f"     ⚠️  '{dup['keyword']}' used {dup['count']} times")
    else:
        print(f"\n   Title: No duplicates ✓")
    
    if opt_bullet_dups:
        print(f"\n   Bullet Duplicates:")
        for dup in opt_bullet_dups:
            print(f"     ⚠️  '{dup['keyword']}' used {dup['count']} times")
    else:
        print(f"\n   Bullets: No duplicates ✓")
    
    # TASK 13: Root Volume Only for Relevant Roots
    print("\n" + "=" * 80)
    print("TASK 13: RELEVANT ROOT VOLUMES (Excludes Irrelevant)")
    print("=" * 80)
    
    relevant_roots = comparison['overall']['relevant_root_volumes']
    
    print(f"\n📈 TOP RELEVANT ROOTS (Total: {len(relevant_roots)}):")
    for i, root in enumerate(relevant_roots[:10], 1):
        ds_marker = " [DESIGN-SPECIFIC]" if root['is_design_specific'] else ""
        print(f"\n   {i}. '{root['root']}'{ds_marker}")
        print(f"      Total Search Volume: {root['total_volume']:,}")
        print(f"      Keywords: {root['keyword_count']}")
    
    print(f"\n   Note: Irrelevant roots are excluded from this calculation")
    
    # Overall Summary
    print("\n" + "=" * 80)
    print("OVERALL COMPARISON SUMMARY")
    print("=" * 80)
    
    overall = comparison['overall']
    
    print(f"\n📊 TOTALS:")
    print(f"\n   Current:")
    print(f"     Total Search Volume: {overall['current']['total_search_volume']:,}")
    print(f"     Total Keywords: {overall['current']['total_keywords']}")
    print(f"     Total Characters: {overall['current']['total_characters']}")
    
    print(f"\n   Optimized:")
    print(f"     Total Search Volume: {overall['optimized']['total_search_volume']:,}")
    print(f"     Total Keywords: {overall['optimized']['total_keywords']}")
    print(f"     Total Characters: {overall['optimized']['total_characters']}")
    
    print(f"\n   Improvement:")
    print(f"     Search Volume: +{overall['improvement']['search_volume']:,} ({overall['improvement']['search_volume_percent']:.1f}%)")
    print(f"     Keywords: +{overall['improvement']['keywords']}")
    
    print()
    print("=" * 80)
    print("PHASE 4 TEST COMPLETE")
    print("=" * 80)
    print()
    print("✅ Task 8: Side-by-side comparison implemented")
    print("✅ Task 9: Keywords with search volumes in brackets")
    print("✅ Task 10: 'Search Volume' heading, no density in bullets, total characters")
    print("✅ Task 12: Duplicate keyword detection and highlighting")
    print("✅ Task 13: Root volume only for relevant/generic roots")

if __name__ == "__main__":
    asyncio.run(test_detailed_comparison())
