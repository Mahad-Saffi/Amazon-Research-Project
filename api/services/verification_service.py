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
        max_concurrent: int = 5,
        progress_callback=None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Verify competitor_relevant keywords by scraping and analyzing
        
        Returns:
            Dict mapping keyword to verification result (verdict, match_percentage, reasoning)
        """
        if not competitor_keywords:
            return {}
        
        logger.info(f"Verifying {len(competitor_keywords)} competitor_relevant keywords")
        
        # Step 1: Scrape titles in parallel
        scraped_titles = await self._scrape_titles_parallel(competitor_keywords)
        
        # Step 2: Verify with AI
        verification_results = await self._verify_with_ai(
            competitor_keywords,
            scraped_titles,
            product_title,
            product_bullets,
            max_concurrent,
            progress_callback
        )
        
        return verification_results
    
    async def _scrape_titles_parallel(
        self, 
        keywords: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """
        Scrape competitor titles for keywords in parallel
        Returns only first 6-8 organic (non-sponsored) titles per keyword
        """
        from Experimental.amazon_keyword_scraper import AmazonKeywordScraper
        
        scraped_titles = {}
        
        def scrape_keyword(keyword: str):
            try:
                scraper = AmazonKeywordScraper()
                scraper.warm_up()
                html = scraper.scrape_search_html(keyword, page=1)
                titles = scraper.extract_product_titles(html)
                scraper.close()
                # Return only first 6-8 organic titles
                return keyword, titles[:8]
            except Exception as e:
                logger.warning(f"Error scraping '{keyword}': {str(e)}")
                return keyword, []
        
        keywords_to_scrape = [kw.get('keyword') for kw in keywords]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(scrape_keyword, kw): kw for kw in keywords_to_scrape}
            
            for future in as_completed(futures):
                keyword, titles = future.result()
                scraped_titles[keyword] = titles
                if titles:
                    logger.info(f"Scraped {len(titles)} titles for '{keyword}'")
        
        logger.info(f"Scraping complete: {len(scraped_titles)} keywords")
        return scraped_titles
    
    async def _verify_with_ai(
        self,
        keywords: List[Dict[str, Any]],
        scraped_titles: Dict[str, List[str]],
        product_title: str,
        product_bullets: List[str],
        max_concurrent: int,
        progress_callback
    ) -> Dict[str, Dict[str, Any]]:
        """Verify keywords using AI agent"""
        verification_results = {}
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def verify_keyword(keyword_data):
            nonlocal completed
            async with semaphore:
                keyword = keyword_data.get('keyword')
                titles = scraped_titles.get(keyword, [])
                
                if not titles:
                    logger.warning(f"No titles for '{keyword}' - marking as irrelevant")
                    verification_results[keyword] = {
                        'verdict': 'irrelevant',
                        'match_percentage': 0,
                        'reasoning': 'No competitor titles found'
                    }
                    completed += 1
                    return
                
                try:
                    titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
                    
                    prompt = f"""
Keyword: {keyword}

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
                    
                    verification_results[keyword] = {
                        'verdict': structured.get('final_verdict', 'irrelevant'),
                        'match_percentage': structured.get('match_percentage', 0),
                        'reasoning': structured.get('reasoning', '')
                    }
                    
                    logger.info(f"Verified '{keyword}': {verification_results[keyword]['verdict']}")
                
                except Exception as e:
                    logger.warning(f"Error verifying '{keyword}': {str(e)}")
                    verification_results[keyword] = {
                        'verdict': 'irrelevant',
                        'match_percentage': 0,
                        'reasoning': f'Verification error: {str(e)}'
                    }
                
                completed += 1
                if progress_callback:
                    progress = 98 + (completed / len(keywords)) * 1
                    await progress_callback(progress, f"Verifying ({completed}/{len(keywords)})...")
        
        tasks = [verify_keyword(kw) for kw in keywords]
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
