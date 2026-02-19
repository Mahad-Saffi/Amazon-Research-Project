"""
Keyword Root Analyzer Service
Extracts and analyzes keyword roots from research data
"""
import logging
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict, Counter
import re

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
                sv = safe_int(kw.get('Search Volume'))
                if sv:
                    search_volumes.append(sv)
                
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

    def group_by_roots(self, keyword_evaluations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group relevant keywords by root words (bigrams first, then unigrams).
        Each keyword appears in at most one root group. Roots are processed in order
        of frequency so higher-frequency roots claim keywords first.
        
        Process:
        1. Extract bigrams (2-word sliding window) and unigrams from relevant keywords
        2. Count how many keywords contain each root
        3. Process bigrams first (sorted by frequency desc) — claim keywords
        4. Then process unigrams (sorted by frequency desc) — claim remaining keywords
        5. Any leftover keywords go into an '_other' group
        
        Args:
            keyword_evaluations: Full list of keyword evaluation dicts
        
        Returns:
            List of root group dicts, each containing:
                - root: the root word/phrase
                - root_type: 'bigram' or 'unigram' or 'unclaimed'
                - frequency: number of keywords in this group
                - keywords: list of keyword evaluation dicts
        """
        relevant_categories = {'relevant', 'design_specific', 'outlier'}
        relevant_keywords = [
            kw for kw in keyword_evaluations
            if kw.get('category', '') in relevant_categories
        ]
        
        if not relevant_keywords:
            logger.info("No relevant keywords to group by roots")
            return []
        
        logger.info(f"Grouping {len(relevant_keywords)} relevant keywords by root words")
        
        # Count roots across all relevant keywords
        bigram_counts, unigram_counts = self._count_root_frequencies(relevant_keywords)
        
        # Sort roots by frequency descending
        sorted_bigrams = sorted(bigram_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_unigrams = sorted(unigram_counts.items(), key=lambda x: x[1], reverse=True)
        
        claimed_keywords = set()  # keyword text (lowered) that has been claimed
        root_groups = []
        
        # Phase 1: Bigram roots
        for bigram, freq in sorted_bigrams:
            if freq < 2:
                continue
            
            group_keywords = []
            for kw in relevant_keywords:
                kw_text = kw.get('keyword', '').strip().lower()
                if kw_text in claimed_keywords:
                    continue
                if bigram in kw_text:
                    group_keywords.append(kw)
                    claimed_keywords.add(kw_text)
            
            if group_keywords:
                root_groups.append({
                    'root': bigram,
                    'root_type': 'bigram',
                    'frequency': len(group_keywords),
                    'keywords': group_keywords
                })
        
        # Phase 2: Unigram roots
        for unigram, freq in sorted_unigrams:
            if freq < 2:
                continue
            
            group_keywords = []
            for kw in relevant_keywords:
                kw_text = kw.get('keyword', '').strip().lower()
                if kw_text in claimed_keywords:
                    continue
                words = kw_text.split()
                if unigram in words:
                    group_keywords.append(kw)
                    claimed_keywords.add(kw_text)
            
            if group_keywords:
                root_groups.append({
                    'root': unigram,
                    'root_type': 'unigram',
                    'frequency': len(group_keywords),
                    'keywords': group_keywords
                })
        
        # Phase 3: Unclaimed keywords
        unclaimed = []
        for kw in relevant_keywords:
            kw_text = kw.get('keyword', '').strip().lower()
            if kw_text not in claimed_keywords:
                unclaimed.append(kw)
        
        if unclaimed:
            root_groups.append({
                'root': '_other',
                'root_type': 'unclaimed',
                'frequency': len(unclaimed),
                'keywords': unclaimed
            })
        
        claimed_count = len(relevant_keywords) - len(unclaimed)
        logger.info(
            f"Root grouping complete: {len(root_groups)} groups, "
            f"{claimed_count}/{len(relevant_keywords)} keywords claimed"
        )
        for group in root_groups[:10]:
            logger.info(f"  Root '{group['root']}' ({group['root_type']}): {group['frequency']} keywords")
        
        return root_groups

    def _count_root_frequencies(
        self, keywords: List[Dict[str, Any]]
    ) -> Tuple[Counter, Counter]:
        """
        Count how many keywords contain each bigram / unigram root.
        
        Returns:
            (bigram_counts, unigram_counts)
        """
        bigram_counts = Counter()
        unigram_counts = Counter()
        
        for kw in keywords:
            phrase = kw.get('keyword', '').strip().lower()
            if not phrase:
                continue
            
            words = phrase.split()
            
            # Bigrams — consecutive word pairs (skip if both are stop words)
            seen_bigrams: Set[str] = set()
            for i in range(len(words) - 1):
                if words[i] in self.stop_words and words[i + 1] in self.stop_words:
                    continue
                bigram = f"{words[i]} {words[i + 1]}"
                if bigram not in seen_bigrams:
                    seen_bigrams.add(bigram)
                    bigram_counts[bigram] += 1
            
            # Unigrams — non-stop words, deduplicated per phrase
            seen_unigrams: Set[str] = set()
            for word in words:
                if word in self.stop_words:
                    continue
                if word not in seen_unigrams:
                    seen_unigrams.add(word)
                    unigram_counts[word] += 1
        
        return bigram_counts, unigram_counts
