"""
Keyword Categorization Agent

Categorizes keywords into: Irrelevant, Outlier, Relevant, Design-Specific
Also detects: Misspelled, Spanish (or other languages)
"""
import os
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import CATEGORIZATION_AGENT_INSTRUCTIONS
from research_agents.schemas import KeywordCategorizationResult

load_dotenv(find_dotenv())

# Get model from environment variable
CATEGORIZATION_AGENT_MODEL = os.getenv("CATEGORIZATION_AGENT_MODEL", "gpt-4o-mini")

categorization_agent = Agent(
    name="CategorizationAgent",
    instructions=CATEGORIZATION_AGENT_INSTRUCTIONS,
    model=CATEGORIZATION_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=5000,
    ),
    output_type=AgentOutputSchema(KeywordCategorizationResult, strict_json_schema=False),
)
