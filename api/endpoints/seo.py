"""
SEO Optimization Endpoint
Provides SEO optimization for product listings
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from api.services.seo_optimization_service import SEOOptimizationService

logger = logging.getLogger(__name__)

router = APIRouter()


class SEOOptimizationRequest(BaseModel):
    """Request model for SEO optimization"""
    current_title: str
    current_bullets: List[str]
    keyword_evaluations: List[Dict[str, Any]]
    product_info: Optional[Dict[str, Any]] = None


@router.post("/seo/optimize")
async def optimize_seo(request: SEOOptimizationRequest):
    """
    Optimize product title and bullet points for SEO
    
    Args:
        request: SEO optimization request with current content and keywords
    
    Returns:
        Complete SEO optimization results with side-by-side comparison
    """
    try:
        logger.info(f"SEO optimization requested for: {request.current_title[:50]}...")
        
        service = SEOOptimizationService()
        
        result = await service.optimize_listing(
            current_title=request.current_title,
            current_bullets=request.current_bullets,
            keyword_evaluations=request.keyword_evaluations,
            product_info=request.product_info
        )
        
        logger.info("SEO optimization completed successfully")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in SEO optimization: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seo/optimize-from-research")
async def optimize_from_research(
    asin_or_url: str,
    keyword_evaluations: List[Dict[str, Any]],
    scraped_data: Dict[str, Any],
    product_info: Optional[Dict[str, Any]] = None
):
    """
    Optimize SEO using data from research pipeline
    
    Args:
        asin_or_url: Product ASIN or URL
        keyword_evaluations: Keyword research results
        scraped_data: Scraped product data (title, bullets, etc.)
        product_info: Additional product information
    
    Returns:
        Complete SEO optimization results
    """
    try:
        logger.info(f"SEO optimization from research for: {asin_or_url}")
        
        # Extract current content from scraped data
        current_title = scraped_data.get('title', '')
        current_bullets = scraped_data.get('bullets', [])
        
        if not current_title:
            raise HTTPException(status_code=400, detail="No title found in scraped data")
        
        if not current_bullets:
            raise HTTPException(status_code=400, detail="No bullet points found in scraped data")
        
        # Run optimization
        service = SEOOptimizationService()
        
        result = await service.optimize_listing(
            current_title=current_title,
            current_bullets=current_bullets,
            keyword_evaluations=keyword_evaluations,
            product_info=product_info
        )
        
        logger.info("SEO optimization from research completed successfully")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in SEO optimization from research: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
