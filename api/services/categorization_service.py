"""
Keyword categorization service
"""
import logging
import json
import asyncio
from typing import List, Dict, Any

from agents import Runner
from research_agents.categorization_agent import categorization_agent
from research_agents.prompts import KEYWORD_CATEGORIZATION_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

class CategorizationService:
    """Handle keyword categorization"""
    
    async def categorize_keywords(
        self,
        keywords: List[str],
        batch_size: int = 5,
        max_concurrent: int = 10,
        progress_callback=None
    ) -> List[Dict[str, Any]]:
        """
        Categorize keywords into irrelevant/outlier/relevant/design-specific
        
        Returns:
            List of categorizations with keyword, category, reasoning
        """
        batches = [keywords[i:i + batch_size] for i in range(0, len(keywords), batch_size)]
        logger.info(f"Categorizing {len(keywords)} keywords in {len(batches)} batches")
        
        semaphore = asyncio.Semaphore(max_concurrent)
        completed = 0
        
        async def process_batch(batch):
            nonlocal completed
            async with semaphore:
                try:
                    prompt = KEYWORD_CATEGORIZATION_PROMPT_TEMPLATE.format(
                        keywords_json=json.dumps(batch, indent=2)
                    )
                    
                    result = await Runner.run(categorization_agent, prompt)
                    raw_output = getattr(result, "final_output", None)
                    structured = self._extract_structured_output(raw_output)
                    
                    completed += 1
                    if progress_callback:
                        progress = 70 + (completed / len(batches)) * 25
                        await progress_callback(progress, f"Categorizing ({completed}/{len(batches)} batches)...")
                    
                    return structured.get("categorizations", [])
                except Exception as e:
                    logger.error(f"Error categorizing batch: {str(e)}")
                    completed += 1
                    return []
        
        tasks = [process_batch(batch) for batch in batches]
        results = await asyncio.gather(*tasks)
        
        categorizations = [cat for batch in results for cat in batch if cat]
        logger.info(f"Categorization complete: {len(categorizations)} results")
        
        return categorizations
    
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
