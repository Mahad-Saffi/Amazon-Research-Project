"""
Keyword Irrelevant Detection Agent

Identifies irrelevant keywords by comparing against product title and bullets.
"""
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import IRRELEVANT_AGENT_INSTRUCTIONS
from research_agents.schemas import KeywordIrrelevantResult

load_dotenv(find_dotenv())


irrelevant_agent = Agent(
    name="IrrelevantAgent",
    instructions=IRRELEVANT_AGENT_INSTRUCTIONS,
    model="gpt-4o-mini",
    model_settings=ModelSettings(
        max_tokens=8000,
    ),
    output_type=AgentOutputSchema(KeywordIrrelevantResult, strict_json_schema=False),
)
