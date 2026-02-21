"""
Competitor relevant verification service
"""
import logging
import asyncio
from typing import List, Dict, Any

from agents import Runner
from research_agents.competitor_relevant_verification_agent import competitor_relevant_verification_agent

logger = logging.getLogger(__name__)

class VerificationService:
    """Handle competitor relevant keyword verification"""
    
    async def verify_competitor_keywords(
        self,
        competitor_keywords: List[Dict[str, Any]],
        product_title: str,
        product_bullets: List[str],
        max_concurrent_scrape: int = 5,
        max_concurrent_verify: int = 5,
        progress_callback=None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verify competitor_relevant keywords by scraping and analyzing IN PARALLEL.
        As soon as a keyword's titles are scraped, verification starts immediately
        without waiting for all scrapes to finish.
        
        Returns:
            Dict mapping keyword to verification result (verdict, match_percentage, reasoning)
        """
        if not competitor_keywords:
            return {}
        
        total = len(competitor_keywords)
        logger.info(f"Verifying {total} competitor_relevant keywords (parallel scrape+verify)")
        
        from Experimental.amazon_keyword_scraper import AmazonKeywordScraper
        
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
                        
                        result = await Runner.run(competitor_relevant_verification_agent, prompt)
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
                progress_pct = 98 + int((completed_count / total) * 1)  # 98-99%
                await progress_callback(
                    progress_pct,
                    f"Verifying keywords: {completed_count}/{total}"
                )
        
        # Launch all scrape+verify tasks — each keyword flows independently
        tasks = [scrape_and_verify(kw) for kw in competitor_keywords]
        await asyncio.gather(*tasks)
        
        logger.info(f"Verification complete: {len(verification_results)} results")
        return verification_results
    
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
