"""
Utility module for extracting meaningful modifiers from irrelevant keywords
and matching them against competitor titles using word boundaries.
"""
import re
from typing import List, Set, Tuple


# Stop words that don't carry meaningful information
STOP_WORDS = {
    'for', 'on', 'at', 'in', 'to', 'the', 'a', 'an', 'and', 'or', 'but',
    'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'can', 'of', 'that', 'this', 'it',
    'which', 'who', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
    'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
    'not', 'only', 'same', 'so', 'than', 'too', 'very', 'just', 'also',
    'up', 'down', 'out', 'off', 'over', 'under', 'about', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'between', 'among'
}


def extract_modifiers(
    irrelevant_keyword: str,
    relevant_keywords: List[str]
) -> List[str]:
    """
    Extract meaningful modifiers from an irrelevant keyword by:
    1. Splitting into words
    2. Removing stop words
    3. Removing words that appear in relevant keywords (dynamically extracted)
    
    Args:
        irrelevant_keyword: The irrelevant keyword to analyze
        relevant_keywords: List of top 3 relevant keywords
    
    Returns:
        List of meaningful modifiers
    """
    # Convert to lowercase and split
    words = irrelevant_keyword.lower().split()
    
    # Create a set of words from relevant keywords for quick lookup
    # This dynamically extracts all words from the top 3 relevant keywords
    relevant_words = set()
    for kw in relevant_keywords:
        kw_words = kw.lower().split()
        for word in kw_words:
            clean_word = re.sub(r'[^\w\s-]', '', word)
            if clean_word:
                relevant_words.add(clean_word)
    
    # Extract meaningful modifiers
    modifiers = []
    for word in words:
        # Remove punctuation
        clean_word = re.sub(r'[^\w\s-]', '', word)
        
        # Skip if empty, stop word, or in relevant keywords
        if clean_word and clean_word not in STOP_WORDS and clean_word not in relevant_words:
            modifiers.append(clean_word)
    
    return modifiers


def find_modifier_in_titles(
    modifier: str,
    titles: List[str]
) -> Tuple[bool, List[str]]:
    """
    Search for a modifier in titles using word boundaries.
    Ensures "table" doesn't match "portable".
    
    Args:
        modifier: The modifier to search for
        titles: List of titles to search in
    
    Returns:
        Tuple of (found: bool, matching_titles: List[str])
    """
    # Create word boundary regex pattern
    pattern = r'\b' + re.escape(modifier.lower()) + r'\b'
    
    matching_titles = []
    for title in titles:
        if re.search(pattern, title.lower()):
            matching_titles.append(title)
    
    found = len(matching_titles) > 0
    return found, matching_titles


def extract_modifiers_from_keyword(keyword: str) -> List[str]:
    """
    Extract modifiers from a single keyword by removing stop words.
    Used for Phase 4 when scraping the irrelevant keyword itself.
    
    Args:
        keyword: The keyword to extract modifiers from
    
    Returns:
        List of meaningful words/modifiers
    """
    words = keyword.lower().split()
    modifiers = []
    
    for word in words:
        clean_word = re.sub(r'[^\w\s-]', '', word)
        if clean_word and clean_word not in STOP_WORDS:
            modifiers.append(clean_word)
    
    return modifiers


def get_common_words(keywords: List[str]) -> Set[str]:
    """
    Get words that appear in multiple keywords (common terms to ignore).
    
    Args:
        keywords: List of keywords
    
    Returns:
        Set of common words
    """
    if not keywords:
        return set()
    
    # Split all keywords into words
    all_words = []
    for kw in keywords:
        words = kw.lower().split()
        all_words.extend([re.sub(r'[^\w\s-]', '', w) for w in words])
    
    # Find words that appear in multiple keywords
    word_counts = {}
    for word in all_words:
        if word and word not in STOP_WORDS:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Return words appearing in 2+ keywords
    return {word for word, count in word_counts.items() if count >= 2}
