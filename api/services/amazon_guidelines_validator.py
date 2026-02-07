"""
Amazon Guidelines Validator
Validates titles and bullet points against Amazon's requirements
"""
import logging
import re
from typing import List, Dict, Any, Tuple

logger = logging.getLogger(__name__)

class AmazonGuidelinesValidator:
    """Validates content against Amazon title and bullet point guidelines"""
    
    def __init__(self):
        # Prohibited special characters for titles
        self.title_prohibited_chars = set('!$?_{}^¬¦')
        
        # Limited-use characters (only for specific purposes)
        self.title_limited_chars = set('~#<>*')
        
        # Prohibited special characters for bullets
        self.bullet_prohibited_chars = set('™®€…†‡o¢£¥©±~â')
        
        # Prohibited emojis
        self.bullet_prohibited_emojis = set('☺☹✅❌')
        
        # Prohibited placeholder text
        self.bullet_prohibited_placeholders = [
            'not applicable', 'na', 'n/a', 'not eligible', 'tbd', 'copy pending'
        ]
        
        # Prohibited claims
        self.bullet_prohibited_claims = [
            'eco-friendly', 'environmentally friendly', 'anti-microbial',
            'anti-bacterial', 'bamboo', 'soy'
        ]
        
        # Prohibited guarantee language
        self.bullet_prohibited_guarantees = [
            'full refund', 'unconditional guarantee', 'satisfaction guarantee',
            'money back guarantee'
        ]
        
        # Prepositions, articles, conjunctions (exempt from word repetition rule)
        self.exempt_words = {
            'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
            'and', 'or', 'but', 'the', 'a', 'an'
        }
    
    def validate_title(self, title: str) -> Dict[str, Any]:
        """
        Validate title against Amazon guidelines
        
        Returns:
            Dict with validation results
        """
        issues = []
        warnings = []
        
        # Check character limit (200 max)
        char_count = len(title)
        if char_count > 200:
            issues.append(f"Title exceeds 200 characters ({char_count} chars)")
        elif char_count > 80:
            warnings.append(f"Title exceeds 80 characters ({char_count} chars) - may be truncated on mobile")
        
        # Check for prohibited characters
        prohibited_found = [c for c in title if c in self.title_prohibited_chars]
        if prohibited_found:
            issues.append(f"Contains prohibited characters: {', '.join(set(prohibited_found))}")
        
        # Check for limited-use characters (should only be for measurements/identifiers)
        limited_found = [c for c in title if c in self.title_limited_chars]
        if limited_found:
            warnings.append(f"Contains limited-use characters: {', '.join(set(limited_found))} - ensure used only for measurements/identifiers")
        
        # Check word repetition (max 2x, except exempt words)
        word_repetition_issues = self._check_word_repetition(title)
        if word_repetition_issues:
            issues.extend(word_repetition_issues)
        
        # Check for promotional phrases
        promotional_phrases = ['free shipping', '100% guaranteed', 'best seller', 'hot item']
        for phrase in promotional_phrases:
            if phrase.lower() in title.lower():
                issues.append(f"Contains promotional phrase: '{phrase}'")
        
        # Check for ALL CAPS
        if title.isupper() and len(title) > 10:
            issues.append("Title is in ALL CAPS")
        
        # Check for all lowercase
        if title.islower() and len(title) > 10:
            warnings.append("Title is in all lowercase - should use title case")
        
        # Check capitalization
        cap_issues = self._check_capitalization(title)
        if cap_issues:
            warnings.extend(cap_issues)
        
        is_compliant = len(issues) == 0
        
        return {
            'is_compliant': is_compliant,
            'character_count': char_count,
            'issues': issues,
            'warnings': warnings,
            'first_80_chars': title[:80]
        }
    
    def validate_bullet_points(self, bullets: List[str]) -> Dict[str, Any]:
        """
        Validate bullet points against Amazon guidelines
        
        Returns:
            Dict with validation results
        """
        issues = []
        warnings = []
        bullet_results = []
        
        # Check minimum count (3 bullets)
        if len(bullets) < 3:
            issues.append(f"Minimum 3 bullet points required (found {len(bullets)})")
        
        for i, bullet in enumerate(bullets, 1):
            bullet_issues = []
            bullet_warnings = []
            
            # Check character limit (10-255)
            char_count = len(bullet)
            if char_count < 10:
                bullet_issues.append(f"Bullet {i}: Too short ({char_count} chars, minimum 10)")
            elif char_count > 255:
                bullet_issues.append(f"Bullet {i}: Too long ({char_count} chars, maximum 255)")
            
            # Check capitalization (must start with capital)
            if bullet and not bullet[0].isupper():
                bullet_issues.append(f"Bullet {i}: Must start with capital letter")
            
            # Check for end punctuation (should not have)
            if bullet and bullet[-1] in '.!?':
                bullet_warnings.append(f"Bullet {i}: Should not end with punctuation")
            
            # Check for prohibited characters
            prohibited_found = [c for c in bullet if c in self.bullet_prohibited_chars]
            if prohibited_found:
                bullet_issues.append(f"Bullet {i}: Contains prohibited characters: {', '.join(set(prohibited_found))}")
            
            # Check for prohibited emojis
            emoji_found = [c for c in bullet if c in self.bullet_prohibited_emojis]
            if emoji_found:
                bullet_issues.append(f"Bullet {i}: Contains prohibited emojis")
            
            # Check for placeholder text
            bullet_lower = bullet.lower()
            for placeholder in self.bullet_prohibited_placeholders:
                if placeholder in bullet_lower:
                    bullet_issues.append(f"Bullet {i}: Contains placeholder text: '{placeholder}'")
            
            # Check for prohibited claims
            for claim in self.bullet_prohibited_claims:
                if claim in bullet_lower:
                    bullet_issues.append(f"Bullet {i}: Contains prohibited claim: '{claim}'")
            
            # Check for guarantee language
            for guarantee in self.bullet_prohibited_guarantees:
                if guarantee in bullet_lower:
                    bullet_issues.append(f"Bullet {i}: Contains prohibited guarantee language: '{guarantee}'")
            
            # Check for URLs/links
            if 'http' in bullet_lower or 'www.' in bullet_lower:
                bullet_issues.append(f"Bullet {i}: Contains URL/link")
            
            # Check for ASIN
            if re.search(r'B[0-9]{2}[A-Z0-9]{7}', bullet):
                bullet_issues.append(f"Bullet {i}: Contains ASIN")
            
            bullet_results.append({
                'bullet_number': i,
                'text': bullet,
                'character_count': char_count,
                'issues': bullet_issues,
                'warnings': bullet_warnings,
                'is_compliant': len(bullet_issues) == 0
            })
            
            issues.extend(bullet_issues)
            warnings.extend(bullet_warnings)
        
        # Check for duplicate content across bullets
        duplicate_issues = self._check_bullet_duplicates(bullets)
        if duplicate_issues:
            issues.extend(duplicate_issues)
        
        is_compliant = len(issues) == 0
        
        return {
            'is_compliant': is_compliant,
            'bullet_count': len(bullets),
            'issues': issues,
            'warnings': warnings,
            'bullet_results': bullet_results
        }
    
    def _check_word_repetition(self, text: str) -> List[str]:
        """
        Check for word repetition (max 2x, except exempt words)
        
        Returns list of issues
        """
        issues = []
        
        # Extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Count occurrences
        from collections import Counter
        word_counts = Counter(words)
        
        # Check for repetition
        for word, count in word_counts.items():
            if count > 2 and word not in self.exempt_words:
                issues.append(f"Word '{word}' repeated {count} times (max 2)")
        
        return issues
    
    def _check_capitalization(self, title: str) -> List[str]:
        """
        Check title capitalization
        
        Should capitalize first letter of each word except prepositions/articles/conjunctions
        """
        warnings = []
        
        words = title.split()
        for i, word in enumerate(words):
            # Skip if it's a special character or number
            if not word[0].isalpha():
                continue
            
            # First word should always be capitalized
            if i == 0:
                if not word[0].isupper():
                    warnings.append(f"First word '{word}' should be capitalized")
                continue
            
            # Check if it's an exempt word
            word_lower = word.lower()
            if word_lower in self.exempt_words:
                # Exempt words should be lowercase (unless first word)
                if word[0].isupper():
                    warnings.append(f"Word '{word}' should be lowercase (preposition/article/conjunction)")
            else:
                # Non-exempt words should be capitalized
                if not word[0].isupper():
                    warnings.append(f"Word '{word}' should be capitalized")
        
        return warnings
    
    def _check_bullet_duplicates(self, bullets: List[str]) -> List[str]:
        """
        Check for duplicate content across bullets
        
        Returns list of issues
        """
        issues = []
        
        # Check for exact duplicates
        seen = set()
        for i, bullet in enumerate(bullets, 1):
            bullet_lower = bullet.lower().strip()
            if bullet_lower in seen:
                issues.append(f"Bullet {i} is duplicate of another bullet")
            seen.add(bullet_lower)
        
        # Check for very similar content (>80% overlap)
        for i in range(len(bullets)):
            for j in range(i + 1, len(bullets)):
                similarity = self._calculate_similarity(bullets[i], bullets[j])
                if similarity > 0.8:
                    issues.append(f"Bullets {i+1} and {j+1} have very similar content ({int(similarity*100)}% similar)")
        
        return issues
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts (simple word overlap)"""
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def validate_all(self, title: str, bullets: List[str]) -> Dict[str, Any]:
        """
        Validate both title and bullets
        
        Returns combined validation results
        """
        title_validation = self.validate_title(title)
        bullets_validation = self.validate_bullet_points(bullets)
        
        all_compliant = title_validation['is_compliant'] and bullets_validation['is_compliant']
        
        return {
            'is_compliant': all_compliant,
            'title': title_validation,
            'bullets': bullets_validation,
            'total_issues': len(title_validation['issues']) + len(bullets_validation['issues']),
            'total_warnings': len(title_validation['warnings']) + len(bullets_validation['warnings'])
        }
