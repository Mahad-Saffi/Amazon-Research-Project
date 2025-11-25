#!/usr/bin/env python3
"""
Amazon HTML Scraper - Enhanced Anti-Blocking for Research Agent

This scraper can be called as a subprocess or used as a module.
Uses session management, retries, and stealth headers to avoid blocking.
Supports both sync (subprocess) and async (parallel) scraping modes.
"""

import sys
import json
import time
import random
import re
import asyncio
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "requests library not found. Install it with: pip install requests"
    }))
    sys.exit(1)

try:
    import aiohttp
except ImportError:
    aiohttp = None  # Optional for async functionality

try:
    from bs4 import BeautifulSoup
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "beautifulsoup4 library not found. Install it with: pip install beautifulsoup4"
    }))
    sys.exit(1)


class AmazonScraperV2:
    """Enhanced Amazon scraper with anti-blocking features."""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,es;q=0.8",
    ]
    
    def __init__(self, proxy: Optional[str] = None, max_retries: int = 3):
        self.proxy = proxy
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 522, 524],
            allowed_methods=["GET", "POST"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        if self.proxy:
            session.proxies = {
                'http': self.proxy,
                'https': self.proxy
            }
        
        return session
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": random.choice(self.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
    
    def _random_delay(self, min_seconds: float = 1.5, max_seconds: float = 3.5):
        time.sleep(random.uniform(min_seconds, max_seconds))
    
    def _parse_html(self, html: str, url: str) -> Dict[str, Any]:
        """Parse HTML and extract product information."""
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {
            "url": url,
            "status": 200,
            "title": "",
            "price": {},
            "elements": {},
            "reviews": {},
            "qa": {}
        }
        
        # Extract title
        title_elem = soup.find('span', {'id': 'productTitle'})
        if title_elem:
            data["title"] = title_elem.get_text(strip=True)
            data["elements"]["productTitle"] = {"text": data["title"]}
        
        # Extract price (improved parsing)
        price_whole = soup.find('span', {'class': 'a-price-whole'})
        price_fraction = soup.find('span', {'class': 'a-price-fraction'})
        
        if price_whole and price_fraction:
            try:
                # Get raw text
                whole_text = price_whole.get_text(strip=True)
                fraction_text = price_fraction.get_text(strip=True)
                
                # Remove commas, dollar signs, spaces
                whole_text = whole_text.replace(',', '').replace('$', '').replace(' ', '')
                fraction_text = fraction_text.replace(' ', '')
                
                # Remove trailing period from whole if present (Amazon format: "19.")
                if whole_text.endswith('.'):
                    whole_text = whole_text[:-1]
                
                # Build price: "19" + "." + "99" = "19.99"
                price_text = whole_text + "." + fraction_text
                
                # Convert to float
                price_value = float(price_text)
                
                # Sanity check: price should be between $0.01 and $99999
                if 0.01 <= price_value <= 99999:
                    data["price"]["amount"] = price_value
                    data["price"]["currency"] = "USD"
                else:
                    # Price out of range, try fallback
                    raise ValueError("Price out of expected range")
                    
            except Exception:
                # Fallback: try a-offscreen span (often has full price)
                pass
        
        # Fallback if primary method failed
        if not data["price"].get("amount"):
            try:
                offscreen = soup.find('span', {'class': 'a-offscreen'})
                if offscreen:
                    price_text = offscreen.get_text(strip=True).replace('$', '').replace(',', '').strip()
                    price_value = float(price_text)
                    if 0.01 <= price_value <= 99999:
                        data["price"]["amount"] = price_value
                        data["price"]["currency"] = "USD"
            except:
                pass
        
        # Extract feature bullets
        bullets = []
        bullets_div = soup.find('div', {'id': 'feature-bullets'})
        if bullets_div:
            for li in bullets_div.find_all('li'):
                text = li.get_text(strip=True)
                if text:
                    bullets.append(text)
            data["elements"]["feature-bullets"] = {
                "present": True,
                "bullets": bullets
            }
        
        # Extract product overview
        overview_div = soup.find('div', {'id': 'productOverview_feature_div'})
        if overview_div:
            kv_pairs = {}
            for row in overview_div.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = cells[0].get_text(strip=True)
                    value = cells[1].get_text(strip=True)
                    kv_pairs[key] = value
            data["elements"]["productOverview_feature_div"] = {
                "present": True,
                "kv": kv_pairs
            }
        
        # Extract images (improved to get full-size)
        image_urls = []
        
        # Method 1: Try to get high-res images from image block
        image_block = soup.find('div', {'id': 'altImages'})
        if image_block:
            for img in image_block.find_all('img'):
                # Try to get high-res version
                hi_res = img.get('data-old-hires') or img.get('data-a-hires')
                if hi_res:
                    image_urls.append(hi_res)
                else:
                    # Fallback to src, but try to upgrade from thumbnail
                    src = img.get('src', '')
                    if src and 'amazon.com/images' in src:
                        # Upgrade thumbnail to larger version: _SS40_ -> _SL1500_
                        src = src.replace('._SS40_', '._SL1500_').replace('_SS40_', '_SL1500_')
                        image_urls.append(src)
        
        # Method 2: Look for main product image
        if not image_urls:
            main_img = soup.find('img', {'id': 'landingImage'})
            if main_img:
                hi_res = main_img.get('data-old-hires') or main_img.get('src')
                if hi_res:
                    image_urls.append(hi_res)
        
        # Filter out transparent pixels and duplicates
        image_urls = [url for url in image_urls if 'transparent-pixel' not in url]
        image_urls = list(dict.fromkeys(image_urls))  # Remove duplicates
        
        data["elements"]["images"] = {
            "present": len(image_urls) > 0,
            "urls": image_urls[:10]  # Limit to 10 images
        }
        
        # Extract A+ content modules (improved)
        aplus_modules = []
        
        # Try multiple A+ content containers
        aplus_containers = [
            soup.find('div', {'id': 'aplus'}),
            soup.find('div', {'id': 'aplus_feature_div'}),
            soup.find('div', {'id': 'aplusBrandStory_feature_div'})
        ]
        
        for aplus_div in aplus_containers:
            if aplus_div:
                # Look for actual content modules (not just navigation)
                for module in aplus_div.find_all('div', {'class': re.compile('aplus-module|celwidget|a-section')}):
                    # Skip navigation modules
                    if 'nav' in module.get('class', []) or 'header' in str(module.get('class', [])).lower():
                        continue
                    
                    # Extract text content
                    module_text = module.get_text(strip=True)
                    
                    # Only add if it has substantial content (not just "Visit the Store")
                    if len(module_text) > 20 and 'visit the store' not in module_text.lower():
                        aplus_modules.append(module_text[:200])  # First 200 chars
                    
                    # Stop after finding some good modules
                    if len(aplus_modules) >= 5:
                        break
        
        data["elements"]["aplus"] = {
            "present": len(aplus_modules) > 0,
            "modules": aplus_modules[:5]  # Limit to 5 modules
        }
        
        # Extract reviews
        review_samples = []
        rating_text = ""
        reviews_div = soup.find('div', {'id': 'reviewsMedley'})
        if reviews_div:
            # Get rating summary
            rating_span = soup.find('span', {'data-hook': 'rating-out-of-text'})
            if rating_span:
                rating_text = rating_span.get_text(strip=True)
            
            # Get review samples
            for review in reviews_div.find_all('span', {'data-hook': 'review-body'}, limit=5):
                text = review.get_text(strip=True)
                if text:
                    review_samples.append(text[:200])  # First 200 chars
        
        data["reviews"] = {
            "review_highlights": [rating_text] if rating_text else [],
            "samples": review_samples
        }
        
        # Extract Q&A
        qa_pairs = []
        qa_section = soup.find('div', {'id': 'ask'})
        if qa_section:
            for qa_div in qa_section.find_all('div', {'class': 'a-fixed-left-grid'}, limit=5):
                question = qa_div.find('a', {'class': 'a-link-normal'})
                answer = qa_div.find('span', {'class': 'a-size-base'})
                if question and answer:
                    qa_pairs.append({
                        "question": question.get_text(strip=True),
                        "answer": answer.get_text(strip=True)[:200]
                    })
        
        data["qa"] = {"pairs": qa_pairs}
        
        return data
    
    def scrape(self, url: str) -> Dict[str, Any]:
        """Scrape Amazon product page and return structured data."""
        result = {
            "success": False,
            "data": {},
            "error": None,
            "scraping_method": "enhanced_v2"
        }
        
        self._random_delay(1.5, 3.0)
        
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self._get_headers()
                response = self.session.get(url, headers=headers, timeout=45, allow_redirects=True)
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Check for blocking
                    if "captcha" in html.lower() or "robot check" in html.lower():
                        result["error"] = "CAPTCHA detected"
                        if attempt < self.max_retries:
                            time.sleep(2 ** attempt)
                            continue
                    elif len(html) < 5000:
                        result["error"] = f"Response too short ({len(html)} bytes)"
                        if attempt < self.max_retries:
                            continue
                    else:
                        # Success - parse HTML
                        result["data"] = self._parse_html(html, url)
                        result["success"] = True
                        break
                else:
                    result["error"] = f"HTTP {response.status_code}"
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
            
            except Exception as e:
                result["error"] = str(e)
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
        
        return result
    
    def close(self):
        self.session.close()
    
    def _is_captcha_page(self, html: str) -> bool:
        """Check if the response is a CAPTCHA or robot check page."""
        if not html:
            return False
        html_lower = html.lower()
        return ("captcha" in html_lower or 
                "robot check" in html_lower or
                len(html) < 5000)
    
    # ========== ASYNC METHODS FOR PARALLEL SCRAPING ==========
    
    async def scrape_async(self, session: 'aiohttp.ClientSession', url: str) -> Dict[str, Any]:
        """
        Async version of scrape() for parallel scraping.
        
        Args:
            session: aiohttp ClientSession
            url: Amazon product URL
        
        Returns:
            Scraping result dictionary
        """
        result = {
            "success": False,
            "error": "Unknown error",
            "data": {},
            "url": url
        }
        
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self._get_headers()
                
                # Add random delay before request
                if attempt > 1:
                    await asyncio.sleep(random.uniform(1.5, 3.5))
                
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        html = await response.text()
                        
                        # Check for CAPTCHA
                        if self._is_captcha_page(html):
                            result["error"] = "CAPTCHA detected"
                            if attempt < self.max_retries:
                                await asyncio.sleep(2 ** attempt)
                            continue
                        
                        # Parse HTML
                        parsed_data = self._parse_html(html, url)
                        result["success"] = True
                        result["data"] = parsed_data
                        result["error"] = None
                        return result
                    else:
                        result["error"] = f"HTTP {response.status}"
                        if attempt < self.max_retries:
                            await asyncio.sleep(2 ** attempt)
            
            except asyncio.TimeoutError:
                result["error"] = "Request timed out"
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                result["error"] = str(e)
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
        
        return result
    
    @staticmethod
    async def scrape_multiple_async(
        urls: List[str],
        max_concurrent: int = 5,
        proxy: Optional[str] = None,
        progress_callback = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape multiple URLs in parallel using async/await.
        
        Args:
            urls: List of Amazon product URLs
            max_concurrent: Maximum concurrent requests (default 5)
            proxy: Optional proxy URL
            progress_callback: Optional callback function(completed, total)
        
        Returns:
            List of scraping results
        """
        if not aiohttp:
            raise ImportError("aiohttp is required for parallel scraping. Install: pip install aiohttp")
        
        results = []
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def bounded_scrape(session, scraper, url):
            nonlocal completed
            async with semaphore:
                result = await scraper.scrape_async(session, url)
                # Add small random delay between requests
                await asyncio.sleep(random.uniform(0.3, 0.8))
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(urls))
                return result
        
        connector = aiohttp.TCPConnector(limit=max_concurrent)
        timeout = aiohttp.ClientTimeout(total=30)
        
        proxy_url = proxy if proxy else None
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            scraper = AmazonScraperV2(proxy=proxy)
            tasks = [bounded_scrape(session, scraper, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append({
                    "success": False,
                    "error": str(result),
                    "data": {},
                    "url": urls[i]
                })
            else:
                final_results.append(result)
        
        return final_results


def scrape_amazon_mock(url: str) -> dict:
    """
    Mock scraper for testing without actual Amazon scraping.
    Returns realistic test data.
    """
    return {
        "success": True,
        "data": {
            "url": url,
            "status": 200,
            "title": "Freeze Dried Strawberries - 1 lb Bulk Bag | Organic, No Sugar Added",
            "price": {
                "amount": 29.99,
                "currency": "USD"
            },
            "elements": {
                "productTitle": {
                    "text": "Freeze Dried Strawberries - 1 lb Bulk Bag | Organic, No Sugar Added"
                },
                "feature-bullets": {
                    "present": True,
                    "bullets": [
                        "✅ PREMIUM QUALITY: 100% organic freeze dried strawberries with no added sugar",
                        "✅ VERSATILE USE: Perfect for snacking, baking, smoothies, and cereals",
                        "✅ TRAVEL READY: Lightweight and shelf-stable for camping and hiking",
                        "✅ NUTRIENT RICH: Retains vitamins and minerals from fresh strawberries",
                        "✅ BULK VALUE: 1 lb resealable bag for long-lasting freshness"
                    ]
                },
                "productOverview_feature_div": {
                    "present": True,
                    "kv": {
                        "Brand": "BREWER",
                        "Item Weight": "1 Pounds",
                        "Package Type": "Bag"
                    }
                },
                "images": {
                    "present": True,
                    "urls": [
                        "https://m.media-amazon.com/images/I/71abc123.jpg",
                        "https://m.media-amazon.com/images/I/71def456.jpg",
                        "https://m.media-amazon.com/images/I/71ghi789.jpg"
                    ]
                },
                "aplus": {
                    "present": True,
                    "modules": [
                        "Premium Freeze Drying Process",
                        "Organic Certification",
                        "Nutritional Benefits"
                    ]
                }
            },
            "reviews": {
                "review_highlights": [
                    "4.7 out of 5 stars",
                    "2,341 ratings"
                ],
                "samples": [
                    "Love these freeze dried strawberries! Perfect for my morning smoothies.",
                    "Great quality and taste. My kids enjoy them as a healthy snack.",
                    "Excellent for camping trips. Lightweight and delicious."
                ]
            },
            "qa": {
                "pairs": [
                    {
                        "question": "Are these organic?",
                        "answer": "Yes, these are 100% USDA certified organic strawberries."
                    },
                    {
                        "question": "How long do they stay fresh?",
                        "answer": "In the resealable bag, they stay fresh for up to 12 months."
                    }
                ]
            }
        },
        "scraping_method": "mock_for_testing"
    }


def main():
    """Main entry point for standalone scraper."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: scraper.py <url> [--mock] [--proxy http://proxy:port]"
        }))
        sys.exit(1)
    
    url = sys.argv[1]
    use_mock = "--mock" in sys.argv
    proxy = None
    
    # Parse proxy argument
    if "--proxy" in sys.argv:
        try:
            proxy_idx = sys.argv.index("--proxy")
            if proxy_idx + 1 < len(sys.argv):
                proxy = sys.argv[proxy_idx + 1]
        except:
            pass
    
    try:
        if use_mock:
            # Use mock data for testing
            result = scrape_amazon_mock(url)
        else:
            # Use real scraper
            scraper = AmazonScraperV2(proxy=proxy, max_retries=3)
            try:
                result = scraper.scrape(url)
            finally:
                scraper.close()
        
        print(json.dumps(result))
        
        # Exit with error code if scraping failed
        if not result.get("success"):
            sys.exit(1)
    
    except Exception as e:
        import traceback
        error_details = f"{str(e)}\n{traceback.format_exc()}"
        print(json.dumps({
            "success": False,
            "error": error_details,
            "data": {},
            "url": url
        }), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
