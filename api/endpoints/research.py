"""
Research endpoint for processing Amazon product analysis
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import logging
import asyncio
from pathlib import Path

from api.services.pipeline import ResearchPipeline

logger = logging.getLogger(__name__)

router = APIRouter()

# Store progress for each request
progress_store = {}

@router.post("/research/json")
async def analyze_product_json(
    design_csv: UploadFile = File(..., description="Design CSV file"),
    revenue_csv: UploadFile = File(..., description="Revenue CSV file"),
    asin_or_url: str = Form(..., description="Amazon ASIN or product URL"),
    marketplace: str = Form(default="US", description="Marketplace code (US, UK, CA, etc.)"),
    use_mock_scraper: bool = Form(default=False, description="Use mock data for testing"),
    use_direct_verification: bool = Form(default=False, description="Use direct verification method (scrape all irrelevant keywords)"),
    request_id: str = Form(default="", description="Request ID for progress tracking")
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
    
    Returns JSON response with keyword evaluations, product summary, and metadata
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
            use_direct_verification=use_direct_verification,
            progress_callback=update_progress,
            request_id=request_id if request_id else None
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

@router.get("/research/download/{filename}")
async def download_csv(filename: str):
    """
    Download the final CSV file from results folder
    
    Args:
        filename: The CSV filename (e.g., keyword_evaluations_ASIN_TIMESTAMP.csv)
    
    Returns:
        The CSV file as a downloadable attachment
    """
    try:
        # Validate filename to prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        # Construct file path
        results_dir = Path("results")
        file_path = results_dir / filename
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Check if file is actually in results directory (security check)
        if not str(file_path.resolve()).startswith(str(results_dir.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        
        logger.info(f"Downloading: {filename}")
        
        # Return file as download
        return FileResponse(
            path=file_path,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

