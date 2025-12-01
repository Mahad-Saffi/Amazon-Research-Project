"""
Keyword Categorization Agent

Categorizes keywords into: Irrelevant, Outlier, Relevant, Design-Specific
Also detects: Misspelled, Spanish (or other languages)
"""
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import CATEGORIZATION_AGENT_INSTRUCTIONS
from research_agents.schemas import KeywordCategorizationResult

load_dotenv(find_dotenv())


categorization_agent = Agent(
    name="CategorizationAgent",
    instructions=CATEGORIZATION_AGENT_INSTRUCTIONS,
    model="gpt-5.1",
    model_settings=ModelSettings(
        max_tokens=5000,
    ),
    output_type=AgentOutputSchema(KeywordCategorizationResult, strict_json_schema=False),
)
