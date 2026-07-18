import re
import logging
from typing import Any, Dict

from app.workflow.executors.base import BaseExecutor
from app.agent.planner import llm

logger = logging.getLogger("openclaw-workflow-reasonerexecutor")

class ReasonerExecutor(BaseExecutor):
    """Executor for REASONER type steps.
    
    Resolves variables inside a reasoner prompt and executes an LLM query to generate data.
    """
    async def execute(self, variables: Dict[str, Any]) -> Any:
        prompt = self.step.reasoner_prompt or ""
        if not prompt:
            raise ValueError(f"Step '{self.step.id}' specifies no reasoner_prompt.")

        # Substitute variable placeholders in prompt: e.g. ${file_content}
        def replace_match(match):
            var_name = match.group(1)
            # Fetch variable and serialize appropriately
            val = variables.get(var_name, '')
            if isinstance(val, (dict, list)):
                import json
                return json.dumps(val)
            return str(val)

        final_prompt = re.sub(r'\$\{(\w+)\}', replace_match, prompt)
        logger.info(f"Executing Reasoner step with prompt size: {len(final_prompt)}")

        try:
            # Invoke LLM asynchronously
            response = await llm.ainvoke(final_prompt)
            output_content = response.content
            if isinstance(output_content, str):
                output_content = output_content.strip()
            
            # Extract token metrics if possible
            tokens_used = 0
            if hasattr(response, "response_metadata") and response.response_metadata:
                token_usage = response.response_metadata.get("token_usage", {})
                if token_usage:
                    tokens_used = token_usage.get("total_tokens", 0)
            
            # Store tokens_used inside metadata or step for reporting
            self.step.metadata_json = self.step.metadata_json or "{}"
            meta = self.step.metadata
            meta["tokens_used"] = tokens_used
            import json
            self.step.metadata_json = json.dumps(meta)

            logger.info(f"Reasoner step completed successfully (Tokens used: {tokens_used})")
            return output_content
        except Exception as exc:
            logger.error(f"Error during Reasoner LLM invocation: {exc}")
            raise exc
