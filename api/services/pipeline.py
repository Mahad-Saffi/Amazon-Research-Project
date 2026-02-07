"""
Simplified research pipeline - orchestrates services
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
import csv

from api.services.csv_processor import CSVProcessor
from api.services.logging_config import setup_run_logger, RunLogger
from api.services.brand_service import BrandService
from api.services.categorization_service import CategorizationService
from api.services.scraper_service import ScraperService
from api.services.validation_service import ValidationService
from api.services.verification_service import VerificationService
from api.services.enhanced_categorization_service import EnhancedCategorizationService
from api.services.direct_verification_service import DirectVerificationService

logger = logging.getLogger(__name__)

class ResearchPipeline:
    """Simplified pipeline orchestrating specialized services"""
    
    def __init__(self):
        self.csv_processor = CSVProcessor()
        self.brand_service = BrandService()
        self.categorization_service = CategorizationService()
        self.scraper_service = ScraperService()
        self.validation_service = ValidationService()
        self.verification_service = VerificationService()
        self.enhanced_categorization_service = EnhancedCategorizationService()
        self.direct_verification_service = DirectVerificationService()
        self.run_logger: Optional[RunLogger] = None
    
    async def run_complete_pipeline(
        self,
        design_csv_content: bytes,
        revenue_csv_content: bytes,
        asin_or_url: str,
        marketplace: str = "US",
        use_mock_scraper: bool = False,
        use_direct_verification: bool = False,
        include_seo_optimization: bool = True,  # New parameter
        progress_callback=None,
        request_id: str = None
    ) -> Dict[str, Any]:
        """Run complete research pipeline"""
        
        # Setup logger
        if request_id:
            self.run_logger = setup_run_logger(request_id)
            run_log = self.run_logger.logger
        else:
            run_log = logger
        
        try:
            run_log.info(f"Pipeline started: {asin_or_url}")
            
            # Step 1-4: CSV Processing (10-25%)
            if progress_callback:
                await progress_callback(10, "Processing CSV files...")
            
            design_rows, revenue_rows = self._process_csvs(
                design_csv_content, 
                revenue_csv_content
            )
            
            if not design_rows and not revenue_rows:
                return self._error_response("No valid keywords found in CSV files")
            
            # Filter out keywords with 0 search volume
            design_rows = [row for row in design_rows 
                          if row.get('Search Volume') and int(row.get('Search Volume', 0)) > 0]
            revenue_rows = [row for row in revenue_rows 
                           if row.get('Search Volume') and int(row.get('Search Volume', 0)) > 0]
            
            run_log.info(f"After filtering 0 volume: {len(design_rows)} design, {len(revenue_rows)} revenue")
            
            if not design_rows and not revenue_rows:
                return self._error_response("No keywords with search volume > 0 found")
            
            # Step 5: Extract root keywords (28-32%)
            if progress_callback:
                await progress_callback(28, "Extracting root keywords...")
            
            root_keywords = self.csv_processor.extract_root_keywords(design_rows, revenue_rows)
            top_10_roots = [rk['keyword'] for rk in root_keywords[:10]]
            logger.info(f"Top 10 roots: {top_10_roots}")
            
            # Step 5.5: Brand Detection (33-36%)
            if progress_callback:
                await progress_callback(33, "Detecting branded keywords...")
            
            all_keywords = list(set([row['Keyword Phrase'] for row in design_rows + revenue_rows]))
            branded_kws, non_branded_kws = await self.brand_service.detect_brands(all_keywords)
            
            # Filter to non-branded for evaluation
            non_branded_set = set(kw.lower() for kw in non_branded_kws)
            filtered_rows = [row for row in design_rows + revenue_rows 
                           if row['Keyword Phrase'].lower() in non_branded_set]
            
            # Keep branded rows for final output
            branded_set = set(kw.lower() for kw in branded_kws)
            branded_rows = [row for row in design_rows + revenue_rows 
                          if row['Keyword Phrase'].lower() in branded_set]
            
            # Step 6: Scrape Amazon (35-45%)
            if progress_callback:
                await progress_callback(35, "Scraping Amazon product...")
            
            scrape_result = self.scraper_service.scrape_product(
                asin_or_url, marketplace, use_mock_scraper
            )
            
            if not scrape_result.get("success"):
                return self._handle_scrape_error(scrape_result)
            
            product_title = scrape_result["title"]
            product_bullets = scrape_result["bullets"]
            scraped_data = scrape_result["data"]
            
            if progress_callback:
                await progress_callback(45, "Product data retrieved")
            
            # Step 7: Filter by top 10 roots
            keywords_to_evaluate = [
                row['Keyword Phrase'] for row in filtered_rows
                if any(root.lower() in row['Keyword Phrase'].lower() for root in top_10_roots)
            ]
            
            if not keywords_to_evaluate:
                return self._success_response([], product_title, product_bullets, scraped_data, 
                                             asin_or_url, marketplace, top_10_roots)
            
            # Step 8-9: Categorize keywords (70-95%)
            if progress_callback:
                await progress_callback(70, "Categorizing keywords...")
            
            categorizations = await self.categorization_service.categorize_keywords(
                keywords_to_evaluate,
                progress_callback=progress_callback
            )
            
            # Step 10: Validate irrelevant keywords (95-98%)
            if progress_callback:
                await progress_callback(95, "Validating keywords...")
            
            categorized_for_validation = [
                {'keyword': cat.get('keyword'), 'category': cat.get('category'), 
                 'reasoning': cat.get('reasoning', '')}
                for cat in categorizations
            ]
            
            validation_checks = await self.validation_service.validate_keywords(
                categorized_for_validation,
                product_title,
                product_bullets,
                progress_callback=progress_callback
            )
            
            # Update categories based on validation
            categorizations = self._apply_validation(categorizations, validation_checks)
            
            # Choose verification method based on toggle
            if use_direct_verification:
                # Method 2: Direct Verification
                # Scrape all irrelevant keywords directly and verify against our product
                if progress_callback:
                    await progress_callback(95, "Direct verification of irrelevant keywords...")
                
                run_log.info("Using DIRECT verification method")
                
                # Merge with CSV data first
                temp_merged = self._merge_with_csv_data(categorizations, filtered_rows)
                
                # Direct verification
                verification_results = await self.direct_verification_service.verify_irrelevant_keywords(
                    temp_merged,
                    product_title,
                    product_bullets,
                    progress_callback=progress_callback
                )
                
                # Apply results
                if verification_results:
                    self.direct_verification_service.apply_verification_results(
                        categorizations,
                        verification_results
                    )
            else:
                # Method 1: Enhanced Categorization + Verification (Original)
                # Step 10.5: Enhanced Irrelevant Categorization (98%)
                if progress_callback:
                    await progress_callback(98, "Analyzing market demand...")
                
                run_log.info("Using ENHANCED categorization + verification method")
                
                # Merge with CSV data first to get search volumes
                temp_merged = self._merge_with_csv_data(categorizations, filtered_rows)
                
                # Run enhanced categorization
                enhanced_categories = self.enhanced_categorization_service.categorize_irrelevant_keywords(
                    temp_merged
                )
                
                # Apply enhanced categories
                if enhanced_categories:
                    self.enhanced_categorization_service.apply_enhanced_categories(
                        categorizations,
                        enhanced_categories
                    )
                
                # Step 11: Verify competitor_relevant keywords (98-99%)
                competitor_kws = [cat for cat in categorizations 
                                if cat.get('category') == 'competitor_relevant']
                
                if competitor_kws:
                    verification_results = await self.verification_service.verify_competitor_keywords(
                        competitor_kws,
                        product_title,
                        product_bullets,
                        progress_callback=progress_callback
                    )
                    
                    categorizations = self._apply_verification(categorizations, verification_results)
            
            # Map categories to relevance scores
            for cat in categorizations:
                cat['relevance_score'] = self._map_category_to_score(cat.get('category', 'relevant'))
            
            # Step 12: Merge and finalize (99-100%)
            if progress_callback:
                await progress_callback(99, "Finalizing results...")
            
            final_results = self._merge_and_finalize(
                categorizations,
                filtered_rows,
                branded_rows,
                branded_kws,
                non_branded_kws
            )
            
            # Save results
            csv_filename = self._save_results(final_results, asin_or_url)
            
            if progress_callback:
                await progress_callback(100, "Complete!")
            
            run_log.info(f"Pipeline complete: {len(final_results)} results")
            
            # Optional: Run SEO optimization
            seo_optimization_result = None
            if include_seo_optimization and product_title and product_bullets:
                try:
                    if progress_callback:
                        await progress_callback(100, "Running SEO optimization...")
                    
                    run_log.info("Running SEO optimization...")
                    
                    from api.services.seo_optimization_service import SEOOptimizationService
                    seo_service = SEOOptimizationService()
                    
                    seo_optimization_result = await seo_service.optimize_listing(
                        current_title=product_title,
                        current_bullets=product_bullets,
                        keyword_evaluations=final_results,
                        product_info={
                            'asin': asin_or_url,
                            'marketplace': marketplace
                        }
                    )
                    
                    run_log.info("SEO optimization complete")
                except Exception as e:
                    run_log.error(f"SEO optimization failed: {str(e)}")
                    seo_optimization_result = {
                        'success': False,
                        'error': str(e)
                    }
            
            return {
                "success": True,
                "product_summary": self._create_summary(product_title, product_bullets),
                "keyword_evaluations": final_results,
                "scraped_data": scraped_data,
                "csv_filename": csv_filename,
                "log_file": self.run_logger.get_log_file_path() if self.run_logger else None,
                "seo_optimization": seo_optimization_result,  # New field
                "metadata": self._create_metadata(
                    asin_or_url, marketplace, top_10_roots,
                    len(design_rows), len(revenue_rows),
                    len(branded_kws), len(non_branded_kws),
                    len(categorizations), len(final_results)
                )
            }
            
        except Exception as e:
            run_log.error(f"Pipeline error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "log_file": self.run_logger.get_log_file_path() if self.run_logger else None
            }
        finally:
            if self.run_logger:
                self.run_logger.cleanup()
    
    def _process_csvs(self, design_content: bytes, revenue_content: bytes):
        """Process CSV files through dedup, filter, relevancy"""
        design_rows = self.csv_processor.parse_csv_content(design_content)
        revenue_rows = self.csv_processor.parse_csv_content(revenue_content)
        
        design_dedup = self.csv_processor.deduplicate_design(design_rows, revenue_rows)
        
        design_filtered = self.csv_processor.filter_columns(design_dedup) if design_dedup else []
        revenue_filtered = self.csv_processor.filter_columns(revenue_rows) if revenue_rows else []
        
        design_relevancy = self.csv_processor.add_relevancy(design_filtered) if design_filtered else []
        revenue_relevancy = self.csv_processor.add_relevancy(revenue_filtered) if revenue_filtered else []
        
        return design_relevancy, revenue_relevancy
    
    def _apply_validation(self, categorizations, validation_checks):
        """Apply validation results to categorizations"""
        irrelevant_lookup = {
            check.get('keyword', '').lower(): check 
            for check in validation_checks 
            if check.get('is_irrelevant', False)
        }
        
        for cat in categorizations:
            keyword_lower = cat.get('keyword', '').lower()
            if keyword_lower in irrelevant_lookup:
                irrelevant_info = irrelevant_lookup[keyword_lower]
                cat['category'] = 'irrelevant'
                cat['reasoning'] = irrelevant_info.get('reasoning', 'Does not match product')
        
        return categorizations
    
    def _merge_with_csv_data(self, categorizations, filtered_rows):
        """Merge categorizations with CSV data to get search volumes"""
        merged = []
        for cat in categorizations:
            matching_row = next(
                (row for row in filtered_rows 
                 if row.get('Keyword Phrase', '').strip().lower() == cat.get('keyword', '').strip().lower()),
                None
            )
            if matching_row:
                merged.append({**cat, **matching_row})
            else:
                merged.append(cat)
        return merged
    
    def _apply_verification(self, categorizations, verification_results):
        """Apply verification results to categorizations"""
        for cat in categorizations:
            keyword = cat.get('keyword')
            if keyword in verification_results:
                result = verification_results[keyword]
                if result['verdict'] == 'relevant':
                    cat['category'] = 'relevant'
                    cat['relevance_score'] = 8
                    cat['reasoning'] = f"Verified: {result['reasoning']}"
                else:
                    cat['category'] = 'irrelevant'
                    cat['relevance_score'] = 3
                    cat['reasoning'] = f"Verified: {result['reasoning']}"
        
        return categorizations
    
    def _map_category_to_score(self, category: str) -> int:
        """Map category to relevance score"""
        mapping = {
            'irrelevant': 3,
            'competitor_relevant': 4,
            'outlier': 5,
            'relevant': 8,
            'design_specific': 10,
            'branded': 2
        }
        return mapping.get(category, 7)
    
    def _merge_and_finalize(self, categorizations, filtered_rows, branded_rows, 
                           branded_kws, non_branded_kws):
        """Merge categorizations with CSV data and add branded keywords"""
        brand_lookup = {}
        for kw in branded_kws:
            brand_lookup[kw.lower()] = {'status': 'Branded', 'reasoning': 'Contains brand name'}
        for kw in non_branded_kws:
            brand_lookup[kw.lower()] = {'status': 'Non-Branded', 'reasoning': 'Generic term'}
        
        merged = []
        
        # Add evaluated keywords
        for cat in categorizations:
            matching_row = next(
                (row for row in filtered_rows 
                 if row.get('Keyword Phrase', '').strip().lower() == cat.get('keyword', '').strip().lower()),
                None
            )
            if matching_row:
                brand_info = brand_lookup.get(cat.get('keyword', '').lower(), {})
                merged.append({
                    **cat,
                    **matching_row,
                    'brand_status': brand_info.get('status', 'Non-Branded'),
                    'brand_reasoning': brand_info.get('reasoning', 'N/A')
                })
        
        # Add branded keywords
        for row in branded_rows:
            keyword = row.get('Keyword Phrase', '').strip()
            brand_info = brand_lookup.get(keyword.lower(), {})
            merged.append({
                'keyword': keyword,
                'category': 'branded',
                'relevance_score': 2,
                'reasoning': 'Branded keyword - not evaluated',
                'brand_status': 'Branded',
                'brand_reasoning': brand_info.get('reasoning', 'Contains brand name'),
                **row
            })
        
        # Filter and sort
        merged = [row for row in merged if row.get('relevance_score', 0) >= 5 
                 or row.get('category') in ['branded', 'irrelevant', 'competitor_relevant']]
        
        merged.sort(key=lambda x: int(x.get('Search Volume', 0)) if x.get('Search Volume') else 0, 
                   reverse=True)
        
        return merged
    
    def _create_summary(self, title: str, bullets: List[str]) -> List[str]:
        """Create product summary"""
        return [f"Title: {title}"] + [f"• {bullet}" for bullet in bullets[:5]]
    
    def _create_metadata(self, asin, marketplace, roots, design_count, revenue_count,
                        branded_count, non_branded_count, categorized_count, final_count):
        """Create metadata dict"""
        return {
            "asin_or_url": asin,
            "marketplace": marketplace,
            "top_10_roots": roots,
            "design_rows_original": design_count,
            "revenue_rows_original": revenue_count,
            "branded_keywords_removed": branded_count,
            "non_branded_keywords_kept": non_branded_count,
            "keywords_categorized": categorized_count,
            "keywords_final": final_count
        }
    
    def _save_results(self, results: List[Dict], asin_or_url: str) -> str:
        """Save results to CSV"""
        try:
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            asin_clean = asin_or_url.replace('/', '_').replace(':', '_')[:50]
            filename = results_dir / f"keyword_evaluations_{asin_clean}_{timestamp}.csv"
            
            if results:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
                    writer.writeheader()
                    writer.writerows(results)
                
                logger.info(f"Saved results: {filename}")
            
            return str(filename)
        except Exception as e:
            logger.error(f"Error saving results: {str(e)}")
            return ""
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Create error response"""
        return {"success": False, "error": message}
    
    def _success_response(self, results, title, bullets, scraped_data, asin, marketplace, roots):
        """Create success response with no results"""
        return {
            "success": True,
            "product_summary": self._create_summary(title, bullets),
            "keyword_evaluations": results,
            "scraped_data": scraped_data,
            "csv_filename": "",
            "metadata": {
                "asin_or_url": asin,
                "marketplace": marketplace,
                "top_10_roots": roots,
                "warning": "No keywords found matching criteria"
            }
        }
    
    def _handle_scrape_error(self, scrape_result):
        """Handle scraping errors"""
        error_msg = scrape_result.get('error', 'Unknown error')
        
        if "CAPTCHA" in error_msg:
            return {
                "success": False,
                "error": "Amazon CAPTCHA detected. Try: 1) Use mock mode, 2) Wait 5-10 min, 3) Use VPN",
                "scraped_data": scrape_result
            }
        
        return {
            "success": False,
            "error": f"Scraping failed: {error_msg}",
            "scraped_data": scrape_result
        }
