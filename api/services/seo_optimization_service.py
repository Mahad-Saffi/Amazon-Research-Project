"""
SEO Optimization Service
Main service that orchestrates SEO optimization for titles and bullet points
"""
import logging
from typing import List, Dict, Any

from api.services.keyword_root_analyzer import KeywordRootAnalyzer
from api.services.keyword_variant_detector import KeywordVariantDetector
from api.services.current_content_analyzer import CurrentContentAnalyzer
from api.services.keyword_selector import KeywordSelector
from api.services.amazon_guidelines_validator import AmazonGuidelinesValidator
from api.services.seo_comparison_service import SEOComparisonService
from research_agents.seo_content_generator_agent import SEOContentGeneratorAgent

logger = logging.getLogger(__name__)

class SEOOptimizationService:
    """Main service for SEO optimization"""
    
    def __init__(self):
        self.root_analyzer = KeywordRootAnalyzer()
        self.variant_detector = KeywordVariantDetector()
        self.content_analyzer = CurrentContentAnalyzer()
        self.keyword_selector = KeywordSelector()
        self.validator = AmazonGuidelinesValidator()
        self.content_generator = SEOContentGeneratorAgent()
        self.comparison_service = SEOComparisonService()
    
    async def optimize_listing(
        self,
        current_title: str,
        current_bullets: List[str],
        keyword_evaluations: List[Dict[str, Any]],
        product_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Complete SEO optimization workflow
        
        Args:
            current_title: Current product title
            current_bullets: Current bullet points
            keyword_evaluations: Keyword research data
            product_info: Additional product info (brand, category, etc.)
        
        Returns:
            Dict with complete optimization results
        """
        logger.info("Starting SEO optimization...")
        
        # Phase 1: Analyze current content
        logger.info("Phase 1: Analyzing current content...")
        current_analysis = self.content_analyzer.analyze_content(
            current_title,
            current_bullets,
            keyword_evaluations
        )
        
        # Phase 1: Extract roots and detect variants
        logger.info("Phase 1: Extracting keyword roots...")
        root_analysis = self.root_analyzer.extract_roots_from_keywords(
            keyword_evaluations,
            relevant_categories=['relevant', 'design_specific']
        )
        
        logger.info("Phase 1: Detecting keyword variants...")
        variant_analysis = self.variant_detector.detect_variants(keyword_evaluations)
        
        # Phase 2: Select keywords
        logger.info("Phase 2: Selecting optimal keywords...")
        keyword_selection = await self.keyword_selector.select_keywords_for_optimization(
            keyword_evaluations,
            root_analysis,
            variant_analysis,
            current_title=current_title,
            current_bullets=current_bullets
        )
        
        # Phase 3: Generate optimized content
        logger.info("Phase 3: Generating optimized title...")
        optimized_title_result = await self.content_generator.generate_optimized_title(
            current_title,
            keyword_selection['title_keywords']['all_keywords'],
            product_info
        )
        
        logger.info("Phase 3: Generating optimized bullet points...")
        optimized_bullets_result = await self.content_generator.generate_optimized_bullets(
            current_bullets,
            keyword_selection['bullet_keywords']['all_keywords'],
            product_info
        )
        
        # Validate optimized content
        logger.info("Validating optimized content...")
        optimized_validation = self.validator.validate_all(
            optimized_title_result['optimized_title'],
            optimized_bullets_result['bullet_points']
        )
        
        # Validate current content for comparison
        current_validation = self.validator.validate_all(
            current_title,
            current_bullets
        )
        
        # Calculate improvements
        improvements = self._calculate_improvements(
            current_analysis,
            keyword_selection,
            optimized_title_result,
            optimized_bullets_result
        )
        
        # Create detailed comparison (Task 8, 9, 10, 12, 13)
        detailed_comparison = self.comparison_service.create_comparison(
            current_title,
            current_bullets,
            optimized_title_result['optimized_title'],
            optimized_bullets_result['bullet_points'],
            current_analysis,
            keyword_selection,
            optimized_title_result,
            optimized_bullets_result
        )
        
        logger.info("SEO optimization complete!")
        
        return {
            'success': True,
            'current': {
                'title': current_title,
                'bullets': current_bullets,
                'analysis': current_analysis,
                'validation': current_validation
            },
            'optimized': {
                'title': optimized_title_result['optimized_title'],
                'bullets': optimized_bullets_result['bullet_points'],
                'title_details': optimized_title_result,
                'bullets_details': optimized_bullets_result,
                'validation': optimized_validation
            },
            'keyword_selection': keyword_selection,
            'improvements': improvements,
            'detailed_comparison': detailed_comparison,  # Task 8, 9, 10, 12, 13
            'root_analysis': {
                'total_roots': root_analysis['total_roots'],
                'top_roots': root_analysis['ranked_roots'][:10]
            }
        }
    
    def _calculate_improvements(
        self,
        current_analysis: Dict[str, Any],
        keyword_selection: Dict[str, Any],
        optimized_title: Dict[str, Any],
        optimized_bullets: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate improvement metrics"""
        
        # Current search volume
        current_title_sv = current_analysis['title']['total_search_volume']
        current_bullets_sv = current_analysis['bullets']['total_search_volume']
        current_total_sv = current_title_sv + current_bullets_sv
        
        # Optimized search volume
        optimized_title_sv = keyword_selection['title_keywords']['total_search_volume']
        optimized_bullets_sv = keyword_selection['bullet_keywords']['total_search_volume']
        optimized_total_sv = optimized_title_sv + optimized_bullets_sv
        
        # Calculate improvements
        sv_improvement = optimized_total_sv - current_total_sv
        sv_improvement_pct = (sv_improvement / current_total_sv * 100) if current_total_sv > 0 else 0
        
        # Keyword count improvements
        current_keyword_count = (
            current_analysis['title']['keyword_count'] +
            current_analysis['bullets']['total_keyword_count']
        )
        optimized_keyword_count = (
            keyword_selection['title_keywords']['total_keywords'] +
            keyword_selection['bullet_keywords']['total_keywords']
        )
        
        # Root coverage improvements
        current_roots = current_analysis['total_roots_covered']
        optimized_roots = len(set(
            [kw['root'] for kw in keyword_selection['title_keywords']['all_keywords']] +
            [kw['root'] for kw in keyword_selection['bullet_keywords']['all_keywords']]
        ))
        
        improvements_list = []
        
        if sv_improvement > 0:
            improvements_list.append(f"Increased search volume by {sv_improvement:,} ({sv_improvement_pct:.1f}%)")
        
        if optimized_keyword_count > current_keyword_count:
            improvements_list.append(f"Added {optimized_keyword_count - current_keyword_count} more keywords")
        
        if optimized_roots > current_roots:
            improvements_list.append(f"Covered {optimized_roots - current_roots} more keyword roots")
        
        if keyword_selection.get('include_design_specific'):
            improvements_list.append("Maintained design-specific positioning")
        
        return {
            'search_volume': {
                'current': current_total_sv,
                'optimized': optimized_total_sv,
                'improvement': sv_improvement,
                'improvement_percent': round(sv_improvement_pct, 1)
            },
            'keyword_count': {
                'current': current_keyword_count,
                'optimized': optimized_keyword_count,
                'improvement': optimized_keyword_count - current_keyword_count
            },
            'root_coverage': {
                'current': current_roots,
                'optimized': optimized_roots,
                'improvement': optimized_roots - current_roots
            },
            'summary': improvements_list
        }
