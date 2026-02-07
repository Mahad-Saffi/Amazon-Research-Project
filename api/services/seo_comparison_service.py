"""
SEO Comparison Service
Creates detailed side-by-side comparison of current vs optimized content
Implements Tasks 8, 9, 10, 12, 13
"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)

class SEOComparisonService:
    """Creates detailed SEO analysis and comparison"""
    
    def __init__(self):
        pass
    
    def create_comparison(
        self,
        current_title: str,
        current_bullets: List[str],
        optimized_title: str,
        optimized_bullets: List[str],
        current_analysis: Dict[str, Any],
        keyword_selection: Dict[str, Any],
        optimized_title_details: Dict[str, Any],
        optimized_bullets_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive side-by-side comparison
        
        Implements:
        - Task 8: Side-by-side comparison
        - Task 9: Keywords with search volumes in brackets
        - Task 10: "Search Volume" heading, remove density from bullets, total characters
        - Task 12: Highlight duplicate keywords
        - Task 13: Root volume only for relevant roots
        
        Returns:
            Dict with complete comparison data
        """
        # Title comparison
        title_comparison = self._create_title_comparison(
            current_title,
            optimized_title,
            current_analysis['title'],
            keyword_selection['title_keywords'],
            optimized_title_details
        )
        
        # Bullet points comparison
        bullets_comparison = self._create_bullets_comparison(
            current_bullets,
            optimized_bullets,
            current_analysis['bullets'],
            keyword_selection['bullet_keywords'],
            optimized_bullets_details
        )
        
        # Overall comparison
        overall_comparison = self._create_overall_comparison(
            title_comparison,
            bullets_comparison,
            current_analysis,
            keyword_selection
        )
        
        return {
            'title': title_comparison,
            'bullets': bullets_comparison,
            'overall': overall_comparison
        }
    
    def _create_title_comparison(
        self,
        current_title: str,
        optimized_title: str,
        current_analysis: Dict[str, Any],
        selected_keywords: Dict[str, Any],
        optimized_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create title comparison
        
        Task 9: Keywords with search volumes in brackets
        Task 10: "Search Volume" not "Volume", total characters
        Task 12: Highlight duplicates
        """
        # Current title analysis
        current_keywords_with_sv = [
            {
                'keyword': kw['keyword'],
                'search_volume': kw['search_volume'],
                'display': f"{kw['keyword']} ({kw['search_volume']:,})"
            }
            for kw in current_analysis['keywords_found']
        ]
        
        current_total_sv = sum(kw['search_volume'] for kw in current_analysis['keywords_found'])
        
        # Check for duplicates in current
        current_duplicates = self._find_duplicate_keywords(
            [kw['keyword'] for kw in current_analysis['keywords_found']]
        )
        
        # Optimized title analysis
        optimized_keywords_with_sv = [
            {
                'keyword': kw['keyword'],
                'search_volume': kw['search_volume'],
                'display': f"{kw['keyword']} ({kw['search_volume']:,})",
                'is_design_specific': kw.get('is_design_specific', False)
            }
            for kw in selected_keywords['all_keywords']
        ]
        
        optimized_total_sv = selected_keywords['total_search_volume']
        
        # Check for duplicates in optimized
        optimized_duplicates = self._find_duplicate_keywords(
            [kw['keyword'] for kw in selected_keywords['all_keywords']]
        )
        
        # Calculate keyword density
        current_words = len(current_title.split())
        current_keyword_words = sum(len(kw['keyword'].split()) for kw in current_analysis['keywords_found'])
        current_density = (current_keyword_words / current_words * 100) if current_words > 0 else 0
        
        optimized_words = len(optimized_title.split())
        optimized_keyword_words = sum(len(kw['keyword'].split()) for kw in selected_keywords['all_keywords'])
        optimized_density = (optimized_keyword_words / optimized_words * 100) if optimized_words > 0 else 0
        
        return {
            'current': {
                'text': current_title,
                'characters': len(current_title),  # Task 10: Total characters
                'keywords': current_keywords_with_sv,  # Task 9: With search volumes
                'keyword_count': len(current_keywords_with_sv),
                'total_search_volume': current_total_sv,  # Task 9: Total SV
                'keyword_density': round(current_density, 1),
                'duplicates': current_duplicates,  # Task 12: Duplicates
                'first_80_chars': current_title[:80]
            },
            'optimized': {
                'text': optimized_title,
                'characters': len(optimized_title),  # Task 10: Total characters
                'keywords': optimized_keywords_with_sv,  # Task 9: With search volumes
                'keyword_count': len(optimized_keywords_with_sv),
                'total_search_volume': optimized_total_sv,  # Task 9: Total SV
                'keyword_density': round(optimized_density, 1),
                'duplicates': optimized_duplicates,  # Task 12: Duplicates
                'first_80_chars': optimized_title[:80]
            }
        }
    
    def _create_bullets_comparison(
        self,
        current_bullets: List[str],
        optimized_bullets: List[str],
        current_analysis: Dict[str, Any],
        selected_keywords: Dict[str, Any],
        optimized_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create bullet points comparison
        
        Task 9: Keywords with search volumes
        Task 10: Remove density, total characters per bullet
        Task 12: Highlight duplicates
        """
        # Current bullets analysis
        current_bullets_data = []
        for i, bullet_data in enumerate(current_analysis['bullets']):
            keywords_with_sv = [
                {
                    'keyword': kw['keyword'],
                    'search_volume': kw['search_volume'],
                    'display': f"{kw['keyword']} ({kw['search_volume']:,})"
                }
                for kw in bullet_data['keywords_found']
            ]
            
            current_bullets_data.append({
                'bullet_number': i + 1,
                'text': bullet_data['text'],
                'characters': bullet_data['character_count'],  # Task 10: Total characters
                'keywords': keywords_with_sv,  # Task 9: With search volumes
                'keyword_count': len(keywords_with_sv),
                'search_volume': bullet_data['search_volume']  # Task 9: Per bullet SV
                # Task 10: NO density field for bullets
            })
        
        # Check for duplicates across all current bullets
        all_current_keywords = []
        for bullet_data in current_analysis['bullets']:
            all_current_keywords.extend([kw['keyword'] for kw in bullet_data['keywords_found']])
        current_duplicates = self._find_duplicate_keywords(all_current_keywords)
        
        # Optimized bullets analysis
        optimized_bullets_data = []
        for i, bullet in enumerate(optimized_bullets):
            # Get keywords for this bullet
            if i < len(optimized_details.get('keywords_per_bullet', [])):
                keyword_names = optimized_details['keywords_per_bullet'][i]
                
                # Find full keyword data
                keywords_with_sv = []
                for kw_name in keyword_names:
                    # Find in selected keywords
                    for kw in selected_keywords['all_keywords']:
                        if kw['keyword'].lower() == kw_name.lower():
                            keywords_with_sv.append({
                                'keyword': kw['keyword'],
                                'search_volume': kw['search_volume'],
                                'display': f"{kw['keyword']} ({kw['search_volume']:,})",
                                'is_design_specific': kw.get('is_design_specific', False)
                            })
                            break
            else:
                keywords_with_sv = []
            
            bullet_sv = sum(kw['search_volume'] for kw in keywords_with_sv)
            
            optimized_bullets_data.append({
                'bullet_number': i + 1,
                'text': bullet,
                'characters': len(bullet),  # Task 10: Total characters
                'keywords': keywords_with_sv,  # Task 9: With search volumes
                'keyword_count': len(keywords_with_sv),
                'search_volume': bullet_sv  # Task 9: Per bullet SV
                # Task 10: NO density field for bullets
            })
        
        # Check for duplicates across all optimized bullets
        all_optimized_keywords = []
        for bullet_data in optimized_bullets_data:
            all_optimized_keywords.extend([kw['keyword'] for kw in bullet_data['keywords']])
        optimized_duplicates = self._find_duplicate_keywords(all_optimized_keywords)
        
        return {
            'current': {
                'bullets': current_bullets_data,
                'bullet_count': len(current_bullets_data),
                'total_search_volume': current_analysis['total_search_volume'],  # Task 9: Total SV
                'total_characters': sum(b['characters'] for b in current_bullets_data),
                'duplicates': current_duplicates  # Task 12: Duplicates
            },
            'optimized': {
                'bullets': optimized_bullets_data,
                'bullet_count': len(optimized_bullets_data),
                'total_search_volume': selected_keywords['total_search_volume'],  # Task 9: Total SV
                'total_characters': sum(b['characters'] for b in optimized_bullets_data),
                'duplicates': optimized_duplicates  # Task 12: Duplicates
            }
        }
    
    def _create_overall_comparison(
        self,
        title_comparison: Dict[str, Any],
        bullets_comparison: Dict[str, Any],
        current_analysis: Dict[str, Any],
        keyword_selection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create overall comparison metrics
        
        Task 13: Root volume only for relevant roots
        """
        # Current totals
        current_total_sv = (
            title_comparison['current']['total_search_volume'] +
            bullets_comparison['current']['total_search_volume']
        )
        
        current_total_keywords = (
            title_comparison['current']['keyword_count'] +
            sum(b['keyword_count'] for b in bullets_comparison['current']['bullets'])
        )
        
        # Optimized totals
        optimized_total_sv = (
            title_comparison['optimized']['total_search_volume'] +
            bullets_comparison['optimized']['total_search_volume']
        )
        
        optimized_total_keywords = (
            title_comparison['optimized']['keyword_count'] +
            sum(b['keyword_count'] for b in bullets_comparison['optimized']['bullets'])
        )
        
        # Task 13: Root volume only for relevant/generic roots
        relevant_roots = self._calculate_relevant_root_volumes(keyword_selection)
        
        return {
            'current': {
                'total_search_volume': current_total_sv,
                'total_keywords': current_total_keywords,
                'total_characters': (
                    title_comparison['current']['characters'] +
                    bullets_comparison['current']['total_characters']
                )
            },
            'optimized': {
                'total_search_volume': optimized_total_sv,
                'total_keywords': optimized_total_keywords,
                'total_characters': (
                    title_comparison['optimized']['characters'] +
                    bullets_comparison['optimized']['total_characters']
                )
            },
            'improvement': {
                'search_volume': optimized_total_sv - current_total_sv,
                'search_volume_percent': (
                    ((optimized_total_sv - current_total_sv) / current_total_sv * 100)
                    if current_total_sv > 0 else 0
                ),
                'keywords': optimized_total_keywords - current_total_keywords
            },
            'relevant_root_volumes': relevant_roots  # Task 13
        }
    
    def _find_duplicate_keywords(self, keywords: List[str]) -> List[Dict[str, Any]]:
        """
        Find duplicate keywords (Task 12)
        
        Returns list of duplicates with count
        """
        from collections import Counter
        
        keyword_counts = Counter(kw.lower() for kw in keywords)
        
        duplicates = []
        for keyword, count in keyword_counts.items():
            if count > 1:
                duplicates.append({
                    'keyword': keyword,
                    'count': count
                })
        
        # Sort by count (most duplicated first)
        duplicates.sort(key=lambda x: x['count'], reverse=True)
        
        return duplicates
    
    def _calculate_relevant_root_volumes(
        self,
        keyword_selection: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Calculate root volumes only for relevant/generic roots (Task 13)
        
        Excludes irrelevant roots from broad search volume
        """
        root_volumes = {}
        
        # Collect from title keywords
        for kw in keyword_selection['title_keywords']['all_keywords']:
            root = kw['root']
            category = kw.get('category', '')
            
            # Task 13: Only include relevant or design_specific
            if category in ['relevant', 'design_specific']:
                if root not in root_volumes:
                    root_volumes[root] = {
                        'root': root,
                        'total_volume': 0,
                        'keyword_count': 0,
                        'is_design_specific': category == 'design_specific'
                    }
                root_volumes[root]['total_volume'] += kw['search_volume']
                root_volumes[root]['keyword_count'] += 1
        
        # Collect from bullet keywords
        for kw in keyword_selection['bullet_keywords']['all_keywords']:
            root = kw['root']
            category = kw.get('category', '')
            
            # Task 13: Only include relevant or design_specific
            if category in ['relevant', 'design_specific']:
                if root not in root_volumes:
                    root_volumes[root] = {
                        'root': root,
                        'total_volume': 0,
                        'keyword_count': 0,
                        'is_design_specific': category == 'design_specific'
                    }
                root_volumes[root]['total_volume'] += kw['search_volume']
                root_volumes[root]['keyword_count'] += 1
        
        # Convert to list and sort by volume
        root_list = list(root_volumes.values())
        root_list.sort(key=lambda x: x['total_volume'], reverse=True)
        
        return root_list
