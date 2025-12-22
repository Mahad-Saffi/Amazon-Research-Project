"""
Enhanced irrelevant categorization logic.
Categorizes irrelevant keywords as either 'irrelevant' or 'competitor_relevant'
by scraping competitor titles and checking if modifiers appear in them.
"""
import logging
from typing import List, Dict, Any
from research_agents.modifier_extractor import extract_modifiers, find_modifier_in_titles

logger = logging.getLogger(__name__)


def categorize_irrelevant_keywords(
    irrelevant_keywords: List[str],
    relevant_keywords: List[str],
    competitor_titles: List[str]
) -> Dict[str, str]:
    """
    Categorize irrelevant keywords as either 'irrelevant' or 'competitor_relevant'
    by checking if modifiers appear in competitor titles.
    
    Logic:
    - Extract meaningful modifiers from each irrelevant keyword
    - Check if modifiers appear in any of the 144 competitor titles (3 keywords × 48 titles)
    - If modifiers found in titles → mark as 'competitor_relevant' (market demand exists)
    - If modifiers NOT found in titles → mark as 'irrelevant' (no market demand)
    
    Args:
        irrelevant_keywords: List of keywords marked as irrelevant
        relevant_keywords: List of top 3 relevant keywords (for context)
        competitor_titles: List of ~144 competitor titles (3 keywords × ~48 titles each)
    
    Returns:
        Dict mapping keyword to category ('irrelevant' or 'competitor_relevant')
    """
    categories = {}
    
    for keyword in irrelevant_keywords:
        # Extract meaningful modifiers
        modifiers = extract_modifiers(keyword, relevant_keywords)
        
        if not modifiers:
            # No meaningful modifiers → irrelevant
            categories[keyword] = 'irrelevant'
            logger.debug(f"'{keyword}' → irrelevant (no meaningful modifiers)")
            continue
        
        # Check if any modifier appears in competitor titles
        found_in_titles = False
        for modifier in modifiers:
            found, matching_titles = find_modifier_in_titles(modifier, competitor_titles)
            if found:
                found_in_titles = True
                logger.debug(f"'{keyword}': modifier '{modifier}' found in {len(matching_titles)} competitor titles")
                break
        
        if found_in_titles:
            # Modifiers found in competitor titles → competitor_relevant
            # (market demand exists for this variation, but we don't offer it)
            categories[keyword] = 'competitor_relevant'
            logger.debug(f"'{keyword}' → competitor_relevant (modifiers found in competitor titles)")
        else:
            # Modifiers NOT found in competitor titles → irrelevant
            # (no market demand for this variation)
            categories[keyword] = 'irrelevant'
            logger.debug(f"'{keyword}' → irrelevant (modifiers not found in competitor titles)")
    
    return categories


class EnhancedIrrelevantCategorizer:
    """
    Simplified categorizer using Python logic only.
    """
    
    def __init__(self, product_title: str, product_bullets: List[str]):
        """
        Initialize with product information.
        
        Args:
            product_title: Product title from Amazon listing
            product_bullets: List of product bullet points
        """
        self.product_title = product_title
        self.product_bullets = product_bullets
        self.product_text = f"{product_title} {' '.join(product_bullets)}".lower()
    
    def categorize_irrelevant(
        self,
        irrelevant_keywords: List[str],
        relevant_keywords: List[str]
    ) -> Dict[str, str]:
        """
        Categorize irrelevant keywords using Python logic.
        
        Args:
            irrelevant_keywords: List of irrelevant keywords to categorize
            relevant_keywords: Top relevant keywords for context
        
        Returns:
            Dict mapping keyword to category ('irrelevant' or 'competitor_relevant')
        """
        return categorize_irrelevant_keywords(irrelevant_keywords, relevant_keywords)
