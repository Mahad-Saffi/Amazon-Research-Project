"""
Direct verification service - scrapes irrelevant keywords directly
Alternative to enhanced categorization + verification flow
"""
import logging
import asyncio
from typing import List, Dict, Any

from agents import Runner
from research_agents.competitor_relevant_verification_agent import competitor_relevant_verification_agent
from Experimental.amazon_keyword_scraper import AmazonKeywordScraper

logger = logging.getLogger(__name__)

class DirectVerificationService:
    """
    Direct verification: Scrape all irrelevant keywords and verify against our product.
    Scraping and AI verification run in parallel — as soon as a keyword's titles
    are scraped, verification starts immediately without waiting for other scrapes.
    
    Flow:
    1. Get all irrelevant keywords
    2. For EACH keyword in parallel:
       a. Scrape competitor titles
       b. Immediately send to AI for verification
    3. If match → 'relevant'
    4. If no match → 'irrelevant'
    """
    
    async def verify_irrelevant_keywords(
        self,
        keyword_evaluations: List[Dict[str, Any]],
        product_title: str,
        product_bullets: List[str],
        max_concurrent_scrape: int = 5,
        max_concurrent_verify: int = 5,
        progress_callback=None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Directly verify all irrelevant keywords by scraping and comparing IN PARALLEL.
        Each keyword flows independently: scrape → verify, without waiting for others.
        
        Args:
            keyword_evaluations: List of keyword categorizations
            product_title: Our product title
            product_bullets: Our product bullets
            max_concurrent_scrape: Max concurrent scraping threads
            max_concurrent_verify: Max concurrent AI verification calls
            progress_callback: Progress callback function
        
        Returns:
            Dict mapping keyword to verification result (verdict, match_percentage, reasoning)
        """
        # Extract irrelevant keywords
        irrelevant_keywords = [
            cat for cat in keyword_evaluations 
            if cat.get('category') == 'irrelevant'
        ]
        
        if not irrelevant_keywords:
            logger.info("No irrelevant keywords to verify")
            return {}
        
        total = len(irrelevant_keywords)
        logger.info(f"Direct verification: {total} irrelevant keywords (parallel scrape+verify)")
        
        verification_results = {}
        scrape_semaphore = asyncio.Semaphore(max_concurrent_scrape)
        verify_semaphore = asyncio.Semaphore(max_concurrent_verify)
        completed_count = 0
        
        def scrape_keyword(keyword: str):
            """Blocking scrape function - runs in thread executor"""
            try:
                scraper = AmazonKeywordScraper()
                scraper.warm_up()
                html = scraper.scrape_search_html(keyword, page=1)
                titles = scraper.extract_product_titles(html)
                scraper.close()
                return keyword, titles[:8]
            except Exception as e:
                logger.warning(f"Error scraping '{keyword}': {str(e)}")
                return keyword, []
        
        async def scrape_and_verify(keyword_data):
            """Scrape a keyword then immediately verify it — no waiting for others"""
            nonlocal completed_count
            keyword = keyword_data.get('keyword')
            
            # Phase 1: Scrape (limited concurrency via semaphore)
            async with scrape_semaphore:
                loop = asyncio.get_event_loop()
                kw, titles = await loop.run_in_executor(None, scrape_keyword, keyword)
            
            if titles:
                logger.info(f"Scraped {len(titles)} titles for '{kw}', sending to verification...")
            
            # Phase 2: Verify immediately (separate semaphore for AI calls)
            async with verify_semaphore:
                if not titles:
                    logger.warning(f"No titles for '{kw}' - marking as irrelevant")
                    verification_results[kw] = {
                        'verdict': 'irrelevant',
                        'match_percentage': 0,
                        'reasoning': 'No competitor titles found'
                    }
                else:
                    try:
                        logger.info(f"Verifying '{kw}' with {len(titles)} titles")
                        titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
                        
                        prompt = f"""
Keyword: {kw}

Our Product:
- Title: {product_title}
- Bullets: {chr(10).join(f'  • {b}' for b in product_bullets)}

Top {len(titles)} Competitor Titles:
{titles_text}

Analyze each title and determine if it matches our product. Return the results in the specified JSON format.
"""
                        
                        result = await Runner.run(
                            competitor_relevant_verification_agent, 
                            prompt
                        )
                        
                        output = getattr(result, "final_output", None)
                        structured = self._extract_structured_output(output)
                        
                        verification_results[kw] = {
                            'verdict': structured.get('final_verdict', 'irrelevant'),
                            'match_percentage': structured.get('match_percentage', 0),
                            'reasoning': structured.get('reasoning', '')
                        }
                        
                        logger.info(f"Verified '{kw}': {verification_results[kw]['verdict']}")
                    
                    except Exception as e:
                        logger.warning(f"Error verifying '{kw}': {str(e)}")
                        verification_results[kw] = {
                            'verdict': 'irrelevant',
                            'match_percentage': 0,
                            'reasoning': f'Verification error: {str(e)}'
                        }
            
            completed_count += 1
            if progress_callback:
                progress_pct = 95 + int((completed_count / total) * 4)  # 95-99%
                await progress_callback(
                    progress_pct,
                    f"Verifying keywords: {completed_count}/{total}"
                )
        
        # Launch all scrape+verify tasks — each keyword flows independently
        tasks = [scrape_and_verify(kw) for kw in irrelevant_keywords]
        await asyncio.gather(*tasks)
        
        logger.info(f"Verification complete: {len(verification_results)} results")
        return verification_results
    
    def apply_verification_results(
        self,
        keyword_evaluations: List[Dict[str, Any]],
        verification_results: Dict[str, Dict[str, Any]]
    ) -> int:
        """
        Apply verification results to keyword evaluations
        
        Args:
            keyword_evaluations: List of keyword categorizations to update
            verification_results: Dict mapping keyword to verification result
        
        Returns:
            Number of keywords changed to relevant
        """
        relevant_count = 0
        
        for cat in keyword_evaluations:
            keyword = cat.get('keyword')
            if keyword in verification_results:
                # Never downgrade design_specific keywords
                if cat.get('category') == 'design_specific':
                    logger.debug(f"Skipping verification override for design_specific keyword: '{keyword}'")
                    continue
                result = verification_results[keyword]
                if result['verdict'] == 'relevant':
                    cat['category'] = 'relevant'
                    cat['relevance_score'] = 8
                    cat['reasoning'] = f"Verified as relevant: {result['reasoning']}"
                    relevant_count += 1
                    logger.debug(f"Updated '{keyword}' to relevant")
                else:
                    # Keep as irrelevant
                    cat['category'] = 'irrelevant'
                    cat['relevance_score'] = 3
                    cat['reasoning'] = f"Verified as irrelevant: {result['reasoning']}"
        
        logger.info(f"Applied verification: {relevant_count} keywords → relevant")
        return relevant_count
    
    def _extract_structured_output(self, output: Any) -> Dict[str, Any]:
        """Extract structured data from agent output"""
        if output and hasattr(output, "model_dump"):
            return output.model_dump()
        elif isinstance(output, dict):
            return output
        elif isinstance(output, str):
            return self._extract_json_from_string(output)
        return {}
    
    def _extract_json_from_string(self, text: str) -> Dict[str, Any]:
        """Extract JSON from string"""
        import re
        import json
        if not text:
            return {}
        matches = re.findall(r"\{[\s\S]*\}", text)
        for snippet in reversed(matches):
            try:
                obj = json.loads(snippet)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
        return {}
