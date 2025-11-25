"""
Complete research pipeline - processes everything in memory
"""
import logging
import json
import asyncio
import csv
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime
from agents import Runner

from api.services.csv_processor import CSVProcessor
from research_agents.agent import summary_agent, evaluation_agent
from research_agents.helper_methods import scrape_amazon_listing

logger = logging.getLogger(__name__)

class ResearchPipeline:
    """Complete pipeline for Amazon product research"""
    
    def __init__(self):
        self.csv_processor = CSVProcessor()
    
    async def run_complete_pipeline(
        self,
        design_csv_content: bytes,
        revenue_csv_content: bytes,
        asin_or_url: str,
        marketplace: str = "US",
        use_mock_scraper: bool = False,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Run complete research pipeline in memory
        
        Steps:
        1. Parse CSV files
        2. Deduplicate design CSV
        3. Filter columns
        4. Add relevancy scores
        5. Extract root keywords
        6. Scrape Amazon product
        7. Generate product summary
        8. Evaluate keyword relevance
        
        Returns:
            Dict with success flag, product summary, keyword evaluations, and metadata
        """
        try:
            # Step 1: Parse CSV files (10%)
            if progress_callback:
                await progress_callback(10, "Parsing CSV files...")
            logger.info("Step 1: Parsing CSV files")
            design_rows = self.csv_processor.parse_csv_content(design_csv_content)
            revenue_rows = self.csv_processor.parse_csv_content(revenue_csv_content)
            logger.info(f"Parsed {len(design_rows)} design rows, {len(revenue_rows)} revenue rows")
            
            # Step 2: Deduplicate design (15%)
            if progress_callback:
                await progress_callback(15, "Deduplicating design CSV...")
            logger.info("Step 2: Deduplicating design CSV")
            design_dedup = self.csv_processor.deduplicate_design(design_rows, revenue_rows)
            
            # If deduplication removes everything, use original design rows
            if len(design_dedup) == 0 and len(design_rows) > 0:
                logger.warning("⚠️  Deduplication removed all design rows, using original design data")
                design_dedup = design_rows
            
            # Step 3: Filter columns (20%)
            if progress_callback:
                await progress_callback(20, "Filtering columns...")
            logger.info("Step 3: Filtering columns")
            design_filtered = self.csv_processor.filter_columns(design_dedup) if design_dedup else []
            revenue_filtered = self.csv_processor.filter_columns(revenue_rows) if revenue_rows else []
            
            # Step 4: Add relevancy (25%)
            if progress_callback:
                await progress_callback(25, "Adding relevancy scores...")
            logger.info("Step 4: Adding relevancy scores")
            design_relevancy = self.csv_processor.add_relevancy(design_filtered) if design_filtered else []
            revenue_relevancy = self.csv_processor.add_relevancy(revenue_filtered) if revenue_filtered else []
            
            # Check if we have any data to process
            if not design_relevancy and not revenue_relevancy:
                logger.error("❌ No data remaining after filtering and relevancy scoring")
                return {
                    "success": False,
                    "error": "No keywords with relevancy >= 2 found in either CSV file. Please check your data.",
                    "metadata": {
                        "design_rows_original": len(design_rows),
                        "revenue_rows_original": len(revenue_rows),
                        "design_rows_filtered": 0,
                        "revenue_rows_filtered": 0
                    }
                }
            
            # Step 5: Extract root keywords (28-32%)
            if progress_callback:
                await progress_callback(28, "Extracting root keywords...")
            logger.info("Step 5: Extracting root keywords")
            root_keywords = self.csv_processor.extract_root_keywords(
                design_relevancy, 
                revenue_relevancy
            )
            
            if progress_callback:
                await progress_callback(32, "Root keywords extracted")
            
            # Get top 10 root keywords
            top_10_roots = [rk['keyword'] for rk in root_keywords[:10]]
            logger.info(f"Top 10 root keywords: {top_10_roots}")
            
            # Step 6: Scrape Amazon product (35-45%)
            if progress_callback:
                await progress_callback(35, "Scraping Amazon product...")
            logger.info(f"Step 6: Scraping Amazon listing: {asin_or_url}")
            scraped_result = scrape_amazon_listing(asin_or_url, marketplace, use_mock=use_mock_scraper)
            
            if not scraped_result.get("success"):
                return {
                    "success": False,
                    "error": f"Scraping failed: {scraped_result.get('error', 'Unknown error')}",
                    "scraped_data": scraped_result
                }
            
            scraped_data = scraped_result.get("data", {})
            logger.info("✅ Scraping successful")
            
            if progress_callback:
                await progress_callback(45, "Product data retrieved successfully")
            
            # Step 7: Filter keywords containing top 10 roots
            logger.info("Step 7: Filtering keywords by top 10 roots")
            filtered_rows = []
            all_rows = (design_relevancy or []) + (revenue_relevancy or [])
            
            for row in all_rows:
                kw = row.get('Keyword Phrase', '').strip()
                if kw and any(root.lower() in kw.lower() for root in top_10_roots):
                    filtered_rows.append(row)
            
            logger.info(f"Filtered to {len(filtered_rows)} rows containing top 10 roots")
            
            # Check if we have keywords to evaluate
            if not filtered_rows:
                logger.warning("⚠️  No keywords found matching top 10 root keywords")
                return {
                    "success": True,
                    "product_summary": [],
                    "keyword_evaluations": [],
                    "scraped_data": scraped_data,
                    "csv_filename": "",
                    "metadata": {
                        "asin_or_url": asin_or_url,
                        "marketplace": marketplace,
                        "top_10_roots": top_10_roots,
                        "design_rows_original": len(design_rows),
                        "revenue_rows_original": len(revenue_rows),
                        "design_rows_deduped": len(design_dedup),
                        "design_rows_filtered": len(design_relevancy) if design_relevancy else 0,
                        "revenue_rows_filtered": len(revenue_relevancy) if revenue_relevancy else 0,
                        "keywords_evaluated": 0,
                        "keywords_final": 0,
                        "batches_processed": 0,
                        "warning": "No keywords found matching top root keywords"
                    }
                }
            
            # Get keywords for evaluation
            keywords_list = [row['Keyword Phrase'] for row in filtered_rows]
            
            # Step 8: Generate product summary (60%)
            if progress_callback:
                await progress_callback(60, "Generating AI product summary...")
            logger.info("Step 8: Generating product summary")
            try:
                summary_prompt = f"Analyze the following scraped product data and create a concise summary in bullet points.\n\nScraped Product Data:\n{json.dumps(scraped_data, indent=2)}"
                summary_result = await Runner.run(summary_agent, summary_prompt)
                
                summary_raw = getattr(summary_result, "final_output", None)
                summary_structured = self._extract_structured_output(summary_raw)
                product_summary = summary_structured.get("product_summary", [])
                logger.info(f"✅ Summary complete: {len(product_summary)} bullet points")
            except Exception as e:
                logger.error(f"❌ Summary agent failed: {str(e)}")
                return {"success": False, "error": f"Summary failed: {str(e)}", "scraped_data": scraped_data}
            
            # Step 9: Evaluate keywords in batches (70%)
            if progress_callback:
                await progress_callback(70, "Evaluating keyword relevance with AI...")
            logger.info("Step 9: Evaluating keyword relevance")
            batch_size = 20
            batches = [keywords_list[i:i + batch_size] for i in range(0, len(keywords_list), batch_size)]
            logger.info(f"Created {len(batches)} batches for parallel evaluation")
            
            completed_batches = 0
            
            async def evaluate_batch(batch):
                nonlocal completed_batches
                try:
                    eval_prompt = f"Evaluate the relevance of the following keywords to the product based on the summary.\n\nProduct Summary:\n{json.dumps(product_summary, indent=2)}\n\nKeywords:\n{json.dumps(batch, indent=2)}"
                    eval_result = await Runner.run(evaluation_agent, eval_prompt)
                    eval_raw = getattr(eval_result, "final_output", None)
                    eval_structured = self._extract_structured_output(eval_raw)
                    
                    # Update progress for each completed batch
                    completed_batches += 1
                    if progress_callback:
                        progress_percent = 70 + (completed_batches / len(batches)) * 20  # 70-90%
                        await progress_callback(progress_percent, f"Evaluating keywords ({completed_batches}/{len(batches)} batches)...")
                    
                    return eval_structured.get("keyword_evaluations", [])
                except Exception as e:
                    logger.error(f"Error evaluating batch: {str(e)}")
                    completed_batches += 1
                    return []
            
            tasks = [evaluate_batch(batch) for batch in batches]
            batch_results = await asyncio.gather(*tasks)
            
            # Flatten results
            keyword_evaluations = [eval for batch in batch_results for eval in batch if eval]
            logger.info(f"✅ Evaluation complete: {len(keyword_evaluations)} evaluations")
            
            # Check if we got any evaluations
            if not keyword_evaluations:
                logger.warning("⚠️  No keyword evaluations returned from AI")
                return {
                    "success": True,
                    "product_summary": product_summary,
                    "keyword_evaluations": [],
                    "scraped_data": scraped_data,
                    "csv_filename": "",
                    "metadata": {
                        "asin_or_url": asin_or_url,
                        "marketplace": marketplace,
                        "top_10_roots": top_10_roots,
                        "design_rows_original": len(design_rows),
                        "revenue_rows_original": len(revenue_rows),
                        "design_rows_deduped": len(design_dedup),
                        "design_rows_filtered": len(design_relevancy) if design_relevancy else 0,
                        "revenue_rows_filtered": len(revenue_relevancy) if revenue_relevancy else 0,
                        "keywords_evaluated": 0,
                        "keywords_final": 0,
                        "batches_processed": len(batches),
                        "warning": "AI evaluation returned no results"
                    }
                }
            
            # Sort by relevance_score descending
            keyword_evaluations.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Merge with original row data
            merged_evaluations = []
            for eval in keyword_evaluations:
                try:
                    matching_row = next(
                        (row for row in filtered_rows 
                         if row.get('Keyword Phrase', '').strip().lower() == eval.get('keyword', '').strip().lower()), 
                        None
                    )
                    if matching_row:
                        merged = {**eval, **matching_row}
                        merged_evaluations.append(merged)
                except Exception as e:
                    logger.error(f"Error merging evaluation: {str(e)}")
                    continue
            
            # Filter to relevance_score >= 5
            merged_evaluations = [row for row in merged_evaluations if row.get('relevance_score', 0) >= 5]
            
            # Sort by search volume descending
            try:
                merged_evaluations.sort(
                    key=lambda x: int(x.get('Search Volume', 0)) if x.get('Search Volume') else 0, 
                    reverse=True
                )
            except Exception as e:
                logger.error(f"Error sorting by search volume: {str(e)}")
            
            logger.info(f"✅ Pipeline complete: {len(merged_evaluations)} final evaluations")
            
            # Check if we have final results
            if not merged_evaluations:
                logger.warning("⚠️  No keywords with relevance score >= 5")
                return {
                    "success": True,
                    "product_summary": product_summary,
                    "keyword_evaluations": [],
                    "scraped_data": scraped_data,
                    "csv_filename": "",
                    "metadata": {
                        "asin_or_url": asin_or_url,
                        "marketplace": marketplace,
                        "top_10_roots": top_10_roots,
                        "design_rows_original": len(design_rows),
                        "revenue_rows_original": len(revenue_rows),
                        "design_rows_deduped": len(design_dedup),
                        "design_rows_filtered": len(design_relevancy) if design_relevancy else 0,
                        "revenue_rows_filtered": len(revenue_relevancy) if revenue_relevancy else 0,
                        "keywords_evaluated": len(keyword_evaluations),
                        "keywords_final": 0,
                        "batches_processed": len(batches),
                        "warning": "No keywords met the relevance threshold (>= 5)"
                    }
                }
            
            # Auto-save CSV to results folder
            csv_filename = self._save_results_to_csv(merged_evaluations, asin_or_url)
            
            return {
                "success": True,
                "product_summary": product_summary,
                "keyword_evaluations": merged_evaluations,
                "scraped_data": scraped_data,
                "csv_filename": csv_filename,
                "metadata": {
                    "asin_or_url": asin_or_url,
                    "marketplace": marketplace,
                    "top_10_roots": top_10_roots,
                    "design_rows_original": len(design_rows),
                    "revenue_rows_original": len(revenue_rows),
                    "design_rows_deduped": len(design_dedup),
                    "design_rows_filtered": len(design_relevancy),
                    "revenue_rows_filtered": len(revenue_relevancy),
                    "keywords_evaluated": len(keyword_evaluations),
                    "keywords_final": len(merged_evaluations),
                    "batches_processed": len(batches)
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_structured_output(self, output: Any) -> Dict[str, Any]:
        """Extract structured data from agent output"""
        if output and hasattr(output, "model_dump"):
            return output.model_dump()
        elif isinstance(output, dict):
            return output
        elif isinstance(output, str):
            return self._extract_json_from_string(output)
        return {}
    
    def _extract_json_from_string(self, text: str) -> Dict[str, Any]:
        """Extract JSON object from string"""
        import re
        if not text:
            return {}
        matches = re.findall(r"\{[\s\S]*\}", text)
        for snippet in reversed(matches):
            try:
                obj = json.loads(snippet)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                continue
        return {}
    
    def _save_results_to_csv(self, evaluations: List[Dict[str, Any]], asin_or_url: str) -> str:
        """Save results to CSV file in results folder"""
        try:
            # Check if we have data to save
            if not evaluations:
                logger.warning("⚠️  No evaluations to save")
                return ""
            
            # Create results directory if it doesn't exist
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            asin_clean = asin_or_url.replace('/', '_').replace(':', '_').replace('?', '_')[:50]
            filename = f"keyword_evaluations_{asin_clean}_{timestamp}.csv"
            filepath = results_dir / filename
            
            # Write CSV with UTF-8 encoding
            fieldnames = list(evaluations[0].keys())
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(evaluations)
            
            logger.info(f"✅ Results saved to: {filepath}")
            return str(filename)
            
        except Exception as e:
            logger.error(f"❌ Error saving CSV: {str(e)}")
            return ""
