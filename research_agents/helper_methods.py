"""
Helper Methods for Research Agent (Standalone Version)

Simplified version without dependencies on main application services.
"""

import json
import subprocess
import sys
import traceback
import time
from typing import Dict, Any, List, Tuple, Optional
from dotenv import load_dotenv, find_dotenv
import logging

load_dotenv(find_dotenv())
logger = logging.getLogger(__name__)


def construct_amazon_url(asin: str, marketplace: str = "US") -> str:
    """
    Construct Amazon URL from ASIN and marketplace code.
    
    Args:
        asin: Amazon ASIN (e.g., "B08KT2Z93D")
        marketplace: Marketplace code (US, UK, CA, DE, etc.)
    
    Returns:
        Full Amazon product URL
    """
    marketplace_domains = {
        "US": "amazon.com",
        "UK": "amazon.co.uk",
        "CA": "amazon.ca",
        "DE": "amazon.de",
        "FR": "amazon.fr",
        "IT": "amazon.it",
        "ES": "amazon.es",
        "JP": "amazon.co.jp",
        "IN": "amazon.in",
        "MX": "amazon.com.mx",
        "BR": "amazon.com.br",
        "AU": "amazon.com.au",
    }
    
    domain = marketplace_domains.get(marketplace.upper(), "amazon.com")
    return f"https://www.{domain}/dp/{asin}"


def scrape_amazon_listing(asin_or_url: str, marketplace: str = "US", use_mock: bool = False) -> Dict[str, Any]:
    """
    Scrape an Amazon product listing using the standalone scraper.
    
    Args:
        asin_or_url: Amazon ASIN or full product URL
        marketplace: Marketplace code (US, UK, CA, etc.)
        use_mock: If True, use mock data instead of real scraping
    
    Note: This uses the scraper from the services directory.
    """
    # Convert ASIN to full URL if needed
    if not asin_or_url.startswith("http"):
        url = construct_amazon_url(asin_or_url, marketplace)
    else:
        url = asin_or_url

    try:
        from pathlib import Path
        current_file = Path(__file__)
        scraper_script = current_file.parent.parent / "services" / "scraper.py"

        # Build command with optional --mock flag
        cmd = [sys.executable, str(scraper_script), url]
        if use_mock:
            cmd.append("--mock")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,  # 4 minutes
            cwd=str(current_file.parent.parent),
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr.strip() else result.stdout.strip()
            if not error_msg:
                error_msg = f"Process exited with code {result.returncode} (no output)"
            return {
                "success": False,
                "error": f"Scraper process failed: {error_msg}",
                "data": {},
                "url": url,
            }

        try:
            container = json.loads(result.stdout.strip())
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Failed to parse scraper output: {str(e)}",
                "data": {},
                "url": url,
            }

        if not isinstance(container, dict):
            return {"success": False, "error": "Invalid scraper response", "data": {}, "url": url}

        if not container.get("success"):
            return {
                "success": False,
                "error": container.get("error", "Unknown scraping error"),
                "data": container.get("data", {}),
                "url": url,
            }

        scraped_data = container.get("data", {}) or {}
        if not scraped_data:
            return {
                "success": False,
                "error": "No product data extracted",
                "data": {},
                "url": url,
            }

        return {"success": True, "data": scraped_data, "url": url}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Scraper process timed out (240 seconds)",
            "data": {},
            "url": url,
        }
    except Exception as e:
        error_details = f"Error in scraping: {str(e)}\nTraceback: {traceback.format_exc()}"
        return {"success": False, "error": error_details, "data": {}, "url": url}


def select_top_rows(rows: List[Dict[str, Any]], mode: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Select top rows from CSV based on mode (revenue or design)."""
    if not rows:
        return []

    def to_float(v: Any) -> float:
        try:
            if isinstance(v, str):
                vs = v.replace(",", "").strip()
                return float(vs)
            return float(v)
        except Exception:
            return 0.0

    def key_revenue(row: Dict[str, Any]) -> float:
        for k in ("Revenue", "Monthly Revenue", "Gross Revenue", "Estimated Revenue"):
            if k in row and row.get(k) not in (None, ""):
                val = to_float(row.get(k))
                if val:
                    return val
        for k in ("Units Sold", "Sales", "Monthly Sales", "Search Volume"):
            if k in row and row.get(k) not in (None, ""):
                val = to_float(row.get(k))
                if val:
                    return val
        return 0.0

    def key_design(row: Dict[str, Any]) -> float:
        for k in ("Cerebro IQ Score", "Relevancy", "Title Density"):
            if k in row and row.get(k) not in (None, ""):
                val = to_float(row.get(k))
                if val:
                    return val
        for k in ("Reviews", "Rating", "Search Volume"):
            if k in row and row.get(k) not in (None, ""):
                val = to_float(row.get(k))
                if val:
                    return val
        return 0.0

    key_fn = key_revenue if mode == "revenue" else key_design
    sorted_rows = sorted(rows, key=key_fn, reverse=True)
    return sorted_rows[:limit]


def collect_asins(rows: List[Dict[str, Any]], *, limit: int = 10) -> set:
    """Extract ASINs from CSV rows."""
    import re
    asin_regex = re.compile(r"B0[A-Z0-9]{8}")
    asins: set = set()
    for row in rows[:limit]:
        for key, val in row.items():
            if isinstance(key, str):
                for m in asin_regex.finditer(key.upper()):
                    asins.add(m.group(0))
            if isinstance(val, str):
                for m in asin_regex.finditer(val.upper()):
                    asins.add(m.group(0))
    return asins


def _parse_rating_info(scraped: Dict[str, Any]) -> Tuple[Optional[float], Optional[int]]:
    """Extract rating value and ratings count from scraped data."""
    import re
    rating_value: Optional[float] = None
    ratings_count: Optional[int] = None

    reviews = (scraped.get("reviews") or {}) if isinstance(scraped, dict) else {}
    highlights = reviews.get("review_highlights") or []
    if highlights:
        m = re.search(r"([0-9.]+)\s+out of 5", str(highlights[0]))
        if m:
            try:
                rating_value = float(m.group(1))
            except Exception:
                rating_value = None
    if len(highlights) > 1 and ratings_count is None:
        m = re.search(r"([0-9,]+)\s+ratings?", str(highlights[1]))
        if m:
            try:
                ratings_count = int(m.group(1).replace(",", ""))
            except Exception:
                ratings_count = None

    return rating_value, ratings_count


def scrape_competitors(asins: List[str], *, max_items: int = 10, marketplace: str = "US") -> List[Dict[str, Any]]:
    """Scrape basic info (price, rating) for competitor ASINs."""
    results: List[Dict[str, Any]] = []
    for asin in asins[:max_items]:
        res = scrape_amazon_listing(asin, marketplace)
        item: Dict[str, Any] = {"asin": asin, "success": bool(res.get("success"))}
        if res.get("success"):
            data = res.get("data", {}) or {}
            url = data.get("url") or construct_amazon_url(asin, marketplace)
            title = data.get("title") or ((data.get("elements") or {}).get("productTitle") or {}).get("text")
            if isinstance(title, list):
                title = title[0] if title else ""
            price = (data.get("price") or {}) if isinstance(data.get("price"), dict) else {}
            amount = price.get("amount")
            currency = price.get("currency")
            rating_value, ratings_count = _parse_rating_info(data)
            item.update({
                "url": url,
                "title": title,
                "price_amount": amount,
                "price_currency": currency,
                "rating_value": rating_value,
                "ratings_count": ratings_count,
            })
        else:
            item.update({
                "error": res.get("error"),
            })
        results.append(item)
    return results


async def scrape_competitors_parallel(
    asins: List[str], 
    *, 
    max_items: int = 10, 
    marketplace: str = "US",
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """
    Scrape competitor ASINs in parallel using async scraping.
    Much faster than sequential scraping.
    
    Args:
        asins: List of Amazon ASINs
        max_items: Maximum number of products to scrape
        marketplace: Marketplace code (US, UK, etc.)
        max_concurrent: Maximum concurrent requests (default 5)
    
    Returns:
        List of scraped product data
    """
    try:
        import asyncio
        from pathlib import Path
        import sys
        
        # Import scraper module
        current_file = Path(__file__)
        services_dir = current_file.parent.parent / "services"
        sys.path.insert(0, str(services_dir))
        
        from scraper import AmazonScraperV2
        
        # Build URLs
        asins = asins[:max_items]
        urls = [construct_amazon_url(asin, marketplace) for asin in asins]
        
        logger.info(f"[PARALLEL SCRAPING] Starting parallel scrape of {len(urls)} products...")
        start_time = time.time()
        
        # Scrape in parallel
        scraped_results = await AmazonScraperV2.scrape_multiple_async(
            urls=urls,
            max_concurrent=max_concurrent,
            progress_callback=lambda completed, total: logger.info(f"[PROGRESS] {completed}/{total} products scraped")
        )
        
        elapsed = time.time() - start_time
        logger.info(f"[PARALLEL SCRAPING] Completed in {elapsed:.1f}s (vs ~{len(urls)*7}s sequential)")
        
        # Transform results to match scrape_competitors format
        results: List[Dict[str, Any]] = []
        for i, scraped in enumerate(scraped_results):
            asin = asins[i]
            item: Dict[str, Any] = {"asin": asin, "success": scraped.get("success", False)}
            
            if scraped.get("success"):
                data = scraped.get("data", {}) or {}
                url = data.get("url") or construct_amazon_url(asin, marketplace)
                title = data.get("title") or ((data.get("elements") or {}).get("productTitle") or {}).get("text")
                if isinstance(title, list):
                    title = title[0] if title else ""
                price = (data.get("price") or {}) if isinstance(data.get("price"), dict) else {}
                amount = price.get("amount")
                currency = price.get("currency")
                rating_value, ratings_count = _parse_rating_info(data)
                item.update({
                    "url": url,
                    "title": title,
                    "price_amount": amount,
                    "price_currency": currency,
                    "rating_value": rating_value,
                    "ratings_count": ratings_count,
                })
            else:
                item.update({
                    "error": scraped.get("error", "Unknown error"),
                })
            
            results.append(item)
        
        return results
        
    except ImportError as e:
        logger.error(f"[PARALLEL SCRAPING] Failed to import required modules: {e}")
        logger.info("[PARALLEL SCRAPING] Falling back to sequential scraping...")
        return scrape_competitors(asins, max_items=max_items, marketplace=marketplace)
    except Exception as e:
        logger.error(f"[PARALLEL SCRAPING] Error: {e}")
        logger.info("[PARALLEL SCRAPING] Falling back to sequential scraping...")
        return scrape_competitors(asins, max_items=max_items, marketplace=marketplace)


def deduplicate_keywords_with_scores(
    keywords: List[str],
    relevancy_scores: Dict[str, int]
) -> Tuple[List[str], Dict[str, int], Dict[str, Any]]:
    """
    Deduplicate keywords while preserving the highest relevancy score.
    """
    logger.info(f"[DEDUP] Starting deduplication for {len(keywords)} keywords")
    
    unique_keyword_scores: Dict[str, int] = {}
    duplicate_tracking: Dict[str, List[int]] = {}
    
    for keyword in keywords:
        normalized_kw = keyword.strip().lower()
        score = relevancy_scores.get(keyword, 0)
        
        if normalized_kw not in duplicate_tracking:
            duplicate_tracking[normalized_kw] = []
        duplicate_tracking[normalized_kw].append(score)
        
        if normalized_kw in unique_keyword_scores:
            unique_keyword_scores[normalized_kw] = max(unique_keyword_scores[normalized_kw], score)
        else:
            unique_keyword_scores[normalized_kw] = score
    
    # Create deduplicated keyword list
    keyword_case_map: Dict[str, str] = {}
    for keyword in keywords:
        normalized = keyword.strip().lower()
        if normalized not in keyword_case_map:
            keyword_case_map[normalized] = keyword.strip()
    
    unique_keywords = [keyword_case_map[norm_kw] for norm_kw in unique_keyword_scores.keys()]
    
    unique_scores = {
        keyword_case_map[norm_kw]: score 
        for norm_kw, score in unique_keyword_scores.items()
    }
    
    duplicates_found = {
        keyword_case_map[norm_kw]: scores 
        for norm_kw, scores in duplicate_tracking.items() 
        if len(scores) > 1
    }
    
    dedup_stats = {
        "original_count": len(keywords),
        "unique_count": len(unique_keywords),
        "duplicates_removed": len(keywords) - len(unique_keywords),
        "duplicates_found_count": len(duplicates_found),
        "duplicates_sample": list(duplicates_found.items())[:5],
        "score_improvements": {
            kw: {"scores": scores, "max_kept": max(scores)}
            for kw, scores in list(duplicates_found.items())[:5]
        }
    }
    
    logger.info(f"[DEDUP] Keywords deduplicated: {dedup_stats['original_count']} -> {dedup_stats['unique_count']}")
    logger.info(f"[DEDUP] Duplicates removed: {dedup_stats['duplicates_removed']}")
    
    return unique_keywords, unique_scores, dedup_stats


def filter_keywords_by_original_content(
    keywords: List[str], 
    scraped_data: Dict[str, Any]
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Filter keywords to only include those that appear in the original scraped product title and bullets.
    
    This addresses Issue #1: Keywords/Bullet points that are not in title
    - Only shows keywords that exist in the ORIGINAL scraped listing
    - Prevents showing irrelevant keywords from CSV files
    - Uses fuzzy matching to handle plurals and variations
    
    Args:
        keywords: List of keyword phrases from CSV files
        scraped_data: Scraped Amazon product data with title and bullets
    
    Returns:
        Tuple of (filtered_keywords, filter_stats)
        - filtered_keywords: Keywords that appear in original content
        - filter_stats: Statistics about the filtering process
    """
    import re
    
    # Extract original title from scraped data
    title = ""
    elements = scraped_data.get("elements", {})
    if elements:
        title_data = elements.get("productTitle", {})
        if title_data:
            title_text = title_data.get("text", "")
            if isinstance(title_text, list):
                title = title_text[0] if title_text else ""
            else:
                title = str(title_text)
    
    # Extract original bullet points from scraped data
    bullets = []
    if elements:
        bullets_data = elements.get("feature-bullets", {})
        if bullets_data:
            bullets = bullets_data.get("bullets", [])
    
    # Combine title and bullets into searchable content
    # Convert to lowercase for case-insensitive matching
    content = (title + " " + " ".join(bullets)).lower()
    
    logger.info(f"[FILTER] Original content length: {len(content)} characters")
    logger.info(f"[FILTER] Title: {title[:100]}...")
    logger.info(f"[FILTER] Bullets count: {len(bullets)}")
    
    # Helper function to check if keyword exists in content
    def keyword_exists_in_content(keyword: str, content: str) -> bool:
        """
        Check if keyword phrase exists in content.
        Handles:
        - Exact matches
        - Plural variations (e.g., "strawberry" vs "strawberries")
        - Word boundaries to avoid partial matches
        """
        kw_lower = keyword.lower().strip()
        if not kw_lower:
            return False
        
        # Check exact match first
        if kw_lower in content:
            return True
        
        # Check plural variations
        # Handle "y" -> "ies" (e.g., strawberry -> strawberries)
        if kw_lower.endswith('y'):
            plural = kw_lower[:-1] + 'ies'
            if plural in content:
                return True
        
        # Handle regular plurals (add 's')
        if not kw_lower.endswith('s'):
            if (kw_lower + 's') in content:
                return True
        else:
            # Try singular form (remove 's')
            singular = kw_lower[:-1]
            if singular in content and len(singular) > 2:
                return True
        
        # Check if all significant words from keyword appear in content
        # This handles multi-word keywords with word order variations
        keyword_tokens = [t for t in re.split(r'[^a-z0-9]+', kw_lower) if len(t) > 2]
        if keyword_tokens:
            matches = sum(1 for token in keyword_tokens if token in content)
            # Require at least 80% of tokens to match for multi-word keywords
            if len(keyword_tokens) > 1 and matches >= len(keyword_tokens) * 0.8:
                return True
            # Require 100% match for single-word keywords
            elif len(keyword_tokens) == 1 and matches == 1:
                return True
        
        return False
    
    # Filter keywords: keep only those that exist in original content
    filtered_keywords = []
    keywords_found = []
    keywords_not_found = []
    
    for keyword in keywords:
        if keyword_exists_in_content(keyword, content):
            filtered_keywords.append(keyword)
            keywords_found.append(keyword)
        else:
            keywords_not_found.append(keyword)
    
    # Compile statistics for logging and debugging
    filter_stats = {
        "original_count": len(keywords),
        "filtered_count": len(filtered_keywords),
        "removed_count": len(keywords_not_found),
        "filter_percentage": round((len(filtered_keywords) / len(keywords) * 100) if keywords else 0, 1),
        "keywords_found_sample": keywords_found[:10],  # First 10 for debugging
        "keywords_removed_sample": keywords_not_found[:10]  # First 10 for debugging
    }
    
    logger.info(f"[FILTER] Keywords filtered: {filter_stats['original_count']} -> {filter_stats['filtered_count']} ({filter_stats['filter_percentage']}% kept)")
    logger.info(f"[FILTER] Sample found: {filter_stats['keywords_found_sample']}")
    logger.info(f"[FILTER] Sample removed: {filter_stats['keywords_removed_sample']}")
    
    return filtered_keywords, filter_stats
