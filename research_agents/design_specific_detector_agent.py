"""
Design-Specific Detector Agent
Uses AI to detect if design-specific keywords are present in current product content
"""
import logging
from typing import List, Dict, Any
from agents import Agent, ModelSettings, AgentOutputSchema, Runner
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


class DesignSpecificDetectionResult(BaseModel):
    """Schema for design-specific detection result"""
    has_design_specific: bool
    found_in_title: List[str]
    found_in_bullets: List[str]
    reasoning: str


# Design-Specific Detection Agent
design_specific_detection_agent = Agent(
    name="DesignSpecificDetectorAgent",
    instructions="""You are an expert at analyzing product listings and identifying design-specific attributes.

Design-specific keywords are attributes that describe specific product characteristics like:
- Material/composition (organic, natural, pure)
- Form/shape (slices, chips, cubes, powder)
- Processing method (freeze dried, dehydrated, roasted)
- Size/quantity specifications (large, small, mini, bulk)
- Special features (resealable, individually wrapped)

Your task is to determine if the current product listing contains any design-specific attributes or keywords.

INSTRUCTIONS:
1. Check if the title contains any design-specific keywords or similar terms
2. Check if the bullet points contain any design-specific keywords or similar terms
3. Consider semantic similarity (e.g., "sliced" is similar to "slices", "organic" matches "organically grown")
4. List which specific keywords were found in title and bullets
5. Provide clear reasoning for your decision

Return your analysis with:
- has_design_specific: true if design-specific keywords are present, false otherwise
- found_in_title: list of design-specific keywords found in title
- found_in_bullets: list of design-specific keywords found in bullets
- reasoning: explanation of your decision""",
    model="gpt-5.2",
    model_settings=ModelSettings(
        max_tokens=1000,
    ),
    output_type=AgentOutputSchema(DesignSpecificDetectionResult, strict_json_schema=False),
)


class DesignSpecificDetectorAgent:
    """AI agent to detect design-specific keywords in product content"""
    
    def __init__(self):
        self.agent = design_specific_detection_agent
    
    async def detect_design_specific_in_content(
        self,
        title: str,
        bullets: List[str],
        design_specific_keywords: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detect if design-specific keywords are present in current content
        
        Args:
            title: Current product title
            bullets: List of current bullet points
            design_specific_keywords: List of design-specific keywords from research
        
        Returns:
            Dict with detection results
        """
        # Extract just the keyword phrases
        ds_keyword_list = [
            kw.get('keyword') or kw.get('Keyword Phrase')
            for kw in design_specific_keywords
        ]
        
        if not ds_keyword_list:
            return {
                'has_design_specific': False,
                'found_in_title': [],
                'found_in_bullets': [],
                'reasoning': 'No design-specific keywords available in research data'
            }
        
        # Prepare input
        bullets_text = "\n".join([f"- {bullet}" for bullet in bullets])
        ds_keywords_text = "\n".join([f"- {kw}" for kw in ds_keyword_list[:20]])  # Limit to 20
        
        input_text = f"""Analyze the current product listing and determine if it contains design-specific attributes.

CURRENT PRODUCT LISTING:

Title: {title}

Bullet Points:
{bullets_text}

DESIGN-SPECIFIC KEYWORDS FROM RESEARCH:
{ds_keywords_text}

Determine if the current product listing (title and bullets) contains any of these design-specific keywords or similar terms."""
        
        try:
            result = await Runner.run(self.agent, input_text)
            detection_raw = getattr(result, "final_output", None)
            
            # Extract structured output
            if detection_raw and hasattr(detection_raw, "model_dump"):
                detection_data = detection_raw.model_dump()
            elif isinstance(detection_raw, dict):
                detection_data = detection_raw
            else:
                raise ValueError("Could not extract structured output")
            
            logger.info(f"Design-specific detection: {detection_data.get('has_design_specific', False)}")
            
            return detection_data
            
        except Exception as e:
            logger.error(f"Error in design-specific detection: {str(e)}")
            # Fallback to simple keyword matching
            return self._fallback_detection(title, bullets, ds_keyword_list)
    
    def _fallback_detection(
        self,
        title: str,
        bullets: List[str],
        design_specific_keywords: List[str]
    ) -> Dict[str, Any]:
        """
        Fallback detection using simple keyword matching
        Used if AI call fails
        """
        title_lower = title.lower()
        bullets_lower = [b.lower() for b in bullets]
        
        found_in_title = []
        found_in_bullets = []
        
        for kw in design_specific_keywords:
            kw_lower = kw.lower()
            
            # Check in title
            if kw_lower in title_lower:
                found_in_title.append(kw)
            
            # Check in bullets
            for bullet in bullets_lower:
                if kw_lower in bullet:
                    found_in_bullets.append(kw)
                    break
        
        has_design_specific = len(found_in_title) > 0 or len(found_in_bullets) > 0
        
        return {
            'has_design_specific': has_design_specific,
            'found_in_title': found_in_title,
            'found_in_bullets': found_in_bullets,
            'reasoning': f"Found {len(found_in_title)} design-specific keywords in title and {len(found_in_bullets)} in bullets using keyword matching"
        }
    
    async def should_include_design_specific(
        self,
        title: str,
        bullets: List[str],
        design_specific_keywords: List[Dict[str, Any]]
    ) -> bool:
        """
        Simple boolean check: should we include design-specific keywords?
        
        Returns:
            True if design-specific keywords should be included, False otherwise
        """
        result = await self.detect_design_specific_in_content(
            title,
            bullets,
            design_specific_keywords
        )
        
        return result.get('has_design_specific', False)
