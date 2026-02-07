"""
Keyword Root Analyzer Service
Extracts and analyzes keyword roots from research data
"""
import logging
from typing import List, Dict, Any, Set
from collections import defaultdict
import re

logger = logging.getLogger(__name__)

class KeywordRootAnalyzer:
    """Analyzes keyword roots and groups keywords by their roots"""
    
    def __init__(self):
        # Common stop words to ignore when extracting roots
        self.stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'should', 'could', 'may', 'might', 'must', 'can'
        }
    
    def extract_roots_from_keywords(
        self,
        keyword_evaluations: List[Dict[str, Any]],
        relevant_categories: List[str] = None
    ) -> Dict[str, Any]:
        """
        Extract and analyze keyword roots from evaluation data
        
        Args:
            keyword_evaluations: List of keyword evaluation dicts
            relevant_categories: Categories to include (default: relevant, design_specific)
        
        Returns:
            Dict with root analysis data
        """
        if relevant_categories is None:
            relevant_categories = ['relevant', 'design_specific']
        
        # Filter to relevant keywords only
        relevant_keywords = [
            kw for kw in keyword_evaluations
            if kw.get('category') in relevant_categories
        ]
        
        logger.info(f"Analyzing {len(relevant_keywords)} relevant keywords")
        
        # Group keywords by root
        root_groups = self._group_keywords_by_root(relevant_keywords)
        
        # Calculate root statistics
        root_stats = self._calculate_root_statistics(root_groups)
        
        # Rank roots by importance
        ranked_roots = self._rank_roots(root_stats)
        
        return {
            'root_groups': root_groups,
            'root_stats': root_stats,
            'ranked_roots': ranked_roots,
            'total_keywords': len(relevant_keywords),
            'total_roots': len(root_groups)
        }
    
    def _group_keywords_by_root(
        self,
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group keywords by their root phrases
        
        A root is the core meaningful phrase in a keyword
        Example: "freeze dried strawberries" -> root: "freeze dried strawberry"
        """
        root_groups = defaultdict(list)
        
        for kw in keywords:
            keyword_phrase = kw.get('keyword', '') or kw.get('Keyword Phrase', '')
            if not keyword_phrase:
                continue
            
            # Extract potential roots
            roots = self._extract_roots(keyword_phrase)
            
            # Add to all matching root groups
            for root in roots:
                root_groups[root].append(kw)
        
        return dict(root_groups)
    
    def _extract_roots(self, keyword: str) -> List[str]:
        """
        Extract potential roots from a keyword
        
        Strategy:
        1. Extract 2-3 word phrases (most common root length)
        2. Remove stop words from edges
        3. Return all potential roots
        """
        keyword_lower = keyword.lower().strip()
        words = keyword_lower.split()
        
        roots = []
        
        # Extract 2-word roots
        for i in range(len(words) - 1):
            two_word = f"{words[i]} {words[i+1]}"
            if not self._is_stop_word(words[i]) and not self._is_stop_word(words[i+1]):
                roots.append(two_word)
        
        # Extract 3-word roots
        for i in range(len(words) - 2):
            three_word = f"{words[i]} {words[i+1]} {words[i+2]}"
            if not self._is_stop_word(words[i]) and not self._is_stop_word(words[i+2]):
                roots.append(three_word)
        
        # Also add the full keyword as a potential root if it's 2-4 words
        if 2 <= len(words) <= 4:
            roots.append(keyword_lower)
        
        return roots
    
    def _is_stop_word(self, word: str) -> bool:
        """Check if word is a stop word"""
        return word.lower() in self.stop_words
    
    def _calculate_root_statistics(
        self,
        root_groups: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate statistics for each root
        
        Returns list of dicts with:
        - root: root phrase
        - keyword_count: number of keywords with this root
        - total_search_volume: sum of search volumes
        - avg_search_volume: average search volume
        - max_search_volume: highest search volume keyword
        - categories: set of categories present
        - keywords: list of keywords with this root
        """
        root_stats = []
        
        for root, keywords in root_groups.items():
            search_volumes = []
            categories = set()
            
            for kw in keywords:
                # Get search volume
                sv = kw.get('Search Volume', 0)
                if sv:
                    try:
                        search_volumes.append(int(sv))
                    except (ValueError, TypeError):
                        pass
                
                # Get category
                cat = kw.get('category', '')
                if cat:
                    categories.add(cat)
            
            total_sv = sum(search_volumes)
            avg_sv = total_sv / len(search_volumes) if search_volumes else 0
            max_sv = max(search_volumes) if search_volumes else 0
            
            root_stats.append({
                'root': root,
                'keyword_count': len(keywords),
                'total_search_volume': total_sv,
                'avg_search_volume': int(avg_sv),
                'max_search_volume': max_sv,
                'categories': list(categories),
                'keywords': keywords,
                'is_design_specific': 'design_specific' in categories
            })
        
        return root_stats
    
    def _rank_roots(
        self,
        root_stats: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Rank roots by importance
        
        Ranking criteria:
        1. Design-specific roots get priority
        2. Total search volume
        3. Number of keywords
        """
        # Separate design-specific and regular roots
        design_roots = [r for r in root_stats if r['is_design_specific']]
        regular_roots = [r for r in root_stats if not r['is_design_specific']]
        
        # Sort design-specific by total search volume
        design_roots.sort(key=lambda x: x['total_search_volume'], reverse=True)
        
        # Sort regular by total search volume
        regular_roots.sort(key=lambda x: x['total_search_volume'], reverse=True)
        
        # Combine: design-specific first, then regular
        ranked = design_roots + regular_roots
        
        # Add rank number
        for i, root in enumerate(ranked, 1):
            root['rank'] = i
        
        return ranked
    
    def get_top_roots(
        self,
        ranked_roots: List[Dict[str, Any]],
        top_n: int = 10,
        include_design_specific: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get top N roots
        
        Args:
            ranked_roots: List of ranked roots
            top_n: Number of roots to return
            include_design_specific: Whether to include design-specific roots
        
        Returns:
            List of top roots
        """
        if include_design_specific:
            return ranked_roots[:top_n]
        else:
            regular_roots = [r for r in ranked_roots if not r['is_design_specific']]
            return regular_roots[:top_n]
    
    def get_design_specific_roots(
        self,
        ranked_roots: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get all design-specific roots"""
        return [r for r in ranked_roots if r['is_design_specific']]
