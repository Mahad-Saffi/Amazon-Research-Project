"""
Direct verification service - scrapes irrelevant keywords directly
Alternative to enhanced categorization + verification flow
"""
import logging
import asyncio
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

from agents import Runner
from research_agents.competitor_relevant_verification_agent import competitor_relevant_verification_agent
from Experimental.amazon_keyword_scraper import AmazonKeywordScraper

logger = logging.getLogger(__name__)

class DirectVerificationService:
    """
    Direct verification: Scrape all irrelevant keywords and verify against our product
    
    Flow:
    1. Get all irrelevant keywords
    2. Scrape each irrelevant keyword directly (get competitor titles)
    3. Use AI to compare competitor titles with our product
    4. If match → 'relevant'
    5. If no match → 'irrelevant'
    
    This skips the Python function logic and goes straight to verification
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
        Directly verify all irrelevant keywords by scraping and comparing
        
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
        
        logger.info(f"Direct verification: {len(irrelevant_keywords)} irrelevant keywords")
        
        # Step 1: Scrape all irrelevant keywords in parallel
        scraped_titles = await self._scrape_all_keywords(
            irrelevant_keywords,
            max_concurrent_scrape,
            progress_callback
        )
        
        # Step 2: Verify with AI
        verification_results = await self._verify_with_ai(
            irrelevant_keywords,
            scraped_titles,
            product_title,
            product_bullets,
            max_concurrent_verify,
            progress_callback
        )
        
        return verification_results
    
    async def _scrape_all_keywords(
        self,
        keywords: List[Dict[str, Any]],
        max_workers: int,
        progress_callback=None
    ) -> Dict[str, List[str]]:
        """
        Scrape competitor titles for all irrelevant keywords in parallel
        Returns only first 6-8 organic (non-sponsored) titles per keyword
        
        Args:
            keywords: List of keyword dicts
            max_workers: Max concurrent scraping threads
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dict mapping keyword to list of organic competitor titles (6-8 titles)
        """
        total_keywords = len(keywords)
        logger.info(f"Scraping {total_keywords} irrelevant keywords (parallel)")
        
        scraped_titles = {}
        completed_count = 0
        
        def scrape_keyword(keyword: str):
            """Scrape titles for a single keyword"""
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
        
        # Use ThreadPoolExecutor for parallel scraping
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scrape_keyword, kw): kw 
                for kw in keywords_to_scrape
            }
            
            for future in as_completed(futures):
                keyword, titles = future.result()
                scraped_titles[keyword] = titles
                completed_count += 1
                
                if titles:
                    logger.info(f"Scraped {len(titles)} titles for '{keyword}' ({completed_count}/{total_keywords})")
                
                # Update progress
                if progress_callback:
                    progress_pct = 95 + int((completed_count / total_keywords) * 3)  # 95-98%
                    await progress_callback(
                        progress_pct, 
                        f"Scraping competitors: {completed_count}/{total_keywords} keywords"
                    )
        
        logger.info(f"Scraping complete: {len(scraped_titles)} keywords with titles")
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
        """
        Verify keywords using AI agent
        
        Args:
            keywords: List of keyword dicts
            scraped_titles: Dict mapping keyword to competitor titles
            product_title: Our product title
            product_bullets: Our product bullets
            max_concurrent: Max concurrent AI calls
            progress_callback: Progress callback
        
        Returns:
            Dict mapping keyword to verification result
        """
        logger.info(f"Verifying {len(keywords)} keywords with AI (concurrent)")
        
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
                    logger.info(f"Verifying '{keyword}' with {len(titles)} titles")
                    
                    # Format titles for agent
                    titles_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(titles)])
                    
                    # Create verification prompt
                    prompt = f"""
Keyword: {keyword}

Our Product:
- Title: {product_title}
- Bullets: {chr(10).join(f'  • {b}' for b in product_bullets)}

Top {len(titles)} Competitor Titles:
{titles_text}

Analyze each title and determine if it matches our product. Return the results in the specified JSON format.
"""
                    
                    # Call AI agent
                    result = await Runner.run(
                        competitor_relevant_verification_agent, 
                        prompt
                    )
                    
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
                    progress_percent = 95 + (completed / len(keywords)) * 4  # 95-99%
                    await progress_callback(progress_percent, f"Verifying irrelevant keywords ({completed}/{len(keywords)})...")
        
        # Run all verifications concurrently
        tasks = [verify_keyword(kw) for kw in keywords]
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
