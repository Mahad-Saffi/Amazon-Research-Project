"""
Complete research pipeline - processes everything in memory
"""
import logging
import json
import asyncio
import csv
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from agents import Runner

from api.services.csv_processor import CSVProcessor
from api.services.logging_config import setup_run_logger, RunLogger
from research_agents.brand_agents import brand_detection_agent
from research_agents.categorization_agent import categorization_agent
from research_agents.irrelevant_agent import irrelevant_agent
from research_agents.helper_methods import scrape_amazon_listing
from research_agents.prompts import (
    BRAND_DETECTION_PROMPT_TEMPLATE,
    KEYWORD_CATEGORIZATION_PROMPT_TEMPLATE,
    IRRELEVANT_VALIDATION_PROMPT_TEMPLATE
)

logger = logging.getLogger(__name__)

class ResearchPipeline:
    """Complete pipeline for Amazon product research"""
    
    def __init__(self):
        self.csv_processor = CSVProcessor()
        self.run_logger: Optional[RunLogger] = None
    
    async def run_complete_pipeline(
        self,
        design_csv_content: bytes,
        revenue_csv_content: bytes,
        asin_or_url: str,
        marketplace: str = "US",
        use_mock_scraper: bool = False,
        progress_callback=None,
        request_id: str = None
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
        # Setup run-specific logger
        if request_id:
            self.run_logger = setup_run_logger(request_id)
            run_log = self.run_logger.logger
        else:
            run_log = logger
        
        try:
            run_log.info(f"Starting pipeline for ASIN: {asin_or_url}, Marketplace: {marketplace}")
            
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
            
            # If deduplication removes everything, skip design processing (all keywords already in revenue)
            if len(design_dedup) == 0 and len(design_rows) > 0:
                run_log.info("All design keywords already present in revenue CSV, skipping design processing")
                design_dedup = []
            
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
            
            # Step 5.5: Brand Detection (33-36%)
            if progress_callback:
                await progress_callback(33, "Detecting branded keywords...")
            logger.info("Step 5.5: Brand detection")
            
            # Get all unique keywords from filtered rows
            all_keywords = list(set([row['Keyword Phrase'] for row in (design_relevancy or []) + (revenue_relevancy or [])]))
            logger.info(f"Total keywords before brand filtering: {len(all_keywords)}")
            
            # Brand Detection
            branded_keywords, non_branded_keywords = await self._detect_brands(all_keywords, progress_callback)
            
            logger.info(f"Brand filtering complete: {len(branded_keywords)} branded, {len(non_branded_keywords)} non-branded")
            
            # Save brand classifications
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            brand_classifications = []
            
            for kw in branded_keywords:
                brand_classifications.append({
                    'keyword': kw,
                    'status': 'Branded',
                    'reasoning': 'Contains brand name'
                })
            
            for kw in non_branded_keywords:
                brand_classifications.append({
                    'keyword': kw,
                    'status': 'Non-Branded',
                    'reasoning': 'Generic term'
                })
            
            if brand_classifications:
                self.csv_processor.save_to_csv(brand_classifications, f"brand_classification_{timestamp}.csv")
                logger.info(f"Saved brand classifications: {len(brand_classifications)} total keywords")
            
            # Separate branded and non-branded rows
            non_branded_set = set(kw.lower() for kw in non_branded_keywords)
            branded_set = set(kw.lower() for kw in branded_keywords)
            
            # Keep all rows but mark which are for evaluation
            all_design_rows = design_relevancy or []
            all_revenue_rows = revenue_relevancy or []
            
            # Filter to only non-branded for AI evaluation
            design_relevancy = [row for row in all_design_rows if row['Keyword Phrase'].lower() in non_branded_set]
            revenue_relevancy = [row for row in all_revenue_rows if row['Keyword Phrase'].lower() in non_branded_set]
            
            # Keep branded rows for final display (without AI evaluation)
            branded_design_rows = [row for row in all_design_rows if row['Keyword Phrase'].lower() in branded_set]
            branded_revenue_rows = [row for row in all_revenue_rows if row['Keyword Phrase'].lower() in branded_set]
            
            logger.info(f"After brand filtering: {len(design_relevancy)} non-branded rows for evaluation, {len(branded_design_rows) + len(branded_revenue_rows)} branded rows kept for display")
            
            # Step 6: Scrape Amazon product (35-45%)
            if progress_callback:
                await progress_callback(35, "Scraping Amazon product...")
            logger.info(f"Step 6: Scraping Amazon listing: {asin_or_url}")
            scraped_result = scrape_amazon_listing(asin_or_url, marketplace, use_mock=use_mock_scraper)
            
            if not scraped_result.get("success"):
                error_msg = scraped_result.get('error', 'Unknown error')
                
                # Check if it's a CAPTCHA error
                if "CAPTCHA" in error_msg:
                    run_log.error(f"❌ Amazon CAPTCHA detected. This is a common anti-bot protection.")
                    return {
                        "success": False,
                        "error": "Amazon CAPTCHA detected. Please try one of these solutions:\n\n"
                                "1. Use Mock Mode: Check 'Use mock scraper' checkbox to test with sample data\n"
                                "2. Wait and Retry: Wait 5-10 minutes and try again\n"
                                "3. Use VPN: Try connecting through a VPN\n"
                                "4. Different Network: Try from a different network/location\n\n"
                                "Note: Amazon actively blocks automated scraping. This is expected behavior.",
                        "scraped_data": scraped_result,
                        "log_file": self.run_logger.get_log_file_path() if self.run_logger else None
                    }
                
                run_log.error(f"❌ Scraping failed: {error_msg}")
                return {
                    "success": False,
                    "error": f"Scraping failed: {error_msg}",
                    "scraped_data": scraped_result,
                    "log_file": self.run_logger.get_log_file_path() if self.run_logger else None
                }
            
            scraped_data = scraped_result.get("data", {})
            logger.info("✅ Scraping successful")
            
            # Save scraped data to JSON file for inspection
            try:
                results_dir = Path("results")
                results_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                asin_clean = asin_or_url.replace('/', '_').replace(':', '_').replace('?', '_')[:50]
                scraped_json_file = results_dir / f"scraped_data_{asin_clean}_{timestamp}.json"
                
                with open(scraped_json_file, 'w', encoding='utf-8') as f:
                    json.dump(scraped_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"📄 Scraped data saved to: {scraped_json_file}")
            except Exception as e:
                logger.warning(f"⚠️  Could not save scraped data: {str(e)}")
            
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
            
            # Step 8: Extract title and bullets from scraped data (60%)
            if progress_callback:
                await progress_callback(60, "Extracting product title and bullets...")
            logger.info("Step 8: Extracting product title and bullets")
            
            # Extract title
            product_title = scraped_data.get("title", "")
            if not product_title:
                # Try from elements
                elements = scraped_data.get("elements", {})
                title_data = elements.get("productTitle", {})
                if title_data:
                    title_text = title_data.get("text", "")
                    product_title = title_text[0] if isinstance(title_text, list) else str(title_text)
            
            # Extract bullets - try multiple locations
            product_bullets = []
            elements = scraped_data.get("elements", {})
            
            # Try location 1: feature-bullets
            bullets_data = elements.get("feature-bullets", {})
            if bullets_data:
                product_bullets = bullets_data.get("bullets", [])
            
            # Try location 2: productFactsDesktopExpander (About this item)
            if not product_bullets:
                facts_data = elements.get("productFactsDesktopExpander", {})
                if facts_data:
                    product_bullets = facts_data.get("bullets", []) or facts_data.get("items", [])
            
            # Try location 3: Direct bullets key
            if not product_bullets:
                product_bullets = scraped_data.get("bullets", []) or scraped_data.get("features", [])
            
            # Try location 4: feature_bullets
            if not product_bullets:
                product_bullets = scraped_data.get("feature_bullets", [])
            
            logger.info(f"✅ Extracted title and {len(product_bullets)} bullets")
            if not product_bullets:
                logger.warning("⚠️  No bullets found in scraped data. Check scraped_data JSON file for structure.")
            
            # Create product summary for display
            product_summary = [f"Title: {product_title}"] + [f"• {bullet}" for bullet in product_bullets[:5]]
            
            # Step 9: Categorize keywords (70-95%)
            if progress_callback:
                await progress_callback(70, "Categorizing keywords...")
            run_log.info("Step 9: Categorizing keywords into irrelevant/outlier/relevant/design-specific")
            
            # Categorize in batches with max 10 concurrent calls
            categorization_batch_size = 5
            max_concurrent_cat = 10
            categorization_batches = [keywords_list[i:i + categorization_batch_size] for i in range(0, len(keywords_list), categorization_batch_size)]
            run_log.info(f"Created {len(categorization_batches)} batches for categorization, max {max_concurrent_cat} concurrent calls")
            
            # Semaphore to limit concurrent API calls
            cat_semaphore = asyncio.Semaphore(max_concurrent_cat)
            completed_cat_batches = 0
            
            async def categorize_batch(batch):
                nonlocal completed_cat_batches
                async with cat_semaphore:
                    try:
                        cat_prompt = KEYWORD_CATEGORIZATION_PROMPT_TEMPLATE.format(
                            keywords_json=json.dumps(batch, indent=2)
                        )
                        
                        cat_result = await Runner.run(categorization_agent, cat_prompt)
                        cat_raw = getattr(cat_result, "final_output", None)
                        cat_structured = self._extract_structured_output(cat_raw)
                        
                        # Update progress for each completed batch
                        completed_cat_batches += 1
                        if progress_callback:
                            progress_percent = 70 + (completed_cat_batches / len(categorization_batches)) * 25  # 70-95%
                            await progress_callback(progress_percent, f"Categorizing keywords ({completed_cat_batches}/{len(categorization_batches)} batches)...")
                        
                        return cat_structured.get("categorizations", [])
                    except Exception as e:
                        run_log.error(f"Error categorizing batch: {str(e)}")
                        completed_cat_batches += 1
                        return []
            
            cat_tasks = [categorize_batch(batch) for batch in categorization_batches]
            cat_batch_results = await asyncio.gather(*cat_tasks)
            
            # Flatten categorization results
            keyword_evaluations = [cat for batch in cat_batch_results for cat in batch if cat]
            run_log.info(f"✅ Categorization complete: {len(keyword_evaluations)} categorizations")
            
            # Step 7: Irrelevant Validation (95-98%)
            if progress_callback:
                await progress_callback(95, "Validating keywords against product...")
            
            logger.info("Step 7: Irrelevant validation")
            run_log.info("Step 7: Validating categorized keywords against product title and bullets")
            
            # Prepare categorized keywords for validation
            categorized_keywords_for_validation = [
                {
                    'keyword': cat.get('keyword'),
                    'category': cat.get('category'),
                    'reasoning': cat.get('reasoning', '')
                }
                for cat in keyword_evaluations
            ]
            
            # Run irrelevant validation in batches (smaller batches to avoid token limits)
            validation_batch_size = 25
            validation_batches = [categorized_keywords_for_validation[i:i + validation_batch_size] 
                                 for i in range(0, len(categorized_keywords_for_validation), validation_batch_size)]
            run_log.info(f"Created {len(validation_batches)} batches for irrelevant validation")
            
            max_concurrent_val = 10
            val_semaphore = asyncio.Semaphore(max_concurrent_val)
            completed_val_batches = 0
            
            async def validate_batch(batch):
                nonlocal completed_val_batches
                async with val_semaphore:
                    try:
                        val_prompt = IRRELEVANT_VALIDATION_PROMPT_TEMPLATE.format(
                            product_title=product_title,
                            product_bullets_json=json.dumps(product_bullets, indent=2),
                            keywords_json=json.dumps(batch, indent=2)
                        )
                        
                        val_result = await Runner.run(irrelevant_agent, val_prompt)
                        val_raw = getattr(val_result, "final_output", None)
                        val_structured = self._extract_structured_output(val_raw)
                        
                        completed_val_batches += 1
                        if progress_callback:
                            progress_percent = 95 + (completed_val_batches / len(validation_batches)) * 3  # 95-98%
                            await progress_callback(progress_percent, f"Validating keywords ({completed_val_batches}/{len(validation_batches)} batches)...")
                        
                        checks = val_structured.get("irrelevance_checks", [])
                        if checks:
                            run_log.info(f"Batch validation successful: {len(checks)} keywords validated")
                        return checks
                    except Exception as e:
                        run_log.error(f"Error validating batch: {str(e)}")
                        run_log.warning(f"Skipping validation for this batch - keeping original categorizations")
                        completed_val_batches += 1
                        return []
            
            val_tasks = [validate_batch(batch) for batch in validation_batches]
            val_batch_results = await asyncio.gather(*val_tasks)
            
            # Flatten validation results
            irrelevance_checks = [check for batch in val_batch_results for check in batch if check]
            run_log.info(f"✅ Validation complete: {len(irrelevance_checks)} checks")
            
            # Create lookup for irrelevant keywords
            irrelevant_lookup = {
                check.get('keyword', '').lower(): check 
                for check in irrelevance_checks 
                if check.get('is_irrelevant', False)
            }
            
            # Store irrelevant keywords (like branded keywords)
            irrelevant_keywords = []
            non_irrelevant_keywords = []
            
            for check in irrelevance_checks:
                keyword = check.get('keyword', '')
                if check.get('is_irrelevant', False):
                    irrelevant_keywords.append(keyword)
                else:
                    non_irrelevant_keywords.append(keyword)
            
            run_log.info(f"Validation results: {len(irrelevant_keywords)} irrelevant, {len(non_irrelevant_keywords)} valid")
            
            # Save irrelevant classifications
            if irrelevance_checks:
                irrelevant_classifications = []
                for check in irrelevance_checks:
                    irrelevant_classifications.append({
                        'keyword': check.get('keyword', ''),
                        'status': 'Irrelevant' if check.get('is_irrelevant', False) else 'Valid',
                        'reasoning': check.get('reasoning', '')
                    })
                
                results_dir = Path("results")
                results_dir.mkdir(exist_ok=True)
                irrelevant_csv_path = results_dir / f"irrelevant_classification_{timestamp}.csv"
                with open(irrelevant_csv_path, 'w', newline='', encoding='utf-8') as f:
                    if irrelevant_classifications:
                        writer = csv.DictWriter(f, fieldnames=['keyword', 'status', 'reasoning'])
                        writer.writeheader()
                        writer.writerows(irrelevant_classifications)
                logger.info(f"Saved irrelevant classifications: {len(irrelevant_classifications)} total keywords")
            
            # Overwrite categories for irrelevant keywords
            overwritten_count = 0
            for cat in keyword_evaluations:
                keyword_lower = cat.get('keyword', '').lower()
                if keyword_lower in irrelevant_lookup:
                    irrelevant_info = irrelevant_lookup[keyword_lower]
                    original_category = cat.get('category', 'unknown')
                    # Overwrite category and reasoning
                    cat['category'] = 'irrelevant'
                    cat['reasoning'] = irrelevant_info.get('reasoning', 'Does not match product')
                    run_log.info(f"Overwritten '{cat.get('keyword')}' from {original_category.upper()} to IRRELEVANT: {cat['reasoning']}")
                    overwritten_count += 1
            
            run_log.info(f"✅ Categories updated with validation results: {overwritten_count} keywords overwritten to IRRELEVANT")
            
            # Map category to relevance_score using Python function
            for cat in keyword_evaluations:
                category = cat.get('category', 'relevant')
                
                # Map category to score range
                if category == 'irrelevant':
                    # Irrelevant: 1-4 (use 3 as default)
                    cat['relevance_score'] = 3
                elif category == 'outlier':
                    # Outlier: 5-6 (use 5 as default)
                    cat['relevance_score'] = 5
                elif category == 'relevant':
                    # Relevant: 7-8 (use 8 as default)
                    cat['relevance_score'] = 8
                elif category == 'design_specific':
                    # Design-specific: 9-10 (use 10 as default)
                    cat['relevance_score'] = 10
                elif category == 'branded':
                    # Branded: 2 (lowest score)
                    cat['relevance_score'] = 2
                else:
                    # Default to relevant
                    cat['relevance_score'] = 7
            
            run_log.info(f"✅ Relevance scores mapped from categories")
            
            # Check if we got any categorizations
            if not keyword_evaluations:
                run_log.warning("⚠️  No keyword categorizations returned from AI")
                return {
                    "success": True,
                    "product_summary": product_summary,
                    "keyword_evaluations": [],
                    "scraped_data": scraped_data,
                    "csv_filename": "",
                    "log_file": self.run_logger.get_log_file_path() if self.run_logger else None,
                    "metadata": {
                        "asin_or_url": asin_or_url,
                        "marketplace": marketplace,
                        "top_10_roots": top_10_roots,
                        "design_rows_original": len(design_rows),
                        "revenue_rows_original": len(revenue_rows),
                        "design_rows_deduped": len(design_dedup),
                        "branded_keywords_removed": len(branded_keywords),
                        "non_branded_keywords_kept": len(non_branded_keywords),
                        "irrelevant_keywords_found": 0,
                        "valid_keywords_kept": 0,
                        "design_rows_filtered": len(design_relevancy) if design_relevancy else 0,
                        "revenue_rows_filtered": len(revenue_relevancy) if revenue_relevancy else 0,
                        "keywords_evaluated": 0,
                        "keywords_final": 0,
                        "batches_processed": len(categorization_batches),
                        "warning": "AI categorization returned no results"
                    }
                }
            
            if progress_callback:
                await progress_callback(98, "Validation complete, finalizing results...")
            
            # Sort by category_score descending
            keyword_evaluations.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # Merge with original row data and add brand status
            merged_evaluations = []
            
            # Create a lookup for brand status and reasoning
            brand_status_lookup = {item['keyword'].lower(): item for item in brand_classifications}
            
            # Add evaluated non-branded keywords
            for eval in keyword_evaluations:
                try:
                    matching_row = next(
                        (row for row in filtered_rows 
                         if row.get('Keyword Phrase', '').strip().lower() == eval.get('keyword', '').strip().lower()), 
                        None
                    )
                    if matching_row:
                        merged = {**eval, **matching_row}
                        # Add brand status
                        keyword_lower = eval.get('keyword', '').strip().lower()
                        brand_info = brand_status_lookup.get(keyword_lower, {})
                        merged['brand_status'] = brand_info.get('status', 'Non-Branded')
                        merged['brand_reasoning'] = brand_info.get('reasoning', 'N/A')
                        merged_evaluations.append(merged)
                except Exception as e:
                    logger.error(f"Error merging evaluation: {str(e)}")
                    continue
            
            # Add branded keywords (not evaluated for relevance)
            branded_rows = branded_design_rows + branded_revenue_rows
            for row in branded_rows:
                try:
                    keyword = row.get('Keyword Phrase', '').strip()
                    keyword_lower = keyword.lower()
                    brand_info = brand_status_lookup.get(keyword_lower, {})
                    
                    # Create entry for branded keyword (no AI evaluation or categorization)
                    branded_entry = {
                        'keyword': keyword,
                        'rationale': 'Branded keyword - not evaluated',
                        'category': 'branded',
                        'relevance_score': 2,  # Branded keywords get score of 2
                        'language_tag': None,
                        'category_reasoning': 'Branded keyword',
                        'brand_status': 'Branded',
                        'brand_reasoning': brand_info.get('reasoning', 'Contains brand name'),
                        **row  # Include all original CSV data
                    }
                    merged_evaluations.append(branded_entry)
                except Exception as e:
                    logger.error(f"Error adding branded keyword: {str(e)}")
                    continue
            
            logger.info(f"Total results: {len(merged_evaluations)} ({len(keyword_evaluations)} evaluated + {len(branded_rows)} branded)")
            
            # Filter to relevance_score >= 5 (but keep branded and irrelevant keywords for visibility)
            merged_evaluations = [
                row for row in merged_evaluations 
                if row.get('relevance_score', 0) >= 5 
                or row.get('brand_status') == 'Branded'
                or row.get('category', '').lower() == 'irrelevant'
            ]
            
            # Sort by search volume descending
            try:
                merged_evaluations.sort(
                    key=lambda x: int(x.get('Search Volume', 0)) if x.get('Search Volume') else 0, 
                    reverse=True
                )
            except Exception as e:
                logger.error(f"Error sorting by search volume: {str(e)}")
            
            logger.info(f"✅ Pipeline complete: {len(merged_evaluations)} final evaluations")
            
            # Restructure output with specific fields in specific order
            final_output = []
            for row in merged_evaluations:
                # Determine category (add "branded" as a category option)
                if row.get('brand_status') == 'Branded':
                    category = 'branded'
                else:
                    category = row.get('category', 'relevant')
                
                # Build the output row with exact field order
                language_tag = row.get('language_tag')
                # Convert None to empty string for tag
                tag_value = language_tag if language_tag and language_tag != 'None' else ''
                
                output_row = {
                    'keyword': row.get('keyword') or row.get('Keyword Phrase', ''),
                    'category': category,
                    'relevance_score': row.get('relevance_score', 0),  # This is category_score from categorization agent
                    'relevance_rationale': row.get('reasoning', ''),  # This is reasoning from categorization agent
                    'tag': tag_value,
                    'category_rationale': row.get('reasoning', ''),  # Same as relevance_rationale
                    'search_volume': row.get('Search Volume', ''),
                    'title_density': row.get('Title Density', ''),
                    'Position (Rank)': row.get('Position (Rank)', ''),
                }
                
                # Add all competitor columns (B0* ASINs)
                for key in row.keys():
                    if key.startswith('B0'):
                        output_row[key] = row.get(key, '')
                
                # Add competitor_relevance_formula (Relevance column)
                output_row['competitor_relevance_formula'] = row.get('Relevance', '')
                
                # Add brand_reasoning
                output_row['brand_reasoning'] = row.get('brand_reasoning', '')
                
                final_output.append(output_row)
            
            merged_evaluations = final_output
            
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
                        "branded_keywords_removed": len(final_branded) if 'final_branded' in locals() else 0,
                        "non_branded_keywords_kept": len(final_non_branded) if 'final_non_branded' in locals() else 0,
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
            
            result = {
                "success": True,
                "product_summary": product_summary,
                "keyword_evaluations": merged_evaluations,
                "scraped_data": scraped_data,
                "csv_filename": csv_filename,
                "log_file": self.run_logger.get_log_file_path() if self.run_logger else None,
                "metadata": {
                    "asin_or_url": asin_or_url,
                    "marketplace": marketplace,
                    "top_10_roots": top_10_roots,
                    "design_rows_original": len(design_rows),
                    "revenue_rows_original": len(revenue_rows),
                    "design_rows_deduped": len(design_dedup),
                    "branded_keywords_removed": len(branded_keywords),
                    "non_branded_keywords_kept": len(non_branded_keywords),
                    "irrelevant_keywords_found": len(irrelevant_keywords),
                    "valid_keywords_kept": len(non_irrelevant_keywords),
                    "design_rows_filtered": len(design_relevancy),
                    "revenue_rows_filtered": len(revenue_relevancy),
                    "keywords_categorized": len(keyword_evaluations),
                    "keywords_final": len(merged_evaluations),
                    "batches_processed": len(categorization_batches)
                }
            }
            
            run_log.info(f"Pipeline completed successfully. Log file: {result['log_file']}")
            return result
            
        except Exception as e:
            run_log.error(f"Pipeline error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "log_file": self.run_logger.get_log_file_path() if self.run_logger else None
            }
        finally:
            # Cleanup logger
            if self.run_logger:
                self.run_logger.cleanup()
    
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
    
    async def _detect_brands(self, keywords: List[str], progress_callback=None) -> tuple[List[str], List[str]]:
        """
        Brand Detection with controlled concurrency
        Returns: (branded_keywords, non_branded_keywords)
        """
        try:
            # Process in batches with max 10 concurrent API calls
            batch_size = 50
            max_concurrent = 10
            
            # Create batches
            batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
            total_batches = len(batches)
            logger.info(f"Brand detection: {len(keywords)} keywords in {total_batches} batches, max {max_concurrent} concurrent calls")
            
            # Semaphore to limit concurrent API calls
            semaphore = asyncio.Semaphore(max_concurrent)
            
            all_branded = []
            all_non_branded = []
            completed_batches = 0
            
            async def process_batch(batch_index, batch):
                nonlocal completed_batches
                async with semaphore:
                    try:
                        prompt = BRAND_DETECTION_PROMPT_TEMPLATE.format(
                            keywords_json=json.dumps(batch, indent=2)
                        )
                        
                        result = await Runner.run(brand_detection_agent, prompt)
                        detection_raw = getattr(result, "final_output", None)
                        detection_structured = self._extract_structured_output(detection_raw)
                        
                        branded_batch = detection_structured.get("branded_keywords", [])
                        non_branded_batch = detection_structured.get("non_branded_keywords", [])
                        
                        completed_batches += 1
                        logger.info(f"Brand detection batch {batch_index + 1}/{total_batches}: {len(branded_batch)} branded, {len(non_branded_batch)} non-branded")
                        
                        return branded_batch, non_branded_batch
                    
                    except Exception as e:
                        logger.error(f"Error in brand detection batch {batch_index + 1}: {str(e)}")
                        completed_batches += 1
                        # On error, treat batch as non-branded to not lose data
                        return [], batch
            
            # Process all batches with controlled concurrency
            tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
            results = await asyncio.gather(*tasks)
            
            # Collect results
            for branded_batch, non_branded_batch in results:
                all_branded.extend(branded_batch)
                all_non_branded.extend(non_branded_batch)
            
            logger.info(f"Brand detection complete: {len(all_branded)} branded, {len(all_non_branded)} non-branded")
            
            return all_branded, all_non_branded
            
        except Exception as e:
            logger.error(f"Error in brand detection: {str(e)}")
            # On error, treat all as non-branded to not lose data
            return [], keywords
    
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
