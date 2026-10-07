from pydantic import BaseModel
from typing import List, Optional
from app.schemas.job import FailureAnalysisSchema, JobRunDetailSchema

class PolicyDecisionSchema(BaseModel):
    policy_decision: str # APPROVED or REJECTED
    action: str # JOB_RESTART or ESCALATE
    restart_strategy: str # RESTART_FROM_FAILED_STEP, RESTART_FROM_START, DO_NOT_RESTART
    restart_mode: str = "E" # E (from failed step), A (from start), or NONE
    confidence_passed: bool
    category_allowed: bool
    retries_passed: bool
    restart_allowed_passed: bool
    policy_reason: str
    strategy_reason: str
    checks: List[dict]

class JobRemediationPolicy:
    """
    Deterministic Safety & Remediation Policy Engine.
    Guarantees that LLM recommendation cannot bypass safety rules.
    """
    AUTO_RESTART_CATEGORIES = {
        "TRANSIENT_DATABASE_LOCK",
        "TRANSIENT_DATABASE_ERROR",
        "INTERMEDIATE_STATE_INCONSISTENCY",
        "NETWORK_TIMEOUT",
        "RFC_ERROR",
        "SYSTEM_RESOURCE_ERROR"
    }

    CONFIDENCE_THRESHOLD = 0.90

    def evaluate(self, analysis: FailureAnalysisSchema, job_details: JobRunDetailSchema) -> PolicyDecisionSchema:
        category_allowed = analysis.failure_category in self.AUTO_RESTART_CATEGORIES
        confidence_passed = analysis.confidence >= self.CONFIDENCE_THRESHOLD
        restart_allowed_passed = job_details.restart_allowed
        retries_passed = job_details.retry_count < job_details.max_retries

        checks = [
            {
                "rule": "Failure Category in Auto-Restart Allowlist",
                "passed": category_allowed,
                "detail": f"Category '{analysis.failure_category}' " + ("is retryable." if category_allowed else "is classified as non-retryable.")
            },
            {
                "rule": "AI Diagnosis Confidence Threshold (>= 90%)",
                "passed": confidence_passed,
                "detail": f"Confidence level is {int(analysis.confidence * 100)}% (Required: {int(self.CONFIDENCE_THRESHOLD * 100)}%)."
            },
            {
                "rule": "SAP Job Permitted Restart Flag",
                "passed": restart_allowed_passed,
                "detail": "Job configuration permits automatic restart." if restart_allowed_passed else "Job configuration blocks restart."
            },
            {
                "rule": "Retry Limit Check",
                "passed": retries_passed,
                "detail": f"Current retry count: {job_details.retry_count} / Max retries: {job_details.max_retries}."
            }
        ]

        is_approved = category_allowed and confidence_passed and restart_allowed_passed and retries_passed
        platform = getattr(job_details, "platform", "MOCK_SAP") or "MOCK_SAP"

        if is_approved:
            if platform == "SAP_BTP":
                restart_strategy = "RESTART_FROM_START"
                restart_mode = "A"
                strategy_reason = "SAP BTP HTTP Action Job is modeled as a single-step execution; retrying full HTTP action from start."
            else:
                restart_mode = analysis.restart_mode if analysis.restart_mode in ["E", "A"] else "E"
                if restart_mode == "A" or getattr(analysis, "restart_strategy", "") == "RESTART_FROM_START":
                    restart_strategy = "RESTART_FROM_START"
                    restart_mode = "A"
                    strategy_reason = "Intermediate state must be rebuilt before retrying. Full rerun from step 1 is required."
                else:
                    restart_strategy = "RESTART_FROM_FAILED_STEP"
                    restart_mode = "E"
                    strategy_reason = "Previous successful steps are safe to retain and the failed step is independently restartable."

            policy_reason = (
                f"Automatic remediation APPROVED. Failure category '{analysis.failure_category}' "
                f"is retryable, confidence is {int(analysis.confidence * 100)}%, and retry count "
                f"({job_details.retry_count}/{job_details.max_retries}) is within safety policy limits."
            )
            return PolicyDecisionSchema(
                policy_decision="APPROVED",
                action="JOB_RESTART",
                restart_strategy=restart_strategy,
                restart_mode=restart_mode,
                confidence_passed=confidence_passed,
                category_allowed=category_allowed,
                retries_passed=retries_passed,
                restart_allowed_passed=restart_allowed_passed,
                policy_reason=policy_reason,
                strategy_reason=strategy_reason,
                checks=checks
            )
        else:
            failed_rules = [c["rule"] for c in checks if not c["passed"]]
            policy_reason = f"Automatic remediation BLOCKED due to policy violations: {', '.join(failed_rules)}."
            strategy_reason = "Non-retryable failure category or safety policy violation. Job cannot be restarted automatically."
            return PolicyDecisionSchema(
                policy_decision="REJECTED",
                action="ESCALATE",
                restart_strategy="DO_NOT_RESTART",
                restart_mode="NONE",
                confidence_passed=confidence_passed,
                category_allowed=category_allowed,
                retries_passed=retries_passed,
                restart_allowed_passed=restart_allowed_passed,
                policy_reason=policy_reason,
                strategy_reason=strategy_reason,
                checks=checks
            )

