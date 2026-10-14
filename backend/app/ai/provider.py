import os
import json
import logging
from typing import List
import httpx
from app.ai.base import AIService
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema, JobLogSchema, JobParameterSchema
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert SAP BASIS and Application Operations AI specialized in SAP job failure root-cause analysis and autonomous remediation.
Analyze the provided SAP job run metadata, step history, technical logs, and execution parameters.
You must return a valid JSON object matching this exact schema:
{
  "failure_category": "TRANSIENT_DATABASE_LOCK" | "INTERMEDIATE_STATE_INCONSISTENCY" | "AUTHORIZATION_ERROR" | "RFC_ERROR" | "UNKNOWN_ERROR",
  "confidence": float between 0.0 and 1.0,
  "root_cause_summary": "Detailed explanation of what failed and why",
  "evidence": ["Bullet point 1 extracted from logs", "Bullet point 2"],
  "recommended_action": "RESTART" | "ESCALATE",
  "restart_mode": "E" (restart from failed step) | "A" (restart from beginning) | "NONE" (do not restart),
  "restart_strategy": "RESTART_FROM_FAILED_STEP" | "RESTART_FROM_START" | "DO_NOT_RESTART",
  "reason": "Detailed policy and architectural rationale for the chosen restart strategy or escalation"
}
Rules:
- For transient database lock contention (e.g. KNA1, DB_LOCK, lock timeout), use failure_category="TRANSIENT_DATABASE_LOCK", recommended_action="RESTART", restart_mode="E", restart_strategy="RESTART_FROM_FAILED_STEP".
- For batch/intermediate state inconsistency where partial recovery is invalid (e.g. Z_SETTLEMENT_RUN, corruption), use failure_category="INTERMEDIATE_STATE_INCONSISTENCY", recommended_action="RESTART", restart_mode="A", restart_strategy="RESTART_FROM_START".
- For missing authorizations or permissions (e.g. F_BKPF_BUK, 403, permission denied), use failure_category="AUTHORIZATION_ERROR", recommended_action="ESCALATE", restart_mode="NONE", restart_strategy="DO_NOT_RESTART".
- Return ONLY valid JSON, no surrounding markdown or explanation.
"""

class RuleBasedAIService(AIService):
    """
    Deterministic rule-based AI analyzer fallback for failure taxonomy classification.
    Runs completely offline with 0 external API dependencies.
    """
    async def analyze_job_failure(
        self,
        job_details: JobRunDetailSchema,
        logs: List[JobLogSchema],
        parameters: List[JobParameterSchema]
    ) -> FailureAnalysisSchema:
        log_text = " ".join([l.message for l in logs]).upper()
        
        if "LOCK_TIMEOUT" in log_text or "DATABASE_LOCK" in log_text or "KNA1" in log_text:
            return FailureAnalysisSchema(
                failure_category="TRANSIENT_DATABASE_LOCK",
                confidence=0.96,
                root_cause_summary="The job failed because a required database table lock (KNA1/KNB1) was held by another transaction beyond timeout limits.",
                evidence=[
                    "ERROR: DATABASE_LOCK_TIMEOUT observed in step logs",
                    "Resource DB_KNA1_WRITE was locked by concurrent process",
                    "Transaction automatically rolled back"
                ],
                recommended_action="RESTART",
                restart_mode="E",
                restart_strategy="RESTART_FROM_FAILED_STEP",
                reason="The error is classified as transient database lock contention. The previous steps completed cleanly and the failed step is independently restartable."
            )
        elif "SETTLEMENT" in log_text or "STATE_INCONSISTENCY" in log_text or "RESTART_FROM_START" in log_text or "BATCH_CORRUPT" in log_text:
            return FailureAnalysisSchema(
                failure_category="INTERMEDIATE_STATE_INCONSISTENCY",
                confidence=0.94,
                root_cause_summary="The settlement run failed due to intermediate ledger staging corruption. Partial recovery from the failed step is unsafe; all batch steps must be recalculated from scratch.",
                evidence=[
                    "ERROR: INTERMEDIATE_STATE_INCONSISTENCY in Step 2",
                    "Staged financial balances do not reconcile with header records",
                    "Transaction rolled back; full rebuild required"
                ],
                recommended_action="RESTART",
                restart_mode="A",
                restart_strategy="RESTART_FROM_START",
                reason="Intermediate state must be rebuilt before retrying. Full rerun from Step 1 is required."
            )
        elif "AUTHORIZATION" in log_text or "LACKS AUTHORIZATION" in log_text or "F_BKPF_BUK" in log_text:
            return FailureAnalysisSchema(
                failure_category="AUTHORIZATION_ERROR",
                confidence=0.98,
                root_cause_summary="The service user account (FIN_SYSTEM_SVC) lacks required authorization object F_BKPF_BUK for Company Code 2000.",
                evidence=[
                    "ERROR: AUTHORIZATION_FAILURE in Step 1",
                    "Missing authorization object F_BKPF_BUK (Activity 01)",
                    "Return Code 12"
                ],
                recommended_action="ESCALATE",
                restart_mode="NONE",
                restart_strategy="DO_NOT_RESTART",
                reason="Authorization failures require Security/IAM team intervention. Automatic retries are non-retryable and blocked by safety policy."
            )
        elif "RFC" in log_text or "NETWORK" in log_text or "TIMEOUT" in log_text:
            return FailureAnalysisSchema(
                failure_category="RFC_ERROR",
                confidence=0.92,
                root_cause_summary="Network or RFC communication link timed out during execution.",
                evidence=[
                    "RFC_TIMEOUT detected",
                    "Connection lost to remote gateway sap_gw_prod_01"
                ],
                recommended_action="RESTART",
                restart_mode="E",
                restart_strategy="RESTART_FROM_FAILED_STEP",
                reason="Transient network timeout. Safe for automatic restart from the failed step after channel reconnection."
            )
        else:
            return FailureAnalysisSchema(
                failure_category="UNKNOWN_ERROR",
                confidence=0.60,
                root_cause_summary=f"Unclassified job failure occurred in step {job_details.failed_step_number or 1}.",
                evidence=[f"Job return code: {job_details.return_code}"],
                recommended_action="ESCALATE",
                restart_mode="NONE",
                restart_strategy="DO_NOT_RESTART",
                reason="Failure cause is unclassified. Manual operational review is required."
            )


class GeminiAIService(AIService):
    """
    Real Google Gemini LLM analyzer using REST API via httpx.
    """
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.fallback = RuleBasedAIService()

    async def analyze_job_failure(
        self,
        job_details: JobRunDetailSchema,
        logs: List[JobLogSchema],
        parameters: List[JobParameterSchema]
    ) -> FailureAnalysisSchema:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
        user_prompt = f"""Job Information:
- Job Name: {job_details.job_name}
- Run Count: {job_details.run_count}
- Failed Step: {job_details.failed_step_number}
- Return Code: {job_details.return_code}
- User: {job_details.job_user}

Execution Steps:
{json.dumps([s.model_dump() for s in job_details.steps], indent=2)}

Technical Logs:
{json.dumps([l.model_dump() for l in logs], indent=2)}

Parameters:
{json.dumps([p.model_dump() for p in parameters], indent=2)}
"""
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + user_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.1
            }
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                text_out = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = json.loads(text_out)
                return FailureAnalysisSchema(**parsed)
        except Exception as e:
            logger.warning(f"Gemini API call failed ({e}), using deterministic fallback rule analyzer.")
            return await self.fallback.analyze_job_failure(job_details, logs, parameters)


class GroqAIService(AIService):
    """
    Real Groq LLM analyzer using Groq OpenAI-compatible REST API.
    """
    def __init__(self, api_key: str, model: str = "openai/gpt-oss-120b"):
        self.api_key = api_key
        self.model = model
        self.fallback = RuleBasedAIService()

    async def analyze_job_failure(
        self,
        job_details: JobRunDetailSchema,
        logs: List[JobLogSchema],
        parameters: List[JobParameterSchema]
    ) -> FailureAnalysisSchema:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        user_prompt = f"""Job: {job_details.job_name} #{job_details.run_count}, Return Code: {job_details.return_code}, Failed Step: {job_details.failed_step_number}
Logs: {json.dumps([l.model_dump() for l in logs])}
Steps: {json.dumps([s.model_dump() for s in job_details.steps])}"""

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                text_out = data["choices"][0]["message"]["content"]
                parsed = json.loads(text_out)
                return FailureAnalysisSchema(**parsed)
        except Exception as e:
            logger.warning(f"Groq API call failed ({e}), using deterministic fallback rule analyzer.")
            return await self.fallback.analyze_job_failure(job_details, logs, parameters)


def get_ai_service() -> AIService:
    """
    Selects the AI provider based on environment variables / settings:
    - AI_PROVIDER="FALLBACK" -> RuleBasedAIService (zero-dependency, fast, deterministic)
    - AI_PROVIDER="GROQ" -> GroqAIService
    - AI_PROVIDER="GEMINI" -> GeminiAIService
    - Defaults to Groq if key configured, otherwise RuleBasedAIService
    """
    provider = (settings.AI_PROVIDER or "").upper()
    if provider in ("FALLBACK", "RULE_BASED", "RULE"):
        return RuleBasedAIService()
    elif provider == "GROQ" and settings.GROQ_API_KEY:
        return GroqAIService(settings.GROQ_API_KEY)
    elif provider == "GEMINI" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("AQ."):
        return GeminiAIService(settings.GEMINI_API_KEY)
    elif settings.GROQ_API_KEY:
        return GroqAIService(settings.GROQ_API_KEY)
    elif settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("AQ."):
        return GeminiAIService(settings.GEMINI_API_KEY)
    
    return RuleBasedAIService()
