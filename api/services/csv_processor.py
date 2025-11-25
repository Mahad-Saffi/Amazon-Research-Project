"""
CSV Processing Service - All operations in memory
"""
import csv
import io
from typing import List, Dict, Any, Set
from collections import Counter
import logging

logger = logging.getLogger(__name__)

# Stop words for root keyword extraction
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
    'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
    'between', 'among', 'against', 'without', 'within', 'is', 'are', 'was', 'were', 'be',
    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'must', 'shall'
}

class CSVProcessor:
    """Process CSV files in memory without writing intermediate files"""
    
    @staticmethod
    def parse_csv_content(content: bytes) -> List[Dict[str, Any]]:
        """Parse CSV bytes into list of dictionaries"""
        text = content.decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        # Strip whitespace from fieldnames
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = []
        for row in reader:
            # Create new dict with stripped keys
            clean_row = {k.strip(): v for k, v in row.items()}
            rows.append(clean_row)
        return rows
    
    @staticmethod
    def deduplicate_design(design_rows: List[Dict], revenue_rows: List[Dict]) -> List[Dict]:
        """Remove keywords from design that are present in revenue"""
        logger.info(f"Deduplicating design: {len(design_rows)} rows")
        
        # Extract revenue keywords
        revenue_keywords = set()
        for row in revenue_rows:
            kw = row.get('Keyword Phrase', '').strip()
            if kw:
                revenue_keywords.add(kw.lower())
        
        # Filter design rows
        deduped = []
        for row in design_rows:
            kw = row.get('Keyword Phrase', '').strip()
            if kw and kw.lower() not in revenue_keywords:
                deduped.append(row)
        
        logger.info(f"Deduplicated: {len(deduped)} rows remaining")
        return deduped
    
    @staticmethod
    def filter_columns(rows: List[Dict]) -> List[Dict]:
        """Keep only required columns"""
        required_columns = {"Keyword Phrase", "Search Volume", "Position (Rank)", "Title Density"}
        
        if not rows:
            return []
        
        # Determine columns to keep
        all_columns = list(rows[0].keys())
        columns_to_keep = []
        for col in all_columns:
            if col in required_columns or col.startswith("B0"):
                columns_to_keep.append(col)
        
        logger.info(f"Filtering columns: {len(all_columns)} -> {len(columns_to_keep)}")
        
        # Filter rows
        filtered = []
        for row in rows:
            filtered_row = {col: row.get(col, '') for col in columns_to_keep}
            filtered.append(filtered_row)
        
        return filtered
    
    @staticmethod
    def add_relevancy(rows: List[Dict]) -> List[Dict]:
        """Add relevancy column based on B0 columns with values < 11"""
        logger.info(f"Adding relevancy to {len(rows)} rows")
        
        rows_with_relevancy = []
        for row in rows:
            # Count B0 columns with values < 11
            relevancy = 0
            for col, value in row.items():
                if col.startswith('B0') and value and str(value).strip():
                    try:
                        val = float(value)
                        if val < 11:
                            relevancy += 1
                    except ValueError:
                        pass
            
            row['relevancy'] = relevancy
            if relevancy >= 2:  # Keep only relevancy >= 2
                rows_with_relevancy.append(row)
        
        # Sort by relevancy descending
        rows_with_relevancy.sort(key=lambda x: int(x.get('relevancy', 0)), reverse=True)
        
        logger.info(f"Filtered to {len(rows_with_relevancy)} rows with relevancy >= 2")
        return rows_with_relevancy
    
    @staticmethod
    def extract_root_keywords(design_rows: List[Dict], revenue_rows: List[Dict]) -> List[Dict]:
        """Extract and count root keywords from both CSVs"""
        logger.info("Extracting root keywords")
        
        all_tokens = []
        
        # Process both design and revenue rows
        for rows in [design_rows, revenue_rows]:
            for row in rows:
                keyword_phrase = row.get('Keyword Phrase', '').strip()
                if keyword_phrase:
                    # Tokenize by spaces
                    tokens = keyword_phrase.lower().split()
                    # Remove stop words
                    filtered_tokens = [token for token in tokens if token not in STOP_WORDS and token]
                    all_tokens.extend(filtered_tokens)
        
        # Count frequencies
        token_counts = Counter(all_tokens)
        
        # Sort by frequency descending
        sorted_tokens = sorted(token_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Convert to list of dicts
        root_keywords = [
            {'keyword': keyword, 'frequency': freq}
            for keyword, freq in sorted_tokens
        ]
        
        logger.info(f"Extracted {len(root_keywords)} unique root keywords")
        if root_keywords:
            logger.info(f"Top 5: {root_keywords[:5]}")
        
        return root_keywords
