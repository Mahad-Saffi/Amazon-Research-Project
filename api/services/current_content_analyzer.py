"""
Current Content Analyzer Service
Analyzes existing product title and bullet points for keywords and metrics
"""
import logging
from typing import List, Dict, Any, Set, Tuple
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


class CurrentContentAnalyzer:
    """Analyzes current product title and bullet points"""
    
    def __init__(self):
        pass
    
    def analyze_content(
        self,
        title: str,
        bullets: List[str],
        keyword_evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze current title and bullet points
        
        Args:
            title: Current product title
            bullets: List of current bullet points
            keyword_evaluations: Keyword research data
        
        Returns:
            Dict with analysis results
        """
        # Analyze title
        title_analysis = self._analyze_title(title, keyword_evaluations)
        
        # Analyze bullets
        bullets_analysis = self._analyze_bullets(bullets, keyword_evaluations)
        
        # Find duplicates across title and bullets
        all_keywords_found = title_analysis['keywords_found'] + bullets_analysis['keywords_found']
        duplicates = self._find_duplicates(all_keywords_found)
        
        # Calculate overall metrics
        total_search_volume = (
            title_analysis['total_search_volume'] +
            bullets_analysis['total_search_volume']
        )
        
        unique_roots = set(title_analysis['roots_covered'] + bullets_analysis['roots_covered'])
        
        return {
            'title': title_analysis,
            'bullets': bullets_analysis,
            'duplicates': duplicates,
            'total_search_volume': total_search_volume,
            'unique_roots_covered': list(unique_roots),
            'total_roots_covered': len(unique_roots)
        }
    
    def _analyze_title(
        self,
        title: str,
        keyword_evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze title for keywords and metrics"""
        
        # Find keywords present in title
        keywords_found = self._find_keywords_in_text(title, keyword_evaluations)
        
        # Calculate search volume
        total_search_volume = sum(kw['search_volume'] for kw in keywords_found)
        
        # Extract roots covered
        roots_covered = self._extract_roots_from_keywords(keywords_found)
        
        # Calculate character count
        char_count = len(title)
        
        # Calculate keyword density (keywords / total words)
        words = title.split()
        keyword_word_count = sum(len(kw['keyword'].split()) for kw in keywords_found)
        keyword_density = keyword_word_count / len(words) if words else 0
        
        # Check first 80 characters
        first_80_chars = title[:80]
        keywords_in_first_80 = self._find_keywords_in_text(first_80_chars, keyword_evaluations)
        
        return {
            'text': title,
            'keywords_found': keywords_found,
            'keyword_count': len(keywords_found),
            'total_search_volume': total_search_volume,
            'roots_covered': roots_covered,
            'character_count': char_count,
            'keyword_density': round(keyword_density, 2),
            'first_80_chars': first_80_chars,
            'keywords_in_first_80': keywords_in_first_80,
            'main_root_in_first_80': len(keywords_in_first_80) > 0
        }
    
    def _analyze_bullets(
        self,
        bullets: List[str],
        keyword_evaluations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze bullet points for keywords and metrics"""
        
        bullet_analyses = []
        all_keywords_found = []
        total_search_volume = 0
        all_roots = []
        
        for i, bullet in enumerate(bullets, 1):
            # Find keywords in this bullet
            keywords_found = self._find_keywords_in_text(bullet, keyword_evaluations)
            
            # Calculate metrics
            bullet_sv = sum(kw['search_volume'] for kw in keywords_found)
            roots = self._extract_roots_from_keywords(keywords_found)
            char_count = len(bullet)
            
            bullet_analyses.append({
                'bullet_number': i,
                'text': bullet,
                'keywords_found': keywords_found,
                'keyword_count': len(keywords_found),
                'search_volume': bullet_sv,
                'roots_covered': roots,
                'character_count': char_count
            })
            
            all_keywords_found.extend(keywords_found)
            total_search_volume += bullet_sv
            all_roots.extend(roots)
        
        # Remove duplicate roots
        unique_roots = list(set(all_roots))
        
        return {
            'bullets': bullet_analyses,
            'bullet_count': len(bullets),
            'keywords_found': all_keywords_found,
            'total_keyword_count': len(all_keywords_found),
            'total_search_volume': total_search_volume,
            'roots_covered': unique_roots,
            'total_character_count': sum(b['character_count'] for b in bullet_analyses)
        }
    
    def _find_keywords_in_text(
        self,
        text: str,
        keyword_evaluations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find which keywords from research are present in the text
        
        Returns list of dicts with:
        - keyword: the keyword phrase
        - search_volume: search volume
        - category: keyword category
        - position: character position in text
        """
        text_lower = text.lower()
        keywords_found = []
        
        for kw_data in keyword_evaluations:
            keyword = kw_data.get('keyword', '') or kw_data.get('Keyword Phrase', '')
            if not keyword:
                continue
            
            keyword_lower = keyword.lower()
            
            # Check if keyword is in text (whole word match)
            if self._is_keyword_in_text(keyword_lower, text_lower):
                search_volume = safe_int(kw_data.get('Search Volume'))
                
                position = text_lower.find(keyword_lower)
                
                keywords_found.append({
                    'keyword': keyword,
                    'search_volume': search_volume,
                    'category': kw_data.get('category', ''),
                    'position': position
                })
        
        # Sort by position in text
        keywords_found.sort(key=lambda x: x['position'])
        
        return keywords_found
    
    def _is_keyword_in_text(self, keyword: str, text: str) -> bool:
        """
        Check if keyword is in text (whole word match)
        
        Uses word boundaries to avoid partial matches
        """
        # Escape special regex characters
        keyword_escaped = re.escape(keyword)
        
        # Use word boundaries
        pattern = r'\b' + keyword_escaped + r'\b'
        
        return bool(re.search(pattern, text, re.IGNORECASE))
    
    def _extract_roots_from_keywords(
        self,
        keywords_found: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extract roots from found keywords
        
        Simple approach: extract 2-3 word phrases
        """
        roots = set()
        
        for kw in keywords_found:
            keyword = kw['keyword']
            words = keyword.lower().split()
            
            # Add 2-word combinations
            for i in range(len(words) - 1):
                roots.add(f"{words[i]} {words[i+1]}")
            
            # Add 3-word combinations
            for i in range(len(words) - 2):
                roots.add(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        return list(roots)
    
    def _find_duplicates(
        self,
        keywords_found: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find duplicate keywords used multiple times
        
        Returns list of duplicates with their occurrences
        """
        from collections import Counter
        
        keyword_counts = Counter(kw['keyword'].lower() for kw in keywords_found)
        
        duplicates = []
        for keyword, count in keyword_counts.items():
            if count > 1:
                # Find all occurrences
                occurrences = [
                    kw for kw in keywords_found
                    if kw['keyword'].lower() == keyword
                ]
                
                duplicates.append({
                    'keyword': keyword,
                    'count': count,
                    'occurrences': occurrences
                })
        
        # Sort by count (most duplicated first)
        duplicates.sort(key=lambda x: x['count'], reverse=True)
        
        return duplicates
    
    def extract_keywords_from_text(self, text: str) -> List[str]:
        """
        Extract potential keywords from text (for content without research data)
        
        Simple extraction: 2-4 word phrases
        """
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        keywords = []
        
        # Extract 2-word phrases
        for i in range(len(words) - 1):
            keywords.append(f"{words[i]} {words[i+1]}")
        
        # Extract 3-word phrases
        for i in range(len(words) - 2):
            keywords.append(f"{words[i]} {words[i+1]} {words[i+2]}")
        
        # Extract 4-word phrases
        for i in range(len(words) - 3):
            keywords.append(f"{words[i]} {words[i+1]} {words[i+2]} {words[i+3]}")
        
        return list(set(keywords))
