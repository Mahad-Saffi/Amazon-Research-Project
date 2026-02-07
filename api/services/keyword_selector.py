"""
Keyword Selector Service
Selects best representative keywords for each root and prioritizes for title/bullets
"""
import logging
from typing import List, Dict, Any, Set, Tuple, Optional
import asyncio

logger = logging.getLogger(__name__)

class KeywordSelector:
    """Selects optimal keywords for SEO optimization"""
    
    def __init__(self):
        # Import here to avoid circular dependency
        from research_agents.design_specific_detector_agent import DesignSpecificDetectorAgent
        self.design_detector = DesignSpecificDetectorAgent()
    
    async def select_keywords_for_optimization(
        self,
        keyword_evaluations: List[Dict[str, Any]],
        root_analysis: Dict[str, Any],
        variant_analysis: List[Dict[str, Any]],
        current_title: str = None,
        current_bullets: List[str] = None,
        current_keywords: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Select best keywords for title and bullet points
        
        Args:
            keyword_evaluations: All keyword research data
            root_analysis: Root analysis from KeywordRootAnalyzer
            variant_analysis: Variant analysis from KeywordVariantDetector
            current_title: Current product title (for design-specific detection)
            current_bullets: Current bullet points (for design-specific detection)
            current_keywords: Currently used keywords (optional)
        
        Returns:
            Dict with selected keywords for title and bullets
        """
        # Get root representatives
        root_representatives = self._select_root_representatives(
            root_analysis['ranked_roots'],
            variant_analysis
        )
        
        # Separate design-specific and regular roots
        design_specific_reps = [
            r for r in root_representatives
            if r['is_design_specific']
        ]
        regular_reps = [
            r for r in root_representatives
            if not r['is_design_specific']
        ]
        
        # Check if current content has design-specific keywords
        include_design_specific = False
        design_detection_result = None
        
        if current_title and current_bullets and design_specific_reps:
            logger.info("Checking if current content has design-specific keywords...")
            design_detection_result = await self.design_detector.detect_design_specific_in_content(
                current_title,
                current_bullets,
                design_specific_reps
            )
            include_design_specific = design_detection_result.get('has_design_specific', False)
            logger.info(f"Include design-specific: {include_design_specific}")
        
        # Select keywords for title (4-6 keywords + 2-3 design-specific if applicable)
        title_keywords = self._select_title_keywords(
            regular_reps,
            design_specific_reps if include_design_specific else [],
            target_regular=4,
            target_design=2
        )
        
        # Select keywords for bullets (10-15 keywords, 2-3 per bullet)
        bullet_keywords = self._select_bullet_keywords(
            regular_reps,
            design_specific_reps if include_design_specific else [],
            title_keywords,
            target_total=12,
            bullets_count=5
        )
        
        return {
            'title_keywords': title_keywords,
            'bullet_keywords': bullet_keywords,
            'root_representatives': root_representatives,
            'design_specific_count': len(design_specific_reps),
            'regular_count': len(regular_reps),
            'include_design_specific': include_design_specific,
            'design_detection': design_detection_result
        }
    
    def _select_root_representatives(
        self,
        ranked_roots: List[Dict[str, Any]],
        variant_analysis: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Select best representative keyword for each root
        
        Algorithm:
        1. For each root, get all keywords containing that root
        2. Sort by search volume
        3. Check for variants and select best one
        4. Return representative keyword
        """
        representatives = []
        
        for root_data in ranked_roots:
            root = root_data['root']
            keywords = root_data['keywords']
            
            if not keywords:
                continue
            
            # Sort keywords by search volume
            sorted_keywords = sorted(
                keywords,
                key=lambda x: int(x.get('Search Volume', 0) or 0),
                reverse=True
            )
            
            # Find best variant from variant analysis
            best_keyword = self._find_best_variant_for_root(
                root,
                sorted_keywords,
                variant_analysis
            )
            
            if best_keyword:
                representatives.append({
                    'root': root,
                    'keyword': best_keyword.get('keyword') or best_keyword.get('Keyword Phrase'),
                    'search_volume': int(best_keyword.get('Search Volume', 0) or 0),
                    'category': best_keyword.get('category', ''),
                    'is_design_specific': root_data['is_design_specific'],
                    'root_total_volume': root_data['total_search_volume'],
                    'root_keyword_count': root_data['keyword_count']
                })
        
        return representatives
    
    def _find_best_variant_for_root(
        self,
        root: str,
        keywords: List[Dict[str, Any]],
        variant_analysis: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best variant for a root from variant analysis
        
        If multiple keywords for this root are variants, use the best variant
        Otherwise, use highest search volume keyword
        """
        if not keywords:
            return None
        
        # Get keyword phrases
        keyword_phrases = [
            kw.get('keyword') or kw.get('Keyword Phrase')
            for kw in keywords
        ]
        
        # Check if any of these keywords are in variant groups
        for variant_group in variant_analysis:
            group_keywords = [v['original_keyword'] for v in variant_group['variants']]
            
            # Check if any of our keywords are in this variant group
            matching = [kw for kw in keyword_phrases if kw in group_keywords]
            
            if matching:
                # Use the best variant from this group
                best_variant_keyword = variant_group['best_variant']['original_keyword']
                
                # Find the full keyword data
                for kw in keywords:
                    kw_phrase = kw.get('keyword') or kw.get('Keyword Phrase')
                    if kw_phrase == best_variant_keyword:
                        return kw
        
        # No variant group found, return highest volume
        return keywords[0]
    
    def _select_title_keywords(
        self,
        regular_reps: List[Dict[str, Any]],
        design_specific_reps: List[Dict[str, Any]],
        target_regular: int = 4,
        target_design: int = 2
    ) -> Dict[str, Any]:
        """
        Select keywords for title
        
        Priority:
        1. Main keyword root (highest volume relevant root)
        2. Design-specific roots (2-3 if available)
        3. Additional high-volume relevant roots (to reach 4-6 total)
        
        Returns:
            Dict with main_keyword, design_keywords, additional_keywords
        """
        # Main keyword: highest volume relevant root
        main_keyword = regular_reps[0] if regular_reps else None
        
        # Design-specific keywords: top 2-3
        design_keywords = design_specific_reps[:target_design]
        
        # Additional keywords: fill to target_regular total
        additional_keywords = []
        if main_keyword:
            # Skip the main keyword, take next ones
            remaining = regular_reps[1:target_regular]
            additional_keywords = remaining
        
        # Calculate total search volume
        all_selected = []
        if main_keyword:
            all_selected.append(main_keyword)
        all_selected.extend(design_keywords)
        all_selected.extend(additional_keywords)
        
        total_volume = sum(kw['search_volume'] for kw in all_selected)
        
        return {
            'main_keyword': main_keyword,
            'design_keywords': design_keywords,
            'additional_keywords': additional_keywords,
            'all_keywords': all_selected,
            'total_keywords': len(all_selected),
            'total_search_volume': total_volume
        }
    
    def _select_bullet_keywords(
        self,
        regular_reps: List[Dict[str, Any]],
        design_specific_reps: List[Dict[str, Any]],
        title_keywords: Dict[str, Any],
        target_total: int = 12,
        bullets_count: int = 5
    ) -> Dict[str, Any]:
        """
        Select keywords for bullet points
        
        Strategy:
        - Exclude keywords already in title
        - Distribute remaining keywords across bullets (2-3 per bullet)
        - Prioritize by search volume
        
        Returns:
            Dict with bullet assignments and keywords
        """
        # Get keywords already used in title
        title_kw_set = set(
            kw['keyword'] for kw in title_keywords['all_keywords']
        )
        
        # Get remaining keywords (not in title)
        remaining_regular = [
            kw for kw in regular_reps
            if kw['keyword'] not in title_kw_set
        ]
        
        remaining_design = [
            kw for kw in design_specific_reps
            if kw['keyword'] not in title_kw_set
        ]
        
        # Combine and sort by search volume
        all_remaining = remaining_regular + remaining_design
        all_remaining.sort(key=lambda x: x['search_volume'], reverse=True)
        
        # Select top keywords up to target
        selected_for_bullets = all_remaining[:target_total]
        
        # Distribute across bullets (2-3 per bullet)
        keywords_per_bullet = max(2, len(selected_for_bullets) // bullets_count)
        
        bullet_assignments = []
        for i in range(bullets_count):
            start_idx = i * keywords_per_bullet
            end_idx = start_idx + keywords_per_bullet
            
            # Last bullet gets remaining keywords
            if i == bullets_count - 1:
                bullet_kws = selected_for_bullets[start_idx:]
            else:
                bullet_kws = selected_for_bullets[start_idx:end_idx]
            
            if bullet_kws:
                bullet_assignments.append({
                    'bullet_number': i + 1,
                    'keywords': bullet_kws,
                    'keyword_count': len(bullet_kws),
                    'total_search_volume': sum(kw['search_volume'] for kw in bullet_kws)
                })
        
        total_volume = sum(kw['search_volume'] for kw in selected_for_bullets)
        
        return {
            'bullet_assignments': bullet_assignments,
            'all_keywords': selected_for_bullets,
            'total_keywords': len(selected_for_bullets),
            'total_search_volume': total_volume,
            'avg_keywords_per_bullet': len(selected_for_bullets) / bullets_count if bullets_count > 0 else 0
        }
    
    def find_better_alternatives(
        self,
        current_keyword: str,
        root_representatives: List[Dict[str, Any]],
        variant_analysis: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Find better alternative keywords for a current keyword
        
        Better = higher search volume within same root, not a variant
        
        Returns:
            List of alternative keywords with improvement metrics
        """
        alternatives = []
        
        # Find root for current keyword
        current_root = self._find_root_for_keyword(current_keyword, root_representatives)
        
        if not current_root:
            return alternatives
        
        # Get all keywords for this root
        root_keywords = [
            rep for rep in root_representatives
            if rep['root'] == current_root
        ]
        
        # Find current keyword's search volume
        current_volume = 0
        for rep in root_representatives:
            if rep['keyword'].lower() == current_keyword.lower():
                current_volume = rep['search_volume']
                break
        
        # Find alternatives with higher volume
        for rep in root_keywords:
            if rep['keyword'].lower() == current_keyword.lower():
                continue
            
            # Check if it's a variant (don't suggest variants as alternatives)
            is_variant = self._check_if_variant(
                current_keyword,
                rep['keyword'],
                variant_analysis
            )
            
            if is_variant:
                continue
            
            # Check if higher volume
            if rep['search_volume'] > current_volume:
                improvement = rep['search_volume'] - current_volume
                improvement_pct = (improvement / current_volume * 100) if current_volume > 0 else 0
                
                alternatives.append({
                    'alternative_keyword': rep['keyword'],
                    'current_keyword': current_keyword,
                    'current_volume': current_volume,
                    'alternative_volume': rep['search_volume'],
                    'improvement': improvement,
                    'improvement_percent': round(improvement_pct, 1),
                    'root': current_root
                })
        
        # Sort by improvement
        alternatives.sort(key=lambda x: x['improvement'], reverse=True)
        
        return alternatives
    
    def _find_root_for_keyword(
        self,
        keyword: str,
        root_representatives: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find which root a keyword belongs to"""
        keyword_lower = keyword.lower()
        
        for rep in root_representatives:
            if rep['keyword'].lower() == keyword_lower:
                return rep['root']
        
        return None
    
    def _check_if_variant(
        self,
        keyword1: str,
        keyword2: str,
        variant_analysis: List[Dict[str, Any]]
    ) -> bool:
        """Check if two keywords are variants of each other"""
        kw1_lower = keyword1.lower()
        kw2_lower = keyword2.lower()
        
        for variant_group in variant_analysis:
            group_keywords = [
                v['original_keyword'].lower()
                for v in variant_group['variants']
            ]
            
            if kw1_lower in group_keywords and kw2_lower in group_keywords:
                return True
        
        return False
