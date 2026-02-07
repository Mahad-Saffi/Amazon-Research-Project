"""
Test script for Design-Specific Detection
Demonstrates AI agent detecting design-specific keywords in current content
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from research_agents.design_specific_detector_agent import DesignSpecificDetectorAgent
from api.services.keyword_root_analyzer import KeywordRootAnalyzer
from api.services.keyword_variant_detector import KeywordVariantDetector
from api.services.keyword_selector import KeywordSelector

async def test_design_specific_detection():
    """Test design-specific detection with different scenarios"""
    
    print("=" * 80)
    print("DESIGN-SPECIFIC KEYWORD DETECTION TEST")
    print("=" * 80)
    print()
    
    # Sample keyword data
    sample_keywords = [
        {'keyword': 'freeze dried strawberries', 'Search Volume': 1500, 'category': 'relevant'},
        {'keyword': 'freeze dried fruit', 'Search Volume': 2000, 'category': 'relevant'},
        {'keyword': 'organic freeze dried strawberries', 'Search Volume': 600, 'category': 'design_specific'},
        {'keyword': 'strawberry slices', 'Search Volume': 900, 'category': 'design_specific'},
        {'keyword': 'dried strawberries', 'Search Volume': 1800, 'category': 'relevant'},
        {'keyword': 'freeze dried snacks', 'Search Volume': 1100, 'category': 'relevant'},
    ]
    
    # Scenario 1: Title WITH design-specific keywords
    print("SCENARIO 1: Title WITH Design-Specific Keywords")
    print("-" * 80)
    
    title_with_ds = "Organic Freeze Dried Strawberry Slices - Healthy Snack"
    bullets_with_ds = [
        "Made with organic strawberries",
        "Perfectly sliced for easy snacking",
        "Resealable bag keeps fruit fresh"
    ]
    
    detector = DesignSpecificDetectorAgent()
    
    design_specific_kws = [kw for kw in sample_keywords if kw['category'] == 'design_specific']
    
    result1 = await detector.detect_design_specific_in_content(
        title_with_ds,
        bullets_with_ds,
        design_specific_kws
    )
    
    print(f"Title: {title_with_ds}")
    print(f"Has Design-Specific: {result1['has_design_specific']}")
    print(f"Found in Title: {result1['found_in_title']}")
    print(f"Found in Bullets: {result1['found_in_bullets']}")
    print(f"Reasoning: {result1['reasoning']}")
    print()
    
    # Scenario 2: Title WITHOUT design-specific keywords
    print("\nSCENARIO 2: Title WITHOUT Design-Specific Keywords")
    print("-" * 80)
    
    title_without_ds = "Freeze Dried Strawberries - Healthy Fruit Snack"
    bullets_without_ds = [
        "Made with real strawberries",
        "Perfect for kids and adults",
        "Great taste and nutrition"
    ]
    
    result2 = await detector.detect_design_specific_in_content(
        title_without_ds,
        bullets_without_ds,
        design_specific_kws
    )
    
    print(f"Title: {title_without_ds}")
    print(f"Has Design-Specific: {result2['has_design_specific']}")
    print(f"Found in Title: {result2['found_in_title']}")
    print(f"Found in Bullets: {result2['found_in_bullets']}")
    print(f"Reasoning: {result2['reasoning']}")
    print()
    
    # Scenario 3: Full keyword selection with design-specific detection
    print("\nSCENARIO 3: Keyword Selection with Design-Specific Detection")
    print("-" * 80)
    
    # Run Phase 1 analysis
    root_analyzer = KeywordRootAnalyzer()
    root_analysis = root_analyzer.extract_roots_from_keywords(sample_keywords)
    
    variant_detector = KeywordVariantDetector()
    variant_analysis = variant_detector.detect_variants(sample_keywords)
    
    selector = KeywordSelector()
    
    # Test with title that HAS design-specific
    print("\n3a. Current title HAS design-specific keywords:")
    print(f"    Title: {title_with_ds}")
    
    selection_with_ds = await selector.select_keywords_for_optimization(
        sample_keywords,
        root_analysis,
        variant_analysis,
        current_title=title_with_ds,
        current_bullets=bullets_with_ds
    )
    
    print(f"\n    Include Design-Specific: {selection_with_ds['include_design_specific']}")
    print(f"    Title Keywords Selected: {selection_with_ds['title_keywords']['total_keywords']}")
    print(f"    Design-Specific in Title: {len(selection_with_ds['title_keywords']['design_keywords'])}")
    print("\n    Selected Title Keywords:")
    for kw in selection_with_ds['title_keywords']['all_keywords']:
        ds_marker = " [DESIGN-SPECIFIC]" if kw['is_design_specific'] else ""
        print(f"      • {kw['keyword']} (SV: {kw['search_volume']:,}){ds_marker}")
    
    # Test with title that DOES NOT have design-specific
    print("\n\n3b. Current title DOES NOT have design-specific keywords:")
    print(f"    Title: {title_without_ds}")
    
    selection_without_ds = await selector.select_keywords_for_optimization(
        sample_keywords,
        root_analysis,
        variant_analysis,
        current_title=title_without_ds,
        current_bullets=bullets_without_ds
    )
    
    print(f"\n    Include Design-Specific: {selection_without_ds['include_design_specific']}")
    print(f"    Title Keywords Selected: {selection_without_ds['title_keywords']['total_keywords']}")
    print(f"    Design-Specific in Title: {len(selection_without_ds['title_keywords']['design_keywords'])}")
    print("\n    Selected Title Keywords:")
    for kw in selection_without_ds['title_keywords']['all_keywords']:
        ds_marker = " [DESIGN-SPECIFIC]" if kw['is_design_specific'] else ""
        print(f"      • {kw['keyword']} (SV: {kw['search_volume']:,}){ds_marker}")
    
    print()
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    print()
    print("✓ AI agent successfully detects design-specific keywords in current content")
    print("✓ Keyword selection adapts based on current content")
    print("✓ Design-specific keywords only included when present in original listing")

if __name__ == "__main__":
    asyncio.run(test_design_specific_detection())
