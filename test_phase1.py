"""
Test script for Phase 1: Data Preparation & Analysis
Demonstrates keyword root analysis, variant detection, and content analysis
"""
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from api.services.keyword_root_analyzer import KeywordRootAnalyzer
from api.services.keyword_variant_detector import KeywordVariantDetector
from api.services.current_content_analyzer import CurrentContentAnalyzer

def test_phase1():
    """Test Phase 1 components with sample data"""
    
    print("=" * 80)
    print("PHASE 1: DATA PREPARATION & ANALYSIS TEST")
    print("=" * 80)
    print()
    
    # Sample keyword evaluation data
    sample_keywords = [
        {
            'keyword': 'freeze dried strawberries',
            'Search Volume': 1500,
            'category': 'relevant'
        },
        {
            'keyword': 'freeze dried strawberry',
            'Search Volume': 1200,
            'category': 'relevant'
        },
        {
            'keyword': 'strawberries freeze dried',
            'Search Volume': 800,
            'category': 'relevant'
        },
        {
            'keyword': 'organic freeze dried strawberries',
            'Search Volume': 600,
            'category': 'design_specific'
        },
        {
            'keyword': 'freeze dried fruit',
            'Search Volume': 2000,
            'category': 'relevant'
        },
        {
            'keyword': 'dried strawberries',
            'Search Volume': 1800,
            'category': 'relevant'
        },
        {
            'keyword': 'strawberry slices',
            'Search Volume': 900,
            'category': 'design_specific'
        },
        {
            'keyword': 'the freeze dried strawberries',
            'Search Volume': 400,
            'category': 'relevant'
        },
        {
            'keyword': 'a freeze dried strawberry',
            'Search Volume': 300,
            'category': 'relevant'
        }
    ]
    
    # Sample current content
    current_title = "Freeze Dried Strawberries - Organic Fruit Snack for Kids"
    current_bullets = [
        "Made with real strawberries for authentic taste",
        "Perfect healthy snack for children and adults",
        "Resealable bag keeps fruit fresh and crunchy"
    ]
    
    # Test 1: Keyword Root Analysis
    print("TEST 1: KEYWORD ROOT ANALYSIS")
    print("-" * 80)
    
    root_analyzer = KeywordRootAnalyzer()
    root_analysis = root_analyzer.extract_roots_from_keywords(sample_keywords)
    
    print(f"Total Keywords Analyzed: {root_analysis['total_keywords']}")
    print(f"Total Roots Found: {root_analysis['total_roots']}")
    print()
    
    print("Top 5 Ranked Roots:")
    for i, root in enumerate(root_analysis['ranked_roots'][:5], 1):
        print(f"{i}. '{root['root']}'")
        print(f"   - Total Search Volume: {root['total_search_volume']:,}")
        print(f"   - Keywords: {root['keyword_count']}")
        print(f"   - Design Specific: {root['is_design_specific']}")
        print(f"   - Categories: {', '.join(root['categories'])}")
        print()
    
    # Test 2: Keyword Variant Detection
    print("\nTEST 2: KEYWORD VARIANT DETECTION")
    print("-" * 80)
    
    variant_detector = KeywordVariantDetector()
    variant_analysis = variant_detector.detect_variants(sample_keywords)
    
    print(f"Total Variant Groups: {len(variant_analysis)}")
    print()
    
    print("Variant Groups (Top 3):")
    for i, group in enumerate(variant_analysis[:3], 1):
        print(f"{i}. Group: '{group['group_key']}'")
        print(f"   - Variants: {group['variant_count']}")
        print(f"   - Total Search Volume: {group['total_search_volume']:,}")
        print(f"   - Best Variant: '{group['best_variant']['original_keyword']}' (SV: {group['best_variant']['Search Volume']:,})")
        print(f"   - All Variants:")
        for v in group['variants']:
            print(f"     • {v['original_keyword']} (SV: {v['Search Volume']:,})")
        print()
    
    # Test 3: Variant Type Detection
    print("\nTEST 3: VARIANT TYPE DETECTION")
    print("-" * 80)
    
    test_pairs = [
        ('freeze dried strawberries', 'freeze dried strawberry'),
        ('freeze dried strawberries', 'the freeze dried strawberries'),
        ('freeze dried strawberries', 'strawberries freeze dried'),
    ]
    
    for kw1, kw2 in test_pairs:
        variant_type = variant_detector.get_variant_type(kw1, kw2)
        is_variant = variant_detector.is_variant(kw1, kw2)
        print(f"'{kw1}' vs '{kw2}'")
        print(f"  Is Variant: {is_variant}")
        print(f"  Type: {variant_type}")
        print()
    
    # Test 4: Current Content Analysis
    print("\nTEST 4: CURRENT CONTENT ANALYSIS")
    print("-" * 80)
    
    content_analyzer = CurrentContentAnalyzer()
    content_analysis = content_analyzer.analyze_content(
        current_title,
        current_bullets,
        sample_keywords
    )
    
    print("TITLE ANALYSIS:")
    print(f"Title: {content_analysis['title']['text']}")
    print(f"Character Count: {content_analysis['title']['character_count']}")
    print(f"Keywords Found: {content_analysis['title']['keyword_count']}")
    print(f"Total Search Volume: {content_analysis['title']['total_search_volume']:,}")
    print(f"Keyword Density: {content_analysis['title']['keyword_density']}")
    print(f"Roots Covered: {len(content_analysis['title']['roots_covered'])}")
    print()
    
    print("Keywords in Title:")
    for kw in content_analysis['title']['keywords_found']:
        print(f"  • {kw['keyword']} (SV: {kw['search_volume']:,}, Category: {kw['category']})")
    print()
    
    print("First 80 Characters:")
    print(f"  '{content_analysis['title']['first_80_chars']}'")
    print(f"  Keywords in First 80: {len(content_analysis['title']['keywords_in_first_80'])}")
    print()
    
    print("\nBULLET POINTS ANALYSIS:")
    print(f"Total Bullets: {content_analysis['bullets']['bullet_count']}")
    print(f"Total Keywords Found: {content_analysis['bullets']['total_keyword_count']}")
    print(f"Total Search Volume: {content_analysis['bullets']['total_search_volume']:,}")
    print(f"Total Character Count: {content_analysis['bullets']['total_character_count']}")
    print()
    
    for bullet in content_analysis['bullets']['bullets']:
        print(f"Bullet {bullet['bullet_number']}:")
        print(f"  Text: {bullet['text']}")
        print(f"  Characters: {bullet['character_count']}")
        print(f"  Keywords: {bullet['keyword_count']}")
        print(f"  Search Volume: {bullet['search_volume']:,}")
        if bullet['keywords_found']:
            print(f"  Keywords Found:")
            for kw in bullet['keywords_found']:
                print(f"    • {kw['keyword']} (SV: {kw['search_volume']:,})")
        print()
    
    print("\nOVERALL ANALYSIS:")
    print(f"Total Search Volume (Title + Bullets): {content_analysis['total_search_volume']:,}")
    print(f"Unique Roots Covered: {content_analysis['total_roots_covered']}")
    print(f"Roots: {', '.join(content_analysis['unique_roots_covered'][:5])}...")
    print()
    
    if content_analysis['duplicates']:
        print("DUPLICATE KEYWORDS FOUND:")
        for dup in content_analysis['duplicates']:
            print(f"  • '{dup['keyword']}' used {dup['count']} times")
    else:
        print("No duplicate keywords found ✓")
    
    print()
    print("=" * 80)
    print("PHASE 1 TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_phase1()
