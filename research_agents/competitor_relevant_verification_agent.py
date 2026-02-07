"""
Competitor Relevant Verification Agent

Verifies if competitor_relevant keywords are actually relevant by:
1. Scraping the keyword on Amazon
2. Getting top 10 product titles
3. Analyzing if titles match our product
4. If >50% match → mark as relevant
5. If <=50% match → mark as irrelevant
"""
import os
from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv
from agents import AgentOutputSchema
from research_agents.prompts import COMPETITOR_RELEVANT_VERIFICATION_INSTRUCTIONS
from research_agents.schemas import CompetitorRelevantVerificationResult

load_dotenv(find_dotenv())

# Get model from environment variable
COMPETITOR_VERIFICATION_AGENT_MODEL = os.getenv("COMPETITOR_VERIFICATION_AGENT_MODEL", "gpt-4o-mini")

competitor_relevant_verification_agent = Agent(
    name="CompetitorRelevantVerificationAgent",
    instructions=COMPETITOR_RELEVANT_VERIFICATION_INSTRUCTIONS,
    model=COMPETITOR_VERIFICATION_AGENT_MODEL,
    model_settings=ModelSettings(
        max_tokens=8000,
    ),
    output_type=AgentOutputSchema(CompetitorRelevantVerificationResult),
)
