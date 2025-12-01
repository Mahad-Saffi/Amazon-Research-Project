"""
Helper Methods for Research Agent

Contains utility functions for Amazon scraping.
"""

import json
import subprocess
import sys
import traceback
from typing import Dict, Any
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
    
    Returns:
        Dictionary with success flag, data, and error message
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
