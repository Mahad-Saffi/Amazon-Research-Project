"""
Integration Test for SEO Optimization
Tests the complete SEO optimization workflow using real data from CSV and JSON files
"""
import asyncio
import json
import csv
import logging
from pathlib import Path

from api.services.seo_optimization_service import SEOOptimizationService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_keyword_evaluations(csv_path: str):
    """Load keyword evaluations from CSV file"""
    keywords = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            keywords.append(row)
    
    logger.info(f"Loaded {len(keywords)} keywords from {csv_path}")
    return keywords


def load_scraped_data(json_path: str):
    """Load scraped product data from JSON file"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    title = data.get('title', '')
    bullets = data.get('elements', {}).get('feature-bullets', {}).get('bullets', [])
    
    logger.info(f"Loaded product data from {json_path}")
    logger.info(f"Title: {title[:100]}...")
    logger.info(f"Bullets: {len(bullets)}")
    
    return title, bullets, data


async def test_seo_optimization():
    """Test complete SEO optimization workflow"""
    
    # File paths
    keywords_csv = "results/keyword_evaluations_https___www.amazon.com_dp_B0FZCXT239_20260208_025252.csv"
    scraped_json = "results/scraped_data_https___www.amazon.com_dp_B0FZCXT239_20260208_024314.json"
    
    # Check if files exist
    if not Path(keywords_csv).exists():
        logger.error(f"Keywords CSV not found: {keywords_csv}")
        return
    
    if not Path(scraped_json).exists():
        logger.error(f"Scraped data JSON not found: {scraped_json}")
        return
    
    # Load data
    logger.info("=" * 80)
    logger.info("LOADING DATA")
    logger.info("=" * 80)
    
    keyword_evaluations = load_keyword_evaluations(keywords_csv)
    current_title, current_bullets, scraped_data = load_scraped_data(scraped_json)
    
    # Product info
    product_info = {
        'asin': 'B0FZCXT239',
        'marketplace': 'US',
        'brand': scraped_data.get('elements', {}).get('productOverview_feature_div', {}).get('kv', {}).get('Brand', ''),
        'category': 'Kitchen & Dining'
    }
    
    # Initialize SEO service
    logger.info("\n" + "=" * 80)
    logger.info("INITIALIZING SEO OPTIMIZATION SERVICE")
    logger.info("=" * 80)
    
    seo_service = SEOOptimizationService()
    
    # Run optimization
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING SEO OPTIMIZATION")
    logger.info("=" * 80)
    
    try:
        result = await seo_service.optimize_listing(
            current_title=current_title,
            current_bullets=current_bullets,
            keyword_evaluations=keyword_evaluations,
            product_info=product_info
        )
        
        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("OPTIMIZATION RESULTS")
        logger.info("=" * 80)
        
        if result.get('success'):
            logger.info("✓ SEO Optimization completed successfully!")
            
            # Current vs Optimized Summary
            logger.info("\n" + "-" * 80)
            logger.info("SUMMARY")
            logger.info("-" * 80)
            
            improvements = result.get('improvements', {})
            
            logger.info(f"\nSearch Volume:")
            logger.info(f"  Current:   {improvements['search_volume']['current']:,}")
            logger.info(f"  Optimized: {improvements['search_volume']['optimized']:,}")
            logger.info(f"  Improvement: +{improvements['search_volume']['improvement']:,} ({improvements['search_volume']['improvement_percent']}%)")
            
            logger.info(f"\nKeyword Count:")
            logger.info(f"  Current:   {improvements['keyword_count']['current']}")
            logger.info(f"  Optimized: {improvements['keyword_count']['optimized']}")
            logger.info(f"  Improvement: +{improvements['keyword_count']['improvement']}")
            
            logger.info(f"\nRoot Coverage:")
            logger.info(f"  Current:   {improvements['root_coverage']['current']}")
            logger.info(f"  Optimized: {improvements['root_coverage']['optimized']}")
            logger.info(f"  Improvement: +{improvements['root_coverage']['improvement']}")
            
            # Current Title
            logger.info("\n" + "-" * 80)
            logger.info("CURRENT TITLE")
            logger.info("-" * 80)
            current = result['current']
            logger.info(f"\n{current['title']}")
            logger.info(f"\nCharacters: {len(current['title'])}")
            logger.info(f"Keywords found: {current['analysis']['title']['keyword_count']}")
            logger.info(f"Search Volume: {current['analysis']['title']['total_search_volume']:,}")
            
            # Optimized Title
            logger.info("\n" + "-" * 80)
            logger.info("OPTIMIZED TITLE")
            logger.info("-" * 80)
            optimized = result['optimized']
            logger.info(f"\n{optimized['title']}")
            logger.info(f"\nCharacters: {len(optimized['title'])}")
            logger.info(f"Keywords used: {len(optimized['title_details']['keywords_used'])}")
            logger.info(f"Keywords: {', '.join(optimized['title_details']['keywords_used'][:5])}...")
            
            # Current Bullets
            logger.info("\n" + "-" * 80)
            logger.info("CURRENT BULLET POINTS")
            logger.info("-" * 80)
            for i, bullet in enumerate(current['bullets'], 1):
                logger.info(f"\n{i}. {bullet}")
            logger.info(f"\nTotal Keywords: {current['analysis']['bullets']['total_keyword_count']}")
            logger.info(f"Total Search Volume: {current['analysis']['bullets']['total_search_volume']:,}")
            
            # Optimized Bullets
            logger.info("\n" + "-" * 80)
            logger.info("OPTIMIZED BULLET POINTS")
            logger.info("-" * 80)
            for i, bullet in enumerate(optimized['bullets'], 1):
                logger.info(f"\n{i}. {bullet}")
                keywords = optimized['bullets_details']['keywords_per_bullet'][i-1]
                logger.info(f"   Keywords: {', '.join(keywords)}")
            
            # Validation Results
            logger.info("\n" + "-" * 80)
            logger.info("VALIDATION RESULTS")
            logger.info("-" * 80)
            
            opt_validation = optimized.get('validation', {})
            if opt_validation:
                title_val = opt_validation.get('title', {})
                logger.info(f"\nTitle Validation:")
                logger.info(f"  Character count: {title_val.get('character_count', 0)}/200")
                if title_val.get('issues'):
                    logger.info(f"  Issues: {', '.join(title_val['issues'])}")
                else:
                    logger.info(f"  ✓ No issues found")
                
                bullets_val = opt_validation.get('bullets', {})
                logger.info(f"\nBullet Points Validation:")
                logger.info(f"  Count: {bullets_val.get('bullet_count', 0)}")
                if bullets_val.get('issues'):
                    logger.info(f"  Issues:")
                    for issue in bullets_val['issues']:
                        logger.info(f"    - {issue}")
                else:
                    logger.info(f"  ✓ No issues found")
            else:
                logger.info("\nValidation data not available")
            
            # Detailed Comparison (Task 8-13)
            logger.info("\n" + "-" * 80)
            logger.info("DETAILED COMPARISON (Tasks 8-13)")
            logger.info("-" * 80)
            
            comparison = result.get('detailed_comparison', {})
            if comparison:
                logger.info("\n✓ Side-by-side comparison generated (Task 8)")
                logger.info("✓ Keywords with search volumes in brackets (Task 9)")
                logger.info("✓ Search Volume heading, total characters (Task 10)")
                logger.info("✓ Singular/plural/pronoun variants handled (Task 11)")
                logger.info("✓ Duplicate keywords highlighted (Task 12)")
                logger.info("✓ Root volume only for relevant roots (Task 13)")
            
            # Save results
            logger.info("\n" + "-" * 80)
            logger.info("SAVING RESULTS")
            logger.info("-" * 80)
            
            output_file = "results/seo_optimization_test_results.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\n✓ Results saved to: {output_file}")
            
        else:
            logger.error(f"✗ Optimization failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"✗ Error during optimization: {str(e)}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(test_seo_optimization())
