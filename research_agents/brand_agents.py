"""
Brand Detection Agent

Single-stage brand filtering that identifies branded keywords anywhere in the phrase.
"""
import os
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import BRAND_DETECTION_AGENT_INSTRUCTIONS
from research_agents.schemas import BrandDetectionResult

load_dotenv(find_dotenv())

# Get model from environment variable
BRAND_DETECTION_AGENT_MODEL = os.getenv("BRAND_DETECTION_AGENT_MODEL", "gpt-4o-mini")

# Brand Detection Agent - Detects brands anywhere in keyword
brand_detection_agent = Agent(
    name="BrandDetectionAgent",
    instructions=BRAND_DETECTION_AGENT_INSTRUCTIONS,
    model=BRAND_DETECTION_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=3000,
    ),
    output_type=AgentOutputSchema(BrandDetectionResult, strict_json_schema=False),
)
