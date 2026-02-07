"""
Keyword Irrelevant Detection Agent

Identifies irrelevant keywords by comparing against product title and bullets.
"""
import os
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import IRRELEVANT_AGENT_INSTRUCTIONS
from research_agents.schemas import KeywordIrrelevantResult

load_dotenv(find_dotenv())

# Get model from environment variable
IRRELEVANT_AGENT_MODEL = os.getenv("IRRELEVANT_AGENT_MODEL", "gpt-4o-mini")

irrelevant_agent = Agent(
    name="IrrelevantAgent",
    instructions=IRRELEVANT_AGENT_INSTRUCTIONS,
    model=IRRELEVANT_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=8000,
    ),
    output_type=AgentOutputSchema(KeywordIrrelevantResult, strict_json_schema=False),
)
