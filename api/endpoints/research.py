"""
Research endpoint for processing Amazon product analysis
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import io
import csv
import json
import asyncio

from api.services.pipeline import ResearchPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# Store progress for each request
progress_store = {}

@router.post("/research")
async def analyze_product(
    design_csv: UploadFile = File(..., description="Design CSV file"),
    revenue_csv: UploadFile = File(..., description="Revenue CSV file"),
    asin_or_url: str = Form(..., description="Amazon ASIN or product URL"),
    marketplace: str = Form(default="US", description="Marketplace code (US, UK, CA, etc.)"),
    use_mock_scraper: bool = Form(default=False, description="Use mock data for testing")
):
    """
    Analyze Amazon product with design and revenue keyword data.
    
    Process:
    1. Deduplicate design CSV (remove keywords present in revenue CSV)
    2. Filter CSVs to keep relevant columns
    3. Add relevancy scores
    4. Extract root keywords
    5. Scrape Amazon product
    6. Generate product summary
    7. Evaluate keyword relevance
    
    Returns CSV with keyword evaluations sorted by relevance and search volume
    """
    try:
        logger.info(f"Starting research for: {asin_or_url}")
        
        # Read uploaded files
        design_content = await design_csv.read()
        revenue_content = await revenue_csv.read()
        
        # Initialize pipeline
        pipeline = ResearchPipeline()
        
        # Run complete pipeline
        result = await pipeline.run_complete_pipeline(
            design_csv_content=design_content,
            revenue_csv_content=revenue_content,
            asin_or_url=asin_or_url,
            marketplace=marketplace,
            use_mock_scraper=use_mock_scraper
        )
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result.get("error", "Pipeline failed"))
        
        # Convert result to CSV for download
        output = io.StringIO()
        if result["keyword_evaluations"]:
            fieldnames = list(result["keyword_evaluations"][0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(result["keyword_evaluations"])
        
        # Return CSV as downloadable file
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=keyword_evaluations_{asin_or_url.replace('/', '_')}.csv"
            }
        )
        
    except Exception as e:
        logger.error(f"Error in research endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/research/json")
async def analyze_product_json(
    design_csv: UploadFile = File(..., description="Design CSV file"),
    revenue_csv: UploadFile = File(..., description="Revenue CSV file"),
    asin_or_url: str = Form(..., description="Amazon ASIN or product URL"),
    marketplace: str = Form(default="US", description="Marketplace code (US, UK, CA, etc.)"),
    use_mock_scraper: bool = Form(default=False, description="Use mock data for testing"),
    request_id: str = Form(default="", description="Request ID for progress tracking")
):
    """
    Same as /research but returns JSON response instead of CSV download
    """
    try:
        logger.info(f"Starting research (JSON) for: {asin_or_url}")
        
        # Read uploaded files
        design_content = await design_csv.read()
        revenue_content = await revenue_csv.read()
        
        # Initialize pipeline
        pipeline = ResearchPipeline()
        
        # Progress callback
        async def update_progress(percent, message):
            if request_id:
                progress_store[request_id] = {"percent": percent, "message": message}
        
        # Run complete pipeline
        result = await pipeline.run_complete_pipeline(
            design_csv_content=design_content,
            revenue_csv_content=revenue_content,
            asin_or_url=asin_or_url,
            marketplace=marketplace,
            use_mock_scraper=use_mock_scraper,
            progress_callback=update_progress
        )
        
        # Clean up progress
        if request_id and request_id in progress_store:
            del progress_store[request_id]
        
        return result
        
    except Exception as e:
        logger.error(f"Error in research/json endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/research/progress/{request_id}")
async def get_progress(request_id: str):
    """Get progress for a specific request"""
    return progress_store.get(request_id, {"percent": 0, "message": "Starting..."})
