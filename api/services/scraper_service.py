"""
Amazon scraping service
"""
import logging
import time
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import json

from research_agents.helper_methods import scrape_amazon_listing

logger = logging.getLogger(__name__)

class ScraperService:
    """Handle Amazon product scraping"""
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [3, 6, 12]  # seconds between retries
    
    def scrape_product(
        self, 
        asin_or_url: str, 
        marketplace: str = "US", 
        use_mock: bool = False
    ) -> Dict[str, Any]:
        """
        Scrape Amazon product and extract title/bullets.
        Retries up to MAX_RETRIES times if Amazon returns empty product data
        (anti-bot/captcha pages that return HTTP 200 with no content).
        
        Returns:
            Dict with success, data, title, bullets
        """
        logger.info(f"Scraping: {asin_or_url}")
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            scraped_result = scrape_amazon_listing(asin_or_url, marketplace, use_mock=use_mock)
            
            if not scraped_result.get("success"):
                logger.warning(f"Scrape attempt {attempt}/{self.MAX_RETRIES} failed: {scraped_result.get('error')}")
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt - 1]
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                return scraped_result
            
            scraped_data = scraped_result.get("data", {})
            product_title, product_bullets = self._extract_title_and_bullets(scraped_data)
            
            if product_title:
                # Got valid data
                logger.info(f"Extracted title and {len(product_bullets)} bullets (attempt {attempt})")
                self._save_scraped_data(scraped_data, asin_or_url)
                return {
                    "success": True,
                    "data": scraped_data,
                    "title": product_title,
                    "bullets": product_bullets
                }
            
            # Scraper returned 200 but no title — likely a captcha/anti-bot page
            logger.warning(
                f"Scrape attempt {attempt}/{self.MAX_RETRIES}: got HTTP 200 but empty title "
                f"(Amazon may have served a captcha page)"
            )
            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_DELAYS[attempt - 1]
                logger.info(f"Retrying in {delay}s...")
                time.sleep(delay)
        
        # All retries exhausted — return whatever we got last
        logger.warning("All scrape retries exhausted — returning data with empty title")
        self._save_scraped_data(scraped_data, asin_or_url)
        return {
            "success": True,
            "data": scraped_data,
            "title": product_title,
            "bullets": product_bullets
        }
    
    def _extract_title_and_bullets(self, scraped_data: Dict) -> tuple:
        """Extract product title and bullets from scraped data"""
        # Extract title
        product_title = scraped_data.get("title", "")
        if not product_title:
            elements = scraped_data.get("elements", {})
            title_data = elements.get("productTitle", {})
            if title_data:
                title_text = title_data.get("text", "")
                product_title = title_text[0] if isinstance(title_text, list) else str(title_text)
        
        # Extract bullets
        product_bullets = []
        elements = scraped_data.get("elements", {})
        
        bullets_data = elements.get("feature-bullets", {})
        if bullets_data:
            product_bullets = bullets_data.get("bullets", [])
        
        if not product_bullets:
            facts_data = elements.get("productFactsDesktopExpander", {})
            if facts_data:
                product_bullets = facts_data.get("bullets", []) or facts_data.get("items", [])
        
        if not product_bullets:
            product_bullets = scraped_data.get("bullets", []) or scraped_data.get("features", [])
        
        if not product_bullets:
            product_bullets = scraped_data.get("feature_bullets", [])
        
        return product_title, product_bullets
    
    def _save_scraped_data(self, data: Dict, asin_or_url: str):
        """Save scraped data to JSON file"""
        try:
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            asin_clean = asin_or_url.replace('/', '_').replace(':', '_').replace('?', '_')[:50]
            file_path = results_dir / f"scraped_data_{asin_clean}_{timestamp}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved scraped data: {file_path}")
        except Exception as e:
            logger.warning(f"Could not save scraped data: {str(e)}")
