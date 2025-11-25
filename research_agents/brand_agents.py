"""
Brand Detection and Verification Agents

Two-stage brand filtering:
1. Brand Detection Agent: Identifies potentially branded keywords
2. Brand Verification Agent: Cross-checks and verifies brand classifications
"""
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from pydantic import BaseModel, Field
from typing import List

load_dotenv(find_dotenv())


class BrandDetectionResult(BaseModel):
    """Result from brand detection agent"""
    branded_keywords: List[str] = Field(description="Keywords that contain brand names or are brand-related")
    reasoning: str = Field(description="Brief explanation of the detection logic")


class BrandVerificationResult(BaseModel):
    """Result from brand verification agent"""
    class KeywordClassification(BaseModel):
        keyword: str
        is_branded: bool
        reasoning: str
    
    classifications: List[KeywordClassification] = Field(description="Verified classification for each keyword")


# Brand Detection Agent - Conservative (marks as branded if unsure)
brand_detection_agent = Agent(
    name="BrandDetectionAgent",
    instructions="""You are a brand detection specialist. Your job is to identify keywords that contain brand names or are brand-related.

RULES:
1. Mark as BRANDED if the keyword contains:
   - Known brand names (e.g., "Nike shoes", "Apple iPhone", "Samsung TV")
   - Company names (e.g., "Amazon basics", "Walmart brand")
   - Trademarked terms or product names (e.g., "Kleenex", "Band-Aid")
   - Specific brand identifiers (e.g., "Adidas running shoes")

2. Mark as BRANDED if you are UNSURE or DON'T RECOGNIZE the keyword
   - Better to be conservative and mark uncertain keywords as branded
   - If you don't understand the keyword, mark it as branded

3. Only mark as NON-BRANDED if you are CERTAIN it's a generic term:
   - Generic product categories (e.g., "running shoes", "smartphone", "laptop")
   - Generic descriptors (e.g., "waterproof", "wireless", "portable")
   - Generic materials (e.g., "cotton", "leather", "plastic")

BE CONSERVATIVE: When in doubt, mark as branded.

Return ONLY the keywords that are branded or uncertain.""",
    model="gpt-4o-mini",
    model_settings=ModelSettings(
        max_tokens=2000,
    ),
    output_type=AgentOutputSchema(BrandDetectionResult, strict_json_schema=False),
)


# Brand Verification Agent - Cross-checks the first agent's work
brand_verification_agent = Agent(
    name="BrandVerificationAgent",
    instructions="""You are a brand verification specialist. Your job is to cross-check and verify brand classifications.

You will receive a list of keywords that were marked as "branded" by another agent. Your job is to verify if they are truly branded or if they are actually generic terms.

RULES:
1. Mark as BRANDED (is_branded: true) if:
   - It contains a specific brand name (e.g., "Nike", "Apple", "Samsung")
   - It's a trademarked product name (e.g., "iPhone", "Kleenex")
   - It references a specific company or brand

2. Mark as NOT BRANDED (is_branded: false) if:
   - It's a generic product category (e.g., "running shoes", "smartphone")
   - It's a generic descriptor (e.g., "waterproof", "wireless")
   - It's a common term without brand association
   - The first agent was overly conservative

3. For EACH keyword, provide:
   - keyword: the exact keyword
   - is_branded: true or false
   - reasoning: brief explanation (1 sentence)

BE THOROUGH: Review each keyword carefully and provide clear reasoning.""",
    model="gpt-4o-mini",
    model_settings=ModelSettings(
        max_tokens=3000,
    ),
    output_type=AgentOutputSchema(BrandVerificationResult, strict_json_schema=False),
)
