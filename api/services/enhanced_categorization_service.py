"""
Enhanced irrelevant categorization service
Categorizes irrelevant keywords as 'irrelevant' or 'competitor_relevant'
using Python logic + competitor title scraping
"""
import logging
from typing import List, Dict, Any

from research_agents.enhanced_irrelevant_logic import categorize_irrelevant_keywords
from Experimental.amazon_keyword_scraper import AmazonKeywordScraper

logger = logging.getLogger(__name__)


def safe_int(value, default=0):
    """Safely convert value to int, handling strings, None, and invalid values"""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            # Remove commas and whitespace
            cleaned = value.replace(',', '').strip()
            return int(float(cleaned))
        except (ValueError, AttributeError):
            return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


class EnhancedCategorizationService:
    """
    Categorize irrelevant keywords using Python logic and competitor scraping
    
    Flow:
    1. Get irrelevant keywords from categorization
    2. Get top 3 relevant keywords by search volume
    3. Scrape competitor titles for those 3 keywords
    4. Use Python function to extract modifiers from irrelevant keywords
    5. Check if modifiers appear in competitor titles
    6. If found → 'competitor_relevant' (market demand exists)
    7. If not found → 'irrelevant' (no market demand)
    """
    
    def categorize_irrelevant_keywords(
        self,
        keyword_evaluations: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Categorize irrelevant keywords as 'irrelevant' or 'competitor_relevant'
        
        Args:
            keyword_evaluations: List of keyword categorizations with category and search volume
        
        Returns:
            Dict mapping keyword to enhanced category ('irrelevant' or 'competitor_relevant')
        """
        # Extract irrelevant keywords
        irrelevant_keywords = [
            cat.get('keyword') for cat in keyword_evaluations 
            if cat.get('category') == 'irrelevant'
        ]
        
        # Get top 3 relevant keywords by search volume
        relevant_keywords_sorted = sorted(
            [cat for cat in keyword_evaluations 
             if cat.get('category') in ['relevant', 'design_specific']],
            key=lambda x: safe_int(x.get('Search Volume')),
            reverse=True
        )[:3]
        
        relevant_keywords = [cat.get('keyword') for cat in relevant_keywords_sorted]
        
        # Check if we have data to process
        if not irrelevant_keywords or not relevant_keywords:
            logger.info("Skipping enhanced categorization: need irrelevant and relevant keywords")
            return {}
        
        logger.info(f"Enhanced categorization: {len(irrelevant_keywords)} irrelevant keywords")
        logger.info(f"Using top 3 relevant keywords: {relevant_keywords}")
        
        try:
            # Scrape competitor titles
            competitor_titles = self._scrape_competitor_titles(relevant_keywords)
            
            if not competitor_titles:
                logger.warning("No competitor titles scraped - skipping enhanced categorization")
                return {}
            
            logger.info(f"Scraped {len(competitor_titles)} competitor titles")
            
            # Use Python function to categorize
            enhanced_categories = categorize_irrelevant_keywords(
                irrelevant_keywords,
                relevant_keywords,
                competitor_titles
            )
            
            # Count results
            competitor_relevant_count = sum(
                1 for cat in enhanced_categories.values() 
                if cat == 'competitor_relevant'
            )
            
            logger.info(f"Enhanced categorization: {competitor_relevant_count} competitor_relevant, "
                       f"{len(enhanced_categories) - competitor_relevant_count} irrelevant")
            
            return enhanced_categories
            
        except Exception as e:
            logger.error(f"Error in enhanced categorization: {str(e)}")
            return {}
    
    def _scrape_competitor_titles(self, relevant_keywords: List[str]) -> List[str]:
        """
        Scrape competitor titles for top 3 relevant keywords
        Returns only organic (non-sponsored) titles
        
        Args:
            relevant_keywords: Top 3 relevant keywords
        
        Returns:
            List of organic competitor product titles (~144 titles: 3 keywords × ~48 organic titles each)
        """
        all_titles = []
        scraper = AmazonKeywordScraper()
        
        try:
            scraper.warm_up()
            
            for keyword in relevant_keywords:
                try:
                    logger.info(f"Scraping competitor titles for: {keyword}")
                    html = scraper.scrape_search_html(keyword, page=1)
                    titles = scraper.extract_product_titles(html)
                    all_titles.extend(titles)
                    logger.info(f"Scraped {len(titles)} titles for '{keyword}'")
                except Exception as e:
                    logger.warning(f"Could not scrape '{keyword}': {str(e)}")
                    continue
        finally:
            scraper.close()
        
        return all_titles
    
    def apply_enhanced_categories(
        self,
        keyword_evaluations: List[Dict[str, Any]],
        enhanced_categories: Dict[str, str]
    ) -> int:
        """
        Apply enhanced categories to keyword evaluations
        
        Args:
            keyword_evaluations: List of keyword categorizations to update
            enhanced_categories: Dict mapping keyword to enhanced category
        
        Returns:
            Number of keywords updated to competitor_relevant
        """
        competitor_relevant_count = 0
        
        for cat in keyword_evaluations:
            keyword = cat.get('keyword')
            if keyword in enhanced_categories:
                new_category = enhanced_categories[keyword]
                if new_category == 'competitor_relevant':
                    cat['category'] = 'competitor_relevant'
                    cat['reasoning'] = 'Market demand exists for this variation, but we do not offer it'
                    competitor_relevant_count += 1
                    logger.debug(f"Updated '{keyword}' to competitor_relevant")
        
        logger.info(f"Applied enhanced categories: {competitor_relevant_count} keywords → competitor_relevant")
        return competitor_relevant_count
