"""
Research endpoint for processing Amazon product analysis
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
import logging
import asyncio
from pathlib import Path
import json
import base64

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
    rank_threshold: int = Form(default=11, description="Rank threshold for relevancy scoring (B0 column values below this count as relevant)"),
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
            rank_threshold=rank_threshold,
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

@router.websocket("/research/ws")
async def websocket_research(websocket: WebSocket):
    """
    WebSocket endpoint for real-time research pipeline with progress updates.
    
    Receives:
    - design_csv: base64 encoded CSV content
    - revenue_csv: base64 encoded CSV content
    - asin_or_url: Amazon ASIN or product URL
    - marketplace: Marketplace code (US, UK, CA, etc.)
    - use_mock_scraper: Use mock data for testing
    - use_direct_verification: Use direct verification method
    - request_id: Request ID for logging
    
    Sends:
    - progress updates: {"type": "progress", "percent": int, "message": str}
    - final result: {"type": "complete", "data": dict}
    - errors: {"type": "error", "error": str}
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Receive initial data from client
        data = await websocket.receive_json()
        logger.info(f"Received WebSocket data for: {data.get('asin_or_url')}")
        
        # Extract parameters
        asin_or_url = data.get("asin_or_url")
        marketplace = data.get("marketplace", "US")
        use_mock_scraper = data.get("use_mock_scraper", False)
        use_direct_verification = data.get("use_direct_verification", False)
        include_seo_optimization = data.get("include_seo_optimization", True)  # New parameter
        rank_threshold = int(data.get("rank_threshold", 11))
        request_id = data.get("request_id", "")
        
        # Decode base64 file data
        design_content = base64.b64decode(data.get("design_csv"))
        revenue_content = base64.b64decode(data.get("revenue_csv"))
        
        logger.info(f"Files decoded - Design: {len(design_content)} bytes, Revenue: {len(revenue_content)} bytes")
        
        # Progress callback that sends updates via WebSocket
        async def ws_progress_callback(percent, message):
            try:
                await websocket.send_json({
                    "type": "progress",
                    "percent": percent,
                    "message": message
                })
                logger.debug(f"Progress sent: {percent}% - {message}")
            except Exception as e:
                logger.error(f"Error sending progress: {e}")
        
        # Initialize pipeline
        pipeline = ResearchPipeline()
        
        # Run pipeline with WebSocket progress updates
        logger.info("Starting pipeline execution via WebSocket")
        result = await pipeline.run_complete_pipeline(
            design_csv_content=design_content,
            revenue_csv_content=revenue_content,
            asin_or_url=asin_or_url,
            marketplace=marketplace,
            use_mock_scraper=use_mock_scraper,
            use_direct_verification=use_direct_verification,
            include_seo_optimization=include_seo_optimization,  # Pass parameter
            rank_threshold=rank_threshold,
            progress_callback=ws_progress_callback,
            request_id=request_id if request_id else None
        )
        
        # Send final result
        logger.info("Pipeline complete, sending final result")
        await websocket.send_json({
            "type": "complete",
            "data": result
        })
        
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected by client")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            logger.error("Failed to send error message to client")
    finally:
        try:
            await websocket.close()
            logger.info("WebSocket connection closed")
        except:
            pass

