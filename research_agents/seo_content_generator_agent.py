"""
SEO Content Generator Agent
Generates optimized titles and bullet points with selected keywords
"""
import logging
import os
from typing import List, Dict, Any
from agents import Agent, ModelSettings, AgentOutputSchema, Runner
from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)


# Get models from environment variables
TITLE_GENERATION_AGENT_MODEL = os.getenv("TITLE_GENERATION_AGENT_MODEL", "gpt-4o-mini")
BULLET_GENERATION_AGENT_MODEL = os.getenv("BULLET_GENERATION_AGENT_MODEL", "gpt-4o-mini")


class OptimizedTitleResult(BaseModel):
    """Schema for optimized title generation"""
    optimized_title: str
    keywords_used: List[str]
    character_count: int
    reasoning: str


class OptimizedBulletPointsResult(BaseModel):
    """Schema for optimized bullet points generation"""
    bullet_points: List[str]
    keywords_per_bullet: List[List[str]]
    reasoning: str


# Title Generation Agent
title_generation_agent = Agent(
    name="TitleGenerationAgent",
    instructions="""You are an expert Amazon listing optimizer specializing in creating high-converting, SEO-optimized product titles.

Your task is to generate an optimized product title that:
1. Incorporates the provided keywords naturally
2. Follows Amazon's title guidelines strictly
3. Maintains readability and customer appeal
4. Prioritizes main keyword and design-specific keywords in first 80 characters

AMAZON TITLE GUIDELINES (MUST FOLLOW):
- Maximum 200 characters (including spaces)
- Ideally 80 characters or fewer for mobile visibility
- NO promotional phrases ("free shipping", "100% guaranteed")
- NO special characters: ! $ ? _ { } ^ ¬ ¦
- Same word maximum 2 times (except prepositions/articles/conjunctions)
- Capitalize first letter of each word (except: in, on, and, or, the, a, an)
- Use numerals not spelled numbers (2 vs two)
- Abbreviate measurements (cm, oz, in, kg)

STRUCTURE:
Brand → Main Keyword → Design-Specific Keywords → Key Attributes → Size/Color/Model

CRITICAL RULES:
- First 80 characters MUST contain main keyword + design-specific keyword + key benefit
- Keywords must flow naturally - NO keyword stuffing
- Maintain professional, customer-friendly tone
- Focus on what customers search for and care about

Return:
- optimized_title: The complete optimized title
- keywords_used: List of keywords successfully incorporated
- character_count: Total character count
- reasoning: Brief explanation of your optimization strategy""",
    model=TITLE_GENERATION_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=1500,
    ),
    output_type=AgentOutputSchema(OptimizedTitleResult, strict_json_schema=False),
)


# Bullet Points Generation Agent
bullet_points_generation_agent = Agent(
    name="BulletPointsGenerationAgent",
    instructions="""You are an expert Amazon listing optimizer specializing in creating compelling, SEO-optimized bullet points.

Your task is to generate optimized bullet points that:
1. Incorporate 2-3 keywords per bullet naturally
2. Follow Amazon's bullet point guidelines strictly
3. Highlight unique features, benefits, and use cases
4. Maintain readability and customer appeal

AMAZON BULLET POINT GUIDELINES (MUST FOLLOW):
- Minimum 3 bullet points
- 10-255 characters per bullet
- Start with capital letter
- NO end punctuation (no periods, exclamation marks)
- Use semicolons to separate phrases within bullet
- Format: "Header: Description" (e.g., "Premium Quality: Made from 100% organic ingredients")
- Spell out numbers 1-9 (except measurements)
- Space between digit and unit ("60 ml")
- NO special characters: ™ ® € … † ‡ ¢ £ ¥ © ± ~
- NO emojis
- NO placeholder text (NA, TBD, etc.)
- NO guarantee language
- Each bullet must be UNIQUE (no repetition)

STRUCTURE PER BULLET:
Feature/Benefit Header: Detailed description with keywords naturally incorporated

CRITICAL RULES:
- Each bullet must provide UNIQUE information
- Keywords must flow naturally - NO keyword stuffing
- Focus on customer benefits, not just features
- Use descriptive, compelling language
- Maintain professional tone

Return:
- bullet_points: List of 5 optimized bullet points
- keywords_per_bullet: List of keywords used in each bullet
- reasoning: Brief explanation of your optimization strategy""",
    model=BULLET_GENERATION_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=2000,
    ),
    output_type=AgentOutputSchema(OptimizedBulletPointsResult, strict_json_schema=False),
)


class SEOContentGeneratorAgent:
    """AI agent to generate optimized titles and bullet points"""
    
    def __init__(self):
        self.title_agent = title_generation_agent
        self.bullet_agent = bullet_points_generation_agent
    
    async def generate_optimized_title(
        self,
        current_title: str,
        selected_keywords: List[Dict[str, Any]],
        product_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized title
        
        Args:
            current_title: Current product title
            selected_keywords: Keywords to incorporate (with search volumes)
            product_info: Additional product information (brand, category, etc.)
        
        Returns:
            Dict with optimized title and metadata
        """
        # Prepare keyword list with search volumes
        keywords_text = "\n".join([
            f"- {kw['keyword']} (Search Volume: {kw['search_volume']:,})"
            for kw in selected_keywords
        ])
        
        # Prepare product info
        brand = product_info.get('brand', '') if product_info else ''
        category = product_info.get('category', '') if product_info else ''
        
        input_text = f"""Generate an optimized Amazon product title.

CURRENT TITLE:
{current_title}

KEYWORDS TO INCORPORATE (prioritize by search volume):
{keywords_text}

PRODUCT INFORMATION:
Brand: {brand or 'Not specified'}
Category: {category or 'Not specified'}

REQUIREMENTS:
1. Incorporate as many high-volume keywords as possible naturally
2. Ensure first 80 characters contain main keyword + design-specific keywords
3. Follow all Amazon title guidelines
4. Maximum 200 characters
5. Maintain readability and customer appeal

Generate the optimized title now."""
        
        try:
            result = await Runner.run(self.title_agent, input_text)
            output = getattr(result, "final_output", None)
            
            if output and hasattr(output, "model_dump"):
                data = output.model_dump()
            elif isinstance(output, dict):
                data = output
            else:
                raise ValueError("Could not extract structured output")
            
            logger.info(f"Generated optimized title: {data.get('character_count', 0)} chars")
            
            return data
            
        except Exception as e:
            logger.error(f"Error generating optimized title: {str(e)}")
            return {
                'optimized_title': current_title,
                'keywords_used': [],
                'character_count': len(current_title),
                'reasoning': f'Error: {str(e)}'
            }
    
    async def generate_optimized_bullets(
        self,
        current_bullets: List[str],
        selected_keywords: List[Dict[str, Any]],
        product_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate optimized bullet points
        
        Args:
            current_bullets: Current bullet points
            selected_keywords: Keywords to incorporate (with search volumes)
            product_info: Additional product information
        
        Returns:
            Dict with optimized bullets and metadata
        """
        # Prepare keyword list
        keywords_text = "\n".join([
            f"- {kw['keyword']} (Search Volume: {kw['search_volume']:,})"
            for kw in selected_keywords
        ])
        
        # Prepare current bullets
        current_bullets_text = "\n".join([
            f"{i}. {bullet}"
            for i, bullet in enumerate(current_bullets, 1)
        ])
        
        input_text = f"""Generate optimized Amazon product bullet points.

CURRENT BULLET POINTS:
{current_bullets_text}

KEYWORDS TO INCORPORATE (distribute 2-3 per bullet):
{keywords_text}

REQUIREMENTS:
1. Generate 5 bullet points
2. Incorporate 2-3 keywords per bullet naturally
3. Each bullet must be UNIQUE (different information)
4. Follow all Amazon bullet point guidelines
5. 10-255 characters per bullet
6. Focus on features, benefits, and use cases
7. Maintain readability and customer appeal

Generate the optimized bullet points now."""
        
        try:
            result = await Runner.run(self.bullet_agent, input_text)
            output = getattr(result, "final_output", None)
            
            if output and hasattr(output, "model_dump"):
                data = output.model_dump()
            elif isinstance(output, dict):
                data = output
            else:
                raise ValueError("Could not extract structured output")
            
            logger.info(f"Generated {len(data.get('bullet_points', []))} optimized bullet points")
            
            return data
            
        except Exception as e:
            logger.error(f"Error generating optimized bullets: {str(e)}")
            return {
                'bullet_points': current_bullets,
                'keywords_per_bullet': [[] for _ in current_bullets],
                'reasoning': f'Error: {str(e)}'
            }
