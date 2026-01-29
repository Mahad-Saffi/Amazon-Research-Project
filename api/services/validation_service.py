"""
Irrelevant keyword validation service
"""
import logging
import json
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
import csv

from agents import Runner
from research_agents.irrelevant_agent import irrelevant_agent
from research_agents.prompts import IRRELEVANT_VALIDATION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class ValidationService:
    """Handle irrelevant keyword validation"""
    
    async def validate_keywords(
        self,
        categorized_keywords: List[Dict[str, Any]],
        product_title: str,
        product_bullets: List[str],
        batch_size: int = 25,
        max_concurrent: int = 10,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Validate categorized keywords against product
        
        Returns:
            List of irrelevance checks with keyword, is_irrelevant, reasoning
        """
        batches = [categorized_keywords[i:i + batch_size] 
                  for i in range(0, len(categorized_keywords), batch_size)]
        
        logger.info(f"Validating {len(categorized_keywords)} keywords in {len(batches)} batches")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def process_batch(batch):
            nonlocal completed
            async with semaphore:
                try:
                    prompt = IRRELEVANT_VALIDATION_PROMPT_TEMPLATE.format(
                        product_title=product_title,
                        product_bullets_json=json.dumps(product_bullets, indent=2),
                        keywords_json=json.dumps(batch, indent=2)
                    )
                    
                    result = await Runner.run(irrelevant_agent, prompt)
                    raw_output = getattr(result, "final_output", None)
                    structured = self._extract_structured_output(raw_output)
                    
                    completed += 1
                    if progress_callback:
                        progress = 95 + (completed / len(batches)) * 3
                        await progress_callback(progress, f"Validating ({completed}/{len(batches)} batches)...")
                    
                    return structured.get("irrelevance_checks", [])
                except Exception as e:
                    logger.error(f"Error validating batch: {str(e)}")
                    completed += 1
                    return []
        
        tasks = [process_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
        checks = [check for batch in results for check in batch if check]
        logger.info(f"Validation complete: {len(checks)} checks")
        
        # Save validation results
        self._save_validation_results(checks)
        
        return checks
    
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
        """Extract JSON from string"""
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
    
    def _save_validation_results(self, checks: List[Dict[str, Any]]):
        """Save validation results to CSV"""
        try:
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = results_dir / f"irrelevant_classification_{timestamp}.csv"
            
            classifications = []
            for check in checks:
                classifications.append({
                    'keyword': check.get('keyword', ''),
                    'status': 'Irrelevant' if check.get('is_irrelevant', False) else 'Valid',
                    'reasoning': check.get('reasoning', '')
                })
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['keyword', 'status', 'reasoning'])
                writer.writeheader()
                writer.writerows(classifications)
            
            logger.info(f"Saved validation results: {len(classifications)} keywords")
        except Exception as e:
            logger.warning(f"Could not save validation results: {str(e)}")
