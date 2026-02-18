#!/usr/bin/env python3

import requests
import random
import time
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup


class AmazonKeywordScraper:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]

    ACCEPT_LANGUAGES = [
        "en-US,en;q=0.9",
        "en-GB,en;q=0.9,en-US;q=0.8",
        "en-US,en;q=0.9,es;q=0.8",
    ]

    def __init__(self, max_retries=5):
        self.max_retries = max_retries
        self.session = self._create_session()

    def _create_session(self):
        """Create session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504, 522, 524],
            allowed_methods=["GET"],
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def _headers(self):
        """Generate stealth headers"""
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

    def _delay(self, min_sec=3, max_sec=6):
        """Random delay"""
        time.sleep(random.uniform(min_sec, max_sec))

    def _is_blocked(self, html):
        """Check if response indicates blocking"""
        html_lower = html.lower()
        blocked_indicators = [
            "captcha",
            "robot check",
            "sorry, we just need to make sure you're not a robot",
            "enter the characters you see below",
            "to discuss automated access to amazon data"
        ]
        return any(indicator in html_lower for indicator in blocked_indicators)

    def warm_up(self):
        """Visit Amazon homepage to establish cookies"""
        print("🔄 Warming up session...")
        try:
            response = self.session.get(
                "https://www.amazon.com/",
                headers=self._headers(),
                timeout=30
            )
            if response.status_code == 200:
                print("✅ Session warmed up successfully")
            else:
                print(f"⚠️  Warm-up returned status {response.status_code}")
        except Exception as e:
            print(f"⚠️  Warm-up failed: {e}")
        
        self._delay(2, 3)

    def build_search_url(self, keyword, page=1):
        """Build Amazon search URL"""
        return f"https://www.amazon.com/s?k={quote_plus(keyword)}&page={page}"

    def scrape_search_html(self, keyword, page=1):
        """Scrape search results with retry logic"""
        url = self.build_search_url(keyword, page)
        
        for attempt in range(1, self.max_retries + 1):
            print(f"🌐 Attempt {attempt}/{self.max_retries}: {url}")
            
            try:
                self._delay()
                
                response = self.session.get(
                    url,
                    headers=self._headers(),
                    timeout=45,
                    allow_redirects=True
                )

                if response.status_code != 200:
                    print(f"⚠️  HTTP {response.status_code}")
                    if attempt < self.max_retries:
                        wait_time = 2 ** attempt
                        print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"HTTP {response.status_code} after {self.max_retries} attempts")

                html = response.text
                
                if self._is_blocked(html):
                    print(f"🚫 Blocked by Amazon (attempt {attempt}/{self.max_retries})")
                    if attempt < self.max_retries:
                        wait_time = 2 ** (attempt + 1)
                        print(f"⏳ Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("Blocked by Amazon (captcha/503) after all retries")
                
                if len(html) < 10000:
                    print(f"⚠️  Response too short ({len(html)} bytes)")
                    if attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    else:
                        raise Exception(f"Response too short ({len(html)} bytes)")
                
                print(f"✅ Successfully fetched HTML ({len(html)} bytes)")
                return html

            except requests.exceptions.RequestException as e:
                print(f"⚠️  Request error: {e}")
                if attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception(f"Request failed after {self.max_retries} attempts: {e}")
        
        raise Exception("Failed to scrape after all retries")

    def extract_product_titles(self, html):
        """Extract non-sponsored product titles from HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        product_items = soup.find_all('div', {'data-component-type': 's-search-result'})
        
        titles = []
        for product_item in product_items:
            # Skip sponsored products (they have "AdHolder" in their class)
            class_list = product_item.get('class', [])
            if 'AdHolder' in class_list:
                continue
            
            # Find the h2 tag which contains the title
            h2_tag = product_item.find('h2')
            if h2_tag:
                # Get the span inside h2 which has the actual title text
                span_tag = h2_tag.find('span')
                if span_tag:
                    title = span_tag.get_text(strip=True)
                    titles.append(title)
        
        return titles

    def save_titles(self, keyword, titles):
        """Save titles to a unique txt file"""
        out_dir = Path("results")
        out_dir.mkdir(parents=True, exist_ok=True)

        safe_kw = re.sub(r"[^a-zA-Z0-9]+", "_", keyword.lower())
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        file_path = out_dir / f"{safe_kw}_titles_{ts}.txt"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(titles))

        return file_path

    def close(self):
        self.session.close()


def main():
    print("=" * 60)
    print("🔍 Amazon Product Title Scraper")
    print("=" * 60)
    
    # Ask for keyword
    keyword = input("\nEnter search keyword: ").strip()
    
    if not keyword:
        print("❌ Error: Keyword cannot be empty")
        return
    
    print(f"\n🎯 Searching for: '{keyword}'")
    print("-" * 60)
    
    scraper = AmazonKeywordScraper()

    try:
        # Warm up session
        scraper.warm_up()
        
        # Scrape search results
        html = scraper.scrape_search_html(keyword, page=1)
        
        # Extract titles
        print("\n📝 Extracting product titles...")
        titles = scraper.extract_product_titles(html)
        
        if not titles:
            print("⚠️  No non-sponsored products found")
            return
        
        # Save to file
        file_path = scraper.save_titles(keyword, titles)
        
        print("\n" + "=" * 60)
        print("✅ SUCCESS!")
        print("=" * 60)
        print(f"📊 Total non-sponsored products: {len(titles)}")
        print(f"💾 Saved to: {file_path}")
        print("\n📋 Product titles:")
        print("-" * 60)
        for i, title in enumerate(titles, 1):
            print(f"{i}. {title}")

    except Exception as e:
        print(f"\n❌ Error: {e}")

    finally:
        scraper.close()


if __name__ == "__main__":
    main()
