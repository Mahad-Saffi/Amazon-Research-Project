"""
Brand detection service
"""
import logging
import json
import asyncio
from typing import List, Tuple, Dict, Any
from pathlib import Path
from datetime import datetime
import csv

from agents import Runner
from research_agents.brand_agents import brand_detection_agent
from research_agents.prompts import BRAND_DETECTION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class BrandService:
    """Handle brand detection for keywords"""
    
    async def detect_brands(
        self, 
        keywords: List[str],
        max_concurrent: int = 10
    ) -> Tuple[List[str], List[str]]:
        """
        Detect branded vs non-branded keywords
        
        Returns:
            (branded_keywords, non_branded_keywords)
        """
        try:
            batch_size = 50
            batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
            
            logger.info(f"Brand detection: {len(keywords)} keywords in {len(batches)} batches")
            
            semaphore = asyncio.Semaphore(max_concurrent)
            all_branded = []
            all_non_branded = []
            
            async def process_batch(batch):
                async with semaphore:
                    try:
                        prompt = BRAND_DETECTION_PROMPT_TEMPLATE.format(
                            keywords_json=json.dumps(batch, indent=2)
                        )
                        
                        result = await Runner.run(brand_detection_agent, prompt)
                        detection_raw = getattr(result, "final_output", None)
                        detection_structured = self._extract_structured_output(detection_raw)
                        
                        branded = detection_structured.get("branded_keywords", [])
                        non_branded = detection_structured.get("non_branded_keywords", [])
                        
                        return branded, non_branded
                    except Exception as e:
                        logger.error(f"Error in brand detection batch: {str(e)}")
                        return [], batch
            
            tasks = [process_batch(batch) for batch in batches]
            results = await asyncio.gather(*tasks)
            
            for branded, non_branded in results:
                all_branded.extend(branded)
                all_non_branded.extend(non_branded)
            
            logger.info(f"Brand detection: {len(all_branded)} branded, {len(all_non_branded)} non-branded")
            
            # Save classifications
            self._save_brand_classifications(all_branded, all_non_branded)
            
            return all_branded, all_non_branded
            
        except Exception as e:
            logger.error(f"Error in brand detection: {str(e)}")
            return [], keywords
    
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
    
    def _save_brand_classifications(self, branded: List[str], non_branded: List[str]):
        """Save brand classifications to CSV"""
        try:
            results_dir = Path("results")
            results_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = results_dir / f"brand_classification_{timestamp}.csv"
            
            classifications = []
            for kw in branded:
                classifications.append({
                    'keyword': kw,
                    'status': 'Branded',
                    'reasoning': 'Contains brand name'
                })
            for kw in non_branded:
                classifications.append({
                    'keyword': kw,
                    'status': 'Non-Branded',
                    'reasoning': 'Generic term'
                })
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['keyword', 'status', 'reasoning'])
                writer.writeheader()
                writer.writerows(classifications)
            
            logger.info(f"Saved brand classifications: {len(classifications)} keywords")
        except Exception as e:
            logger.warning(f"Could not save brand classifications: {str(e)}")
