"""
VERIFIER Agent — Response Validation & Quality Assurance

The VERIFIER agent is the final quality gate in the EIRA pipeline.

Role:
  Validates that the final EIRA response adequately addresses the original user
  question through comprehensive quality scoring and issue detection.

Responsibilities:
  1. Semantic Relevance — Does answer match question intent?
  2. Completeness — Are all question aspects covered?
  3. Citation Coverage — Is response adequately sourced?
  4. Coherence — Is answer logically structured?
  5. Confidence Consistency — Does confidence match quality?

Decision Logic:
  ✅ Accept — Response passes all validation checks (overall ≥ 0.75, no critical issues)
  🔄 Re-iterate — Issues found; recommend re-querying with feedback
  ❓ Clarify — Minor issues; suggest user clarification

Input:
  - original_question: str (user's initial query)
  - eira_response: EIRAResponse (response from orchestrator)
  - intent_classification: IntentClassification (EIRA's intent analysis)

Output:
  - VerificationReport (detailed validation results)
  - Final response or re-iteration request

Example Flow:
  1. User asks: "What's the avg age of engineers in Austin?"
  2. EIRA responds with SQL results
  3. VERIFIER checks:
     - Does answer mention age and engineering? ✓
     - Are results cited? ✓
     - Is answer complete? ✓
     - Passes? → Return response to user ✓

  Or if validation fails:
     - Incomplete answer detected
     - Return: "Please provide avg age statistics"
     - Trigger re-iteration

Reference: CLAUDE.md § VERIFIER Agent
"""

from typing import Optional
from datetime import datetime
from models.pydantic_io import (
    EIRAResponse,
    IntentClassification,
)
from tools.verifier_tools import (
    validate_response_against_question,
    get_re_iteration_feedback,
    VerificationReport,
    ValidationSeverity,
)
import logging

logger = logging.getLogger(__name__)


class VERIFIERAgent:
    """
    VERIFIER Agent — Quality Assurance Gate for EIRA Responses

    Operates as the final validation layer before responses reach users.
    """

    def __init__(self, name: str = "VERIFIER"):
        """Initialize VERIFIER agent"""
        self.name = name
        self.validation_attempts = 0
        self.max_re_iterations = 2

    async def verify_response(
        self,
        original_question: str,
        response: EIRAResponse,
        intent_classification: IntentClassification,
        attempt: int = 1,
    ) -> tuple[bool, EIRAResponse, Optional[VerificationReport]]:
        """
        Main VERIFIER entry point.

        Validates response against original question.

        Args:
            original_question: Original user query
            response: EIRA's response to validate
            intent_classification: Intent analysis from EIRA
            attempt: Re-iteration attempt number

        Returns:
            (passes: bool, response_or_feedback: EIRAResponse, report: VerificationReport)
        """
        logger.info(
            f"{self.name} validating response (attempt {attempt}/{self.max_re_iterations})"
        )

        self.validation_attempts = attempt

        # ────────────────────────────────────────────────────────────────
        # Run comprehensive validation
        # ────────────────────────────────────────────────────────────────
        report = await validate_response_against_question(
            original_question=original_question,
            response=response,
            intent_classification=intent_classification,
        )

        # ────────────────────────────────────────────────────────────────
        # Decision Logic
        # ────────────────────────────────────────────────────────────────

        if report.passes:
            logger.info(f"{self.name} validation PASSED (score: {report.overall_quality_score})")
            return True, response, report

        else:
            logger.warning(
                f"{self.name} validation FAILED (score: {report.overall_quality_score})"
            )

            # Check if we should re-iterate
            critical_issues = [i for i in report.issues if i.severity == ValidationSeverity.CRITICAL]

            if attempt < self.max_re_iterations and critical_issues:
                logger.info(
                    f"{self.name} recommending re-iteration ({attempt + 1}/{self.max_re_iterations})"
                )
                feedback = await get_re_iteration_feedback(report, original_question)

                # Create feedback response
                feedback_response = EIRAResponse(
                    answer=feedback,
                    sources=[],
                    confidence=0.0,
                    hitl_triggered=True,
                    model_used="verifier-feedback",
                )

                return False, feedback_response, report

            else:
                logger.warning(
                    f"{self.name} cannot re-iterate (max attempts reached)"
                )
                # Return response with confidence reduced
                response.confidence = max(0.0, response.confidence - 0.2)
                return True, response, report

    async def check_response_quality(
        self,
        response: EIRAResponse,
    ) -> dict:
        """
        Quick quality check without full validation.

        Returns:
            Quick metrics about response quality
        """
        metrics = {
            "has_sources": len(response.sources) > 0,
            "source_count": len(response.sources),
            "confidence_score": response.confidence,
            "answer_length": len(response.answer),
            "is_reasonable_length": 50 < len(response.answer) < 5000,
        }

        # Check for confidence > 0.75
        metrics["high_confidence"] = response.confidence >= 0.75

        # Check for grounded sources
        if response.sources:
            grounded_count = sum(1 for s in response.sources if s.grounded)
            metrics["grounded_sources"] = grounded_count / len(response.sources)
        else:
            metrics["grounded_sources"] = 0.0

        metrics["quality_ok"] = (
            metrics["has_sources"]
            and metrics["is_reasonable_length"]
            and metrics["grounded_sources"] > 0.8
        )

        return metrics

    async def get_validation_summary(
        self,
        report: VerificationReport,
    ) -> str:
        """
        Generate user-friendly validation summary.

        Returns:
            Formatted summary of validation results
        """
        summary_lines = [
            "═" * 60,
            "RESPONSE QUALITY ASSESSMENT",
            "═" * 60,
            f"Overall Quality Score: {report.overall_quality_score:.1%}",
            f"Status: {'✅ PASSED' if report.passes else '❌ FAILED'}",
            "",
            "Detailed Scores:",
            f"  • Semantic Relevance:   {report.semantic_relevance_score:.1%}",
            f"  • Completeness:         {report.completeness_score:.1%}",
            f"  • Citation Coverage:    {report.citation_coverage_score:.1%}",
            f"  • Coherence:            {report.coherence_score:.1%}",
            "",
        ]

        if report.issues:
            summary_lines.append(f"Issues Found: {len(report.issues)}")
            summary_lines.append("")

            # Group by severity
            for severity in [ValidationSeverity.CRITICAL, ValidationSeverity.HIGH, ValidationSeverity.MEDIUM, ValidationSeverity.LOW]:
                severity_issues = [i for i in report.issues if i.severity == severity]
                if severity_issues:
                    emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(severity.value, "•")
                    summary_lines.append(f"{emoji} {severity.value.upper()}: ({len(severity_issues)})")

                    for issue in severity_issues:
                        summary_lines.append(f"    - {issue.description}")

            summary_lines.append("")

        summary_lines.append(f"Recommendation: {report.recommended_action.upper()}")
        summary_lines.append("═" * 60)

        return "\n".join(summary_lines)


# ────────────────────────────────────────────────────────────────────────
# Convenience Instance
# ────────────────────────────────────────────────────────────────────────

verifier = VERIFIERAgent(name="VERIFIER")
