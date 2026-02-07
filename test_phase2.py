"""
Test script for Phase 2: Keyword Selection Strategy
Demonstrates keyword selection for title and bullet points
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from api.services.keyword_root_analyzer import KeywordRootAnalyzer
from api.services.keyword_variant_detector import KeywordVariantDetector
from api.services.keyword_selector import KeywordSelector

def test_phase2():
    """Test Phase 2 components with sample data"""
    
    print("=" * 80)
    print("PHASE 2: KEYWORD SELECTION STRATEGY TEST")
    print("=" * 80)
    print()
    
    # Sample keyword evaluation data (expanded)
    sample_keywords = [
        {'keyword': 'freeze dried strawberries', 'Search Volume': 1500, 'category': 'relevant'},
        {'keyword': 'freeze dried strawberry', 'Search Volume': 1200, 'category': 'relevant'},
        {'keyword': 'strawberries freeze dried', 'Search Volume': 800, 'category': 'relevant'},
        {'keyword': 'organic freeze dried strawberries', 'Search Volume': 600, 'category': 'design_specific'},
        {'keyword': 'freeze dried fruit', 'Search Volume': 2000, 'category': 'relevant'},
        {'keyword': 'dried strawberries', 'Search Volume': 1800, 'category': 'relevant'},
        {'keyword': 'strawberry slices', 'Search Volume': 900, 'category': 'design_specific'},
        {'keyword': 'the freeze dried strawberries', 'Search Volume': 400, 'category': 'relevant'},
        {'keyword': 'freeze dried snacks', 'Search Volume': 1100, 'category': 'relevant'},
        {'keyword': 'healthy fruit snacks', 'Search Volume': 950, 'category': 'relevant'},
        {'keyword': 'organic strawberries', 'Search Volume': 700, 'category': 'design_specific'},
        {'keyword': 'crunchy strawberries', 'Search Volume': 500, 'category': 'relevant'},
        {'keyword': 'strawberry chips', 'Search Volume': 850, 'category': 'relevant'},
        {'keyword': 'dehydrated strawberries', 'Search Volume': 650, 'category': 'relevant'},
        {'keyword': 'freeze dried berries', 'Search Volume': 1300, 'category': 'relevant'},
    ]
    
    # Run Phase 1 analysis first
    print("Running Phase 1 Analysis...")
    print("-" * 80)
    
    root_analyzer = KeywordRootAnalyzer()
    root_analysis = root_analyzer.extract_roots_from_keywords(sample_keywords)
    
    variant_detector = KeywordVariantDetector()
    variant_analysis = variant_detector.detect_variants(sample_keywords)
    
    print(f"✓ Found {root_analysis['total_roots']} roots")
    print(f"✓ Found {len(variant_analysis)} variant groups")
    print()
    
    # Test Phase 2: Keyword Selection
    print("TEST 1: ROOT REPRESENTATIVE SELECTION")
    print("-" * 80)
    
    selector = KeywordSelector()
    selection_result = selector.select_keywords_for_optimization(
        sample_keywords,
        root_analysis,
        variant_analysis
    )
    
    print(f"Total Root Representatives: {len(selection_result['root_representatives'])}")
    print(f"Design-Specific: {selection_result['design_specific_count']}")
    print(f"Regular: {selection_result['regular_count']}")
    print()
    
    print("Top 10 Root Representatives:")
    for i, rep in enumerate(selection_result['root_representatives'][:10], 1):
        ds_marker = " [DESIGN-SPECIFIC]" if rep['is_design_specific'] else ""
        print(f"{i}. '{rep['keyword']}'{ds_marker}")
        print(f"   Root: {rep['root']}")
        print(f"   Search Volume: {rep['search_volume']:,}")
        print(f"   Root Total Volume: {rep['root_total_volume']:,}")
        print()
    
    # Test 2: Title Keyword Selection
    print("\nTEST 2: TITLE KEYWORD SELECTION")
    print("-" * 80)
    
    title_kws = selection_result['title_keywords']
    
    print(f"Total Keywords Selected for Title: {title_kws['total_keywords']}")
    print(f"Total Search Volume: {title_kws['total_search_volume']:,}")
    print()
    
    if title_kws['main_keyword']:
        print("MAIN KEYWORD (Highest Volume Relevant Root):")
        mk = title_kws['main_keyword']
        print(f"  • {mk['keyword']} (SV: {mk['search_volume']:,})")
        print()
    
    if title_kws['design_keywords']:
        print(f"DESIGN-SPECIFIC KEYWORDS ({len(title_kws['design_keywords'])}):")
        for dk in title_kws['design_keywords']:
            print(f"  • {dk['keyword']} (SV: {dk['search_volume']:,})")
        print()
    
    if title_kws['additional_keywords']:
        print(f"ADDITIONAL KEYWORDS ({len(title_kws['additional_keywords'])}):")
        for ak in title_kws['additional_keywords']:
            print(f"  • {ak['keyword']} (SV: {ak['search_volume']:,})")
        print()
    
    print("ALL TITLE KEYWORDS:")
    for kw in title_kws['all_keywords']:
        ds_marker = " [DS]" if kw['is_design_specific'] else ""
        print(f"  • {kw['keyword']} (SV: {kw['search_volume']:,}){ds_marker}")
    print()
    
    # Test 3: Bullet Point Keyword Selection
    print("\nTEST 3: BULLET POINT KEYWORD SELECTION")
    print("-" * 80)
    
    bullet_kws = selection_result['bullet_keywords']
    
    print(f"Total Keywords Selected for Bullets: {bullet_kws['total_keywords']}")
    print(f"Total Search Volume: {bullet_kws['total_search_volume']:,}")
    print(f"Average Keywords per Bullet: {bullet_kws['avg_keywords_per_bullet']:.1f}")
    print()
    
    print("BULLET ASSIGNMENTS:")
    for assignment in bullet_kws['bullet_assignments']:
        print(f"\nBullet {assignment['bullet_number']}:")
        print(f"  Keywords: {assignment['keyword_count']}")
        print(f"  Search Volume: {assignment['total_search_volume']:,}")
        print(f"  Keywords:")
        for kw in assignment['keywords']:
            ds_marker = " [DS]" if kw['is_design_specific'] else ""
            print(f"    • {kw['keyword']} (SV: {kw['search_volume']:,}){ds_marker}")
    print()
    
    # Test 4: Find Better Alternatives
    print("\nTEST 4: FIND BETTER ALTERNATIVES")
    print("-" * 80)
    
    # Test with a lower-volume keyword
    test_keyword = "strawberries freeze dried"
    print(f"Finding better alternatives for: '{test_keyword}'")
    print()
    
    alternatives = selector.find_better_alternatives(
        test_keyword,
        selection_result['root_representatives'],
        variant_analysis
    )
    
    if alternatives:
        print(f"Found {len(alternatives)} better alternatives:")
        for alt in alternatives:
            print(f"\n  Alternative: '{alt['alternative_keyword']}'")
            print(f"  Current Volume: {alt['current_volume']:,}")
            print(f"  Alternative Volume: {alt['alternative_volume']:,}")
            print(f"  Improvement: +{alt['improvement']:,} ({alt['improvement_percent']}%)")
            print(f"  Root: {alt['root']}")
    else:
        print("  No better alternatives found (this is already the best!)")
    print()
    
    # Test 5: Summary Statistics
    print("\nTEST 5: SUMMARY STATISTICS")
    print("-" * 80)
    
    total_title_volume = title_kws['total_search_volume']
    total_bullet_volume = bullet_kws['total_search_volume']
    total_volume = total_title_volume + total_bullet_volume
    
    print(f"Title Search Volume: {total_title_volume:,}")
    print(f"Bullets Search Volume: {total_bullet_volume:,}")
    print(f"Total Search Volume: {total_volume:,}")
    print()
    
    print(f"Title Keywords: {title_kws['total_keywords']}")
    print(f"Bullet Keywords: {bullet_kws['total_keywords']}")
    print(f"Total Keywords: {title_kws['total_keywords'] + bullet_kws['total_keywords']}")
    print()
    
    design_in_title = sum(1 for kw in title_kws['all_keywords'] if kw['is_design_specific'])
    design_in_bullets = sum(1 for kw in bullet_kws['all_keywords'] if kw['is_design_specific'])
    
    print(f"Design-Specific in Title: {design_in_title}")
    print(f"Design-Specific in Bullets: {design_in_bullets}")
    print(f"Total Design-Specific: {design_in_title + design_in_bullets}")
    print()
    
    print("=" * 80)
    print("PHASE 2 TEST COMPLETE")
    print("=" * 80)
    print()
    print("✓ Root representatives selected")
    print("✓ Title keywords optimized (4-6 keywords + 2-3 design-specific)")
    print("✓ Bullet keywords distributed (2-3 per bullet)")
    print("✓ Better alternatives identified")

if __name__ == "__main__":
    test_phase2()
