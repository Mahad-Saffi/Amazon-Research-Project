"""
Enhanced Keyword Irrelevant Categorization Agent

Re-categorizes irrelevant keywords by:
1. Extracting meaningful modifiers (removing stop words and common terms)
2. Checking if modifiers appear in competitor titles (144 titles from 3 keywords × 48 each)
3. For modifiers found in competitor titles, scraping the irrelevant keyword itself
4. Using an agent to verify if top organic results match our product
"""
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import ENHANCED_IRRELEVANT_AGENT_INSTRUCTIONS
from research_agents.schemas import KeywordEnhancedIrrelevantResult

load_dotenv(find_dotenv())


enhanced_irrelevant_agent = Agent(
    name="EnhancedIrrelevantAgent",
    instructions=ENHANCED_IRRELEVANT_AGENT_INSTRUCTIONS,
    model="gpt-4o",
    model_settings=ModelSettings(
        max_tokens=8000,
    ),
    output_type=AgentOutputSchema(KeywordEnhancedIrrelevantResult),
)
