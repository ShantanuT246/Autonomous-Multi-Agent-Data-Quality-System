import json
import logging
import re
import time
from typing import Any, Dict, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError
from backend.app.config import settings
from backend.app.db.repository import repo

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def extract_json_block(text: str) -> str:
    """Extract valid JSON from markdown code blocks or surrounding text."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    # Try finding the first '{' or '[' and matching closing
    start_brace = text.find("{")
    start_bracket = text.find("[")
    
    if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        end_brace = text.rfind("}")
        if end_brace != -1:
            return text[start_brace : end_brace + 1]
    elif start_bracket != -1:
        end_bracket = text.rfind("]")
        if end_bracket != -1:
            return text[start_bracket : end_bracket + 1]

    return text


class LLMClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def _call_gemini_api(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.1) -> str:
        """Call Gemini via google.genai or langchain_google_genai."""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = client.models.generate_content(
                model=self.model_name,
                contents=full_prompt,
                config={"temperature": temperature},
            )
            return response.text or ""
        except Exception as e:
            # Fallback to langchain_google_genai
            from langchain_google_genai import ChatGoogleGenerativeAI
            from langchain_core.messages import HumanMessage, SystemMessage

            llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=temperature,
            )
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))
            res = llm.invoke(messages)
            return str(res.content)

    def call_llm(
        self,
        prompt: str,
        response_schema: Type[T],
        system_prompt: Optional[str] = None,
        run_id: Optional[str] = None,
        temperature: float = 0.1,
        max_retries: int = 3,
    ) -> T:
        """
        Structured LLM caller with:
        - Structured schema prompt injection
        - Exponential backoff retry
        - Markdown/JSON block extraction
        - JSON repair / re-asking on validation failure
        - MongoDB logging of all prompt/response pairs
        - Offline mock fallback when GEMINI_API_KEY is not configured
        """
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        augmented_system_prompt = (
            (system_prompt or "You are an expert autonomous data quality reasoning agent.")
            + "\n\nCRITICAL INSTRUCTION: You MUST respond ONLY with valid JSON conforming strictly to this Pydantic JSON schema:\n"
            + schema_json
            + "\nDo not include commentary or markdown explanations outside the JSON."
        )

        start_time = time.time()
        last_error = None

        if not self.is_configured():
            logger.info("GEMINI_API_KEY not configured. Generating schema-valid fallback response.")
            # Produce mock/test valid response for offline development
            fallback_obj = self._generate_mock_response(prompt, response_schema)
            latency = (time.time() - start_time) * 1000
            repo.log_llm_call(
                prompt=prompt,
                response_raw=fallback_obj.model_dump_json(),
                parsed_data=fallback_obj.model_dump(),
                latency_ms=latency,
                model="mock-offline",
                run_id=run_id,
            )
            return fallback_obj

        for attempt in range(1, max_retries + 1):
            try:
                raw_response = self._call_gemini_api(
                    prompt=prompt,
                    system_prompt=augmented_system_prompt,
                    temperature=temperature,
                )
                clean_json = extract_json_block(raw_response)

                parsed_obj = response_schema.model_validate_json(clean_json)
                latency = (time.time() - start_time) * 1000
                repo.log_llm_call(
                    prompt=prompt,
                    response_raw=raw_response,
                    parsed_data=parsed_obj.model_dump(),
                    latency_ms=latency,
                    model=self.model_name,
                    run_id=run_id,
                )
                return parsed_obj

            except (ValidationError, json.JSONDecodeError) as ve:
                last_error = ve
                logger.warning(f"JSON validation failed on attempt {attempt}: {ve}. Retrying with repair prompt...")
                # Re-ask prompt with specific error context
                prompt = (
                    f"Previous attempt produced invalid JSON for the schema: {ve}\n"
                    f"Please fix and output ONLY the corrected JSON for:\n{prompt}"
                )
                time.sleep(1.5 * attempt)
            except Exception as e:
                last_error = e
                logger.warning(f"LLM API error on attempt {attempt}: {e}")
                time.sleep(2.0 * attempt)

        # If retries exhausted, log error and fallback
        latency = (time.time() - start_time) * 1000
        repo.log_llm_call(
            prompt=prompt,
            response_raw="",
            latency_ms=latency,
            model=self.model_name,
            run_id=run_id,
            error=str(last_error),
        )
        logger.error(f"LLM failed after {max_retries} attempts: {last_error}. Using fallback.")
        return self._generate_mock_response(prompt, response_schema)

    def _generate_mock_response(self, prompt: str, response_schema: Type[T]) -> T:
        """Construct sensible default objects for testing when offline."""
        schema_name = response_schema.__name__.lower()
        if "issue" in schema_name:
            # Construct a minimal valid list of issues
            from backend.app.schemas.enums import IssueType, Severity
            from backend.app.schemas.models import Issue
            dummy_issue = Issue(
                id="ISSUE-1",
                column="general",
                issue_type=IssueType.MISSING_VALUES,
                severity=Severity.LOW,
                description="Detected dataset anomalies requiring cleaning.",
                affected_count=1,
                examples=[],
            )
            # Check if container or single
            try:
                return response_schema(issues=[dummy_issue])
            except Exception:
                try:
                    return response_schema(id="ISSUE-1", issue_type=IssueType.MISSING_VALUES, description="Test issue")
                except Exception:
                    pass

        # Generic default initialization: try default call, then model_construct
        try:
            return response_schema()
        except Exception:
            try:
                # Provide dummy string for required fields if needed
                fields = response_schema.model_fields
                kwargs = {}
                for f_name, f_info in fields.items():
                    if f_info.is_required():
                        if f_info.annotation == str or getattr(f_info.annotation, "__name__", "") == "str":
                            kwargs[f_name] = "Generated summary"
                        elif f_info.annotation == list or getattr(f_info.annotation, "__origin__", None) == list:
                            kwargs[f_name] = []
                        elif f_info.annotation == int or getattr(f_info.annotation, "__name__", "") == "int":
                            kwargs[f_name] = 0
                return response_schema(**kwargs)
            except Exception:
                return response_schema.model_construct()


llm_client = LLMClient()


def call_llm(
    prompt: str,
    response_schema: Type[T],
    system_prompt: Optional[str] = None,
    run_id: Optional[str] = None,
    temperature: float = 0.1,
) -> T:
    """Convenience wrapper for the LLM client."""
    return llm_client.call_llm(
        prompt=prompt,
        response_schema=response_schema,
        system_prompt=system_prompt,
        run_id=run_id,
        temperature=temperature,
    )
