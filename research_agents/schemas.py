from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional, List
from enum import Enum


class MarketTier(str, Enum):
    BUDGET = "budget"
    PREMIUM = "premium"


class MarketPosition(BaseModel):
    model_config = ConfigDict(extra='forbid')
    tier: MarketTier = Field(..., description="Market tier of the product, e.g., budget, premium")
    rationale: str = Field(..., description="Rationale for the market position")
    price: Optional[float] = Field(default=None, description="Price of the product")
    currency: Optional[str] = Field(default=None, description="Currency of the price")
    unit_count: Optional[float] = Field(default=None, description="Unit count of the product")
    unit_name: Optional[str] = Field(default=None, description="Unit name of the product")


class MainKeywordInfo(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chosen: Optional[str] = Field(..., description="Chosen main keyword")
    candidates: List[str] = Field(..., description="List of candidate keywords for the main keyword")
    rationale: Optional[str] = Field(..., description="Rationale for the main keyword selection")


class CurrentListing(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(..., description="Title of the current listing")
    bullets: List[str] = Field(..., description="List of bullet points for the product")
    backend_keywords: List[str] = Field(..., description="List of backend keywords for the product")


class ContentSources(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: Dict[str, Any] = Field(..., description="Content related to the product title")
    images: Dict[str, Any] = Field(..., description="Content related to product images")
    aplus_content: Dict[str, Any] = Field(..., description="Content related to A+ content")
    reviews: Dict[str, Any] = Field(..., description="Content related to product reviews")
    qa_section: Dict[str, Any] = Field(..., description="Content related to Q&A section")


class KeywordEvaluation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    keyword: str
    relevance_score: int = Field(..., ge=1, le=10, description="Relevance score from 1 to 10")
    rationale: str


class ProductSummary(BaseModel):
    model_config = ConfigDict(extra='forbid')
    product_summary: List[str]


class KeywordEvaluations(BaseModel):
    model_config = ConfigDict(extra='forbid')
    keyword_evaluations: List[KeywordEvaluation]
