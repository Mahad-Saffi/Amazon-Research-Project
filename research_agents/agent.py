from agents import Agent, ModelSettings
from dotenv import load_dotenv, find_dotenv

from agents import AgentOutputSchema
from .schemas import ProductSummary, KeywordEvaluations
from .prompts import SUMMARY_INSTRUCTIONS, EVALUATION_INSTRUCTIONS


load_dotenv(find_dotenv())  # Load environment variables from .env file


summary_agent = Agent(
    name="SummaryAgent",
    instructions=SUMMARY_INSTRUCTIONS,
    model="gpt-5-mini",
    model_settings=ModelSettings(
        max_tokens=2000,
    ),
    output_type=AgentOutputSchema(ProductSummary, strict_json_schema=False),
)

evaluation_agent = Agent(
    name="EvaluationAgent",
    instructions=EVALUATION_INSTRUCTIONS,
    model="gpt-5",
    model_settings=ModelSettings(
        max_tokens=4000,
    ),
    output_type=AgentOutputSchema(KeywordEvaluations, strict_json_schema=False),
)
