"""
ASIN Validator Service
Validates Amazon ASIN codes and URLs before processing
"""
import re
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class ASINValidator:
    """Validates ASIN codes and Amazon URLs"""
    
    # ASIN format: 10 characters, alphanumeric (usually starts with B)
    ASIN_PATTERN = re.compile(r'^[A-Z0-9]{10}$')
    
    # Amazon URL patterns
    AMAZON_DOMAINS = [
        'amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', 
        'amazon.it', 'amazon.es', 'amazon.ca', 'amazon.co.jp',
        'amazon.in', 'amazon.com.mx', 'amazon.com.br', 'amazon.com.au'
    ]
    
    def __init__(self):
        pass
    
    def validate(self, asin_or_url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate ASIN or URL
        
        Args:
            asin_or_url: ASIN code or Amazon URL
        
        Returns:
            Tuple of (is_valid, asin, error_message)
            - is_valid: True if valid, False otherwise
            - asin: Extracted ASIN code if valid, None otherwise
            - error_message: Error description if invalid, None otherwise
        """
        if not asin_or_url or not isinstance(asin_or_url, str):
            return False, None, "ASIN or URL is required"
        
        asin_or_url = asin_or_url.strip()
        
        # Check if it's a URL
        if asin_or_url.startswith('http://') or asin_or_url.startswith('https://'):
            return self._validate_url(asin_or_url)
        
        # Check if it's just an ASIN
        return self._validate_asin(asin_or_url)
    
    def _validate_asin(self, asin: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate ASIN code
        
        ASIN format: 10 alphanumeric characters (e.g., B0FZCXT239)
        """
        asin = asin.strip().upper()
        
        if not self.ASIN_PATTERN.match(asin):
            return False, None, f"Invalid ASIN format. ASIN must be 10 alphanumeric characters (e.g., B0FZCXT239). Got: {asin}"
        
        logger.info(f"Valid ASIN: {asin}")
        return True, asin, None
    
    def _validate_url(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate Amazon URL and extract ASIN
        
        Valid formats:
        - https://www.amazon.com/dp/B0FZCXT239
        - https://www.amazon.com/product-name/dp/B0FZCXT239
        - https://amazon.com/dp/B0FZCXT239
        - http://www.amazon.com/dp/B0FZCXT239
        
        Invalid formats:
        - https://www.amazon.comdp/B0FZCXT239 (missing /)
        - https://www.amazon.com/B0FZCXT239 (missing /dp/)
        """
        url = url.strip()
        
        # Check if URL contains a valid Amazon domain
        domain_found = None
        for domain in self.AMAZON_DOMAINS:
            if domain in url:
                domain_found = domain
                break
        
        if not domain_found:
            return False, None, f"Invalid Amazon URL. Must contain a valid Amazon domain (e.g., amazon.com). Got: {url}"
        
        # Check for /dp/ pattern
        if '/dp/' not in url:
            return False, None, f"Invalid Amazon URL format. URL must contain '/dp/' followed by ASIN. Got: {url}"
        
        # Extract ASIN from URL
        # Pattern: /dp/ASIN or /dp/ASIN/ or /dp/ASIN?params
        try:
            # Split by /dp/ and get the part after it
            parts = url.split('/dp/')
            if len(parts) < 2:
                return False, None, f"Invalid Amazon URL format. Could not find ASIN after '/dp/'. Got: {url}"
            
            # Get the ASIN part (after /dp/)
            asin_part = parts[1]
            
            # Remove query parameters and trailing slashes
            asin_part = asin_part.split('?')[0]  # Remove query params
            asin_part = asin_part.split('/')[0]  # Remove anything after ASIN
            asin_part = asin_part.strip('/')
            
            # Validate the extracted ASIN
            is_valid, asin, error = self._validate_asin(asin_part)
            
            if not is_valid:
                return False, None, f"Invalid ASIN in URL. {error}"
            
            logger.info(f"Valid Amazon URL. Extracted ASIN: {asin}")
            return True, asin, None
            
        except Exception as e:
            return False, None, f"Error parsing Amazon URL: {str(e)}. Got: {url}"
    
    def normalize_to_url(self, asin: str, marketplace: str = "US") -> str:
        """
        Convert ASIN to standard Amazon URL
        
        Args:
            asin: ASIN code
            marketplace: Marketplace code (US, UK, DE, etc.)
        
        Returns:
            Standard Amazon URL
        """
        marketplace_domains = {
            'US': 'amazon.com',
            'UK': 'amazon.co.uk',
            'DE': 'amazon.de',
            'FR': 'amazon.fr',
            'IT': 'amazon.it',
            'ES': 'amazon.es',
            'CA': 'amazon.ca',
            'JP': 'amazon.co.jp',
            'IN': 'amazon.in',
            'MX': 'amazon.com.mx',
            'BR': 'amazon.com.br',
            'AU': 'amazon.com.au'
        }
        
        domain = marketplace_domains.get(marketplace.upper(), 'amazon.com')
        return f"https://www.{domain}/dp/{asin}"
