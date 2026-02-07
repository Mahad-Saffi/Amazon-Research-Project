"""
Keyword Variant Detector Service
Detects and groups keyword variants (singular/plural, pronouns, etc.)
"""
import logging
from typing import List, Dict, Any, Set, Tuple
import re

logger = logging.getLogger(__name__)

class KeywordVariantDetector:
    """Detects keyword variants like singular/plural, pronoun differences"""
    
    def __init__(self):
        # Common pronouns and articles
        self.pronouns_articles = {
            'a', 'an', 'the', 'this', 'that', 'these', 'those',
            'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
    
    def detect_variants(
        self,
        keywords: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect and group keyword variants
        
        Args:
            keywords: List of keyword dicts with 'keyword' and 'Search Volume'
        
        Returns:
            List of variant groups with best representative selected
        """
        # Group keywords by their normalized form
        variant_groups = self._group_variants(keywords)
        
        # Select best representative for each group
        variant_analysis = []
        for group_key, variants in variant_groups.items():
            best_variant = self._select_best_variant(variants)
            variant_analysis.append({
                'group_key': group_key,
                'variants': variants,
                'best_variant': best_variant,
                'variant_count': len(variants),
                'total_search_volume': sum(v.get('Search Volume', 0) or 0 for v in variants)
            })
        
        # Sort by total search volume
        variant_analysis.sort(key=lambda x: x['total_search_volume'], reverse=True)
        
        return variant_analysis
    
    def _group_variants(
        self,
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group keywords that are variants of each other
        
        Variants include:
        - Singular/plural: "strawberry" vs "strawberries"
        - Pronoun/article differences: "the strawberry" vs "a strawberry"
        - Word order is NOT a variant: "freeze dried strawberry" vs "strawberry freeze dried"
        """
        from collections import defaultdict
        variant_groups = defaultdict(list)
        
        for kw in keywords:
            keyword_phrase = kw.get('keyword', '') or kw.get('Keyword Phrase', '')
            if not keyword_phrase:
                continue
            
            # Normalize to create group key
            normalized = self._normalize_keyword(keyword_phrase)
            variant_groups[normalized].append({
                **kw,
                'original_keyword': keyword_phrase
            })
        
        return dict(variant_groups)
    
    def _normalize_keyword(self, keyword: str) -> str:
        """
        Normalize keyword to group variants
        
        Steps:
        1. Remove pronouns/articles from start
        2. Convert to singular form (basic rules)
        3. Lowercase and strip
        """
        keyword_lower = keyword.lower().strip()
        words = keyword_lower.split()
        
        # Remove leading pronouns/articles
        while words and words[0] in self.pronouns_articles:
            words.pop(0)
        
        # Remove trailing pronouns/articles
        while words and words[-1] in self.pronouns_articles:
            words.pop()
        
        if not words:
            return keyword_lower
        
        # Convert last word to singular (basic rules)
        # This handles most common cases
        words[-1] = self._singularize(words[-1])
        
        return ' '.join(words)
    
    def _singularize(self, word: str) -> str:
        """
        Basic singularization rules
        
        Note: This is simplified. For production, consider using inflect library
        """
        # Common plural patterns
        if word.endswith('ies') and len(word) > 4:
            # berries -> berry
            return word[:-3] + 'y'
        elif word.endswith('es') and len(word) > 3:
            # boxes -> box, but not "es" words like "yes"
            if word.endswith('ses') or word.endswith('ches') or word.endswith('shes') or word.endswith('xes'):
                return word[:-2]
            return word[:-1]
        elif word.endswith('s') and len(word) > 2:
            # Remove trailing 's' if not part of the word
            # Check if it's likely a plural
            if not word.endswith('ss') and not word.endswith('us'):
                return word[:-1]
        
        return word
    
    def _select_best_variant(
        self,
        variants: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Select the best variant from a group
        
        Selection criteria:
        1. Highest search volume
        2. If volumes are close (within 20%), prefer grammatically simpler
        3. Prefer no pronouns/articles
        """
        if not variants:
            return None
        
        if len(variants) == 1:
            return variants[0]
        
        # Sort by search volume
        sorted_variants = sorted(
            variants,
            key=lambda x: int(x.get('Search Volume', 0) or 0),
            reverse=True
        )
        
        highest_volume = int(sorted_variants[0].get('Search Volume', 0) or 0)
        
        # Check if top variants have similar volume (within 20%)
        similar_volume_variants = []
        for v in sorted_variants:
            volume = int(v.get('Search Volume', 0) or 0)
            if volume >= highest_volume * 0.8:
                similar_volume_variants.append(v)
            else:
                break
        
        # If multiple variants have similar volume, prefer simpler form
        if len(similar_volume_variants) > 1:
            # Prefer variant without pronouns/articles
            for v in similar_volume_variants:
                keyword = v.get('original_keyword', '')
                words = keyword.lower().split()
                if words and words[0] not in self.pronouns_articles:
                    return v
        
        # Default to highest volume
        return sorted_variants[0]
    
    def is_variant(self, keyword1: str, keyword2: str) -> bool:
        """
        Check if two keywords are variants of each other
        
        Args:
            keyword1: First keyword
            keyword2: Second keyword
        
        Returns:
            True if they are variants, False otherwise
        """
        norm1 = self._normalize_keyword(keyword1)
        norm2 = self._normalize_keyword(keyword2)
        
        return norm1 == norm2
    
    def get_variant_type(self, keyword1: str, keyword2: str) -> str:
        """
        Determine the type of variant relationship
        
        Returns:
            'singular_plural', 'pronoun_article', 'identical', or 'not_variant'
        """
        if keyword1.lower() == keyword2.lower():
            return 'identical'
        
        if not self.is_variant(keyword1, keyword2):
            return 'not_variant'
        
        # Check for pronoun/article difference
        words1 = keyword1.lower().split()
        words2 = keyword2.lower().split()
        
        # Remove pronouns/articles
        words1_clean = [w for w in words1 if w not in self.pronouns_articles]
        words2_clean = [w for w in words2 if w not in self.pronouns_articles]
        
        if words1_clean == words2_clean:
            return 'pronoun_article'
        
        # Must be singular/plural
        return 'singular_plural'
