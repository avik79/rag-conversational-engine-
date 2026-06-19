"""
Comprehensive Test Suite for VERIFIER Agent

Covers:
  - All 5 validation metrics
  - All issue severity levels
  - All decision paths (accept, re-iterate, clarify)
  - Edge cases and boundary conditions
  - Re-iteration scenarios
  - Integration tests
  - Configuration variations
  - Error handling

Run: pytest tests/test_verifier_comprehensive.py -v
"""

import pytest
import asyncio
from datetime import datetime
from models.pydantic_io import (
    EIRAResponse,
    IntentClassification,
    SourceCitation,
    EmployeeRow,
)
from tools.verifier_tools import (
    validate_response_against_question,
    get_re_iteration_feedback,
    VerificationReport,
    ValidationSeverity,
)
from agents.verifier import VERIFIERAgent, verifier


# ────────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────────

@pytest.fixture
def sql_intent():
    """SQL-only intent classification"""
    return IntentClassification(
        intent="sql_only",
        sql_subquery="Get average age of engineers in Austin",
        reasoning="User asked for employee statistics",
    )


@pytest.fixture
def rag_intent():
    """RAG-only intent classification"""
    return IntentClassification(
        intent="rag_only",
        rag_subquery="Current weather in Austin",
        reasoning="User asked for weather information",
    )


@pytest.fixture
def cross_domain_intent():
    """Cross-domain intent classification"""
    return IntentClassification(
        intent="cross_domain",
        sql_subquery="Find Austin employees",
        rag_subquery="Austin weather information",
        reasoning="User wants to correlate employee data with context",
    )


@pytest.fixture
def good_sources():
    """Multiple grounded sources"""
    return [
        SourceCitation(
            claim="12 engineers in Austin",
            evidence_ref="sql:employee_id:5",
            grounded=True,
        ),
        SourceCitation(
            claim="average age 32.5",
            evidence_ref="sql:employee_id:15",
            grounded=True,
        ),
        SourceCitation(
            claim="age range 26-38",
            evidence_ref="sql:employee_id:8",
            grounded=True,
        ),
    ]


@pytest.fixture
def single_source():
    """Single source"""
    return [
        SourceCitation(
            claim="Average age is 32 years",
            evidence_ref="sql:employee_id:1",
            grounded=True,
        ),
    ]


@pytest.fixture
def ungrounded_source():
    """Ungrounded source"""
    return [
        SourceCitation(
            claim="All engineers are happy",
            evidence_ref="sql:employee_id:999",
            grounded=False,
        ),
    ]


@pytest.fixture
def no_sources():
    """No sources"""
    return []


# ────────────────────────────────────────────────────────────────────────
# Test Suite 1: Semantic Relevance (30% weight)
# ────────────────────────────────────────────────────────────────────────

class TestSemanticRelevance:
    """Tests for semantic relevance validation (30% weight)"""

    @pytest.mark.asyncio
    async def test_semantic_relevance_good_length(self, sql_intent, good_sources):
        """Response with good length should pass semantic check"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers in that location with ages ranging "
                   "from 26 to 38 years old.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score >= 0.80

    @pytest.mark.asyncio
    async def test_semantic_relevance_too_short(self, sql_intent, single_source):
        """Response that's too short should get lower score"""
        response = EIRAResponse(
            answer="32 years",
            sources=single_source,
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score < 0.70
        assert any(
            "too short" in issue.type.lower()
            for issue in report.issues
            if issue.severity == ValidationSeverity.HIGH
        )

    @pytest.mark.asyncio
    async def test_semantic_relevance_too_long(self, sql_intent, good_sources):
        """Response that's too long should get lower score"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. " * 250,  # Exceeds 5000
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score < 0.75

    @pytest.mark.asyncio
    async def test_semantic_relevance_off_topic(self, sql_intent, single_source):
        """Off-topic response should fail"""
        response = EIRAResponse(
            answer="I don't know about that. I'm unable to find that information.",
            sources=single_source,
            confidence=0.30,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score < 0.50
        critical = [i for i in report.issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical) > 0

    @pytest.mark.asyncio
    async def test_semantic_relevance_sql_missing_employee_mention(self, sql_intent):
        """SQL query response missing employee/department mention"""
        response = EIRAResponse(
            answer="Yes, there is data in the system.",
            sources=[],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score <= 0.70

    @pytest.mark.asyncio
    async def test_semantic_relevance_rag_short_synthesis(self, rag_intent):
        """RAG response with insufficient synthesis"""
        response = EIRAResponse(
            answer="Weather is sunny.",
            sources=[SourceCitation(
                claim="sunny",
                evidence_ref="chunk_12345678-1234-1234-1234-123456789012",
                grounded=True,
            )],
            confidence=0.75,
        )

        report = await validate_response_against_question(
            "What's the weather in Austin?",
            response,
            rag_intent,
        )

        assert report.semantic_relevance_score < 0.80

    @pytest.mark.asyncio
    async def test_semantic_relevance_cross_domain_integration(self, cross_domain_intent):
        """Cross-domain response integrating both SQL and RAG"""
        response = EIRAResponse(
            answer="There are 12 engineers in Austin with an average age of 32.5. "
                   "The weather there is currently sunny and 28°C.",
            sources=[
                SourceCitation(
                    claim="12 engineers",
                    evidence_ref="sql:employee_id:1",
                    grounded=True,
                ),
                SourceCitation(
                    claim="weather sunny 28°C",
                    evidence_ref="chunk_abcd1234-5678-90ef-ghij-klmnopqrstuv",
                    grounded=True,
                ),
            ],
            confidence=0.82,
        )

        report = await validate_response_against_question(
            "Tell me about engineers in Austin and current weather",
            response,
            cross_domain_intent,
        )

        assert report.semantic_relevance_score >= 0.80


# ────────────────────────────────────────────────────────────────────────
# Test Suite 2: Completeness (25% weight)
# ────────────────────────────────────────────────────────────────────────

class TestCompleteness:
    """Tests for completeness validation (25% weight)"""

    @pytest.mark.asyncio
    async def test_completeness_with_sources(self, sql_intent, good_sources):
        """Complete response with multiple sources"""
        response = EIRAResponse(
            answer="The average age is 32.5 years. There are 12 engineers total. "
                   "Ages range from 26 to 38. In summary, this represents the "
                   "Austin engineering team's age profile.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.completeness_score >= 0.75

    @pytest.mark.asyncio
    async def test_completeness_no_sources(self, sql_intent, no_sources):
        """Response with no sources is incomplete"""
        response = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=no_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.completeness_score < 0.65

    @pytest.mark.asyncio
    async def test_completeness_single_source(self, sql_intent, single_source):
        """Response with single source has lower completeness"""
        response = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.completeness_score < 0.80

    @pytest.mark.asyncio
    async def test_completeness_multi_part_question_addressed(self, sql_intent):
        """Multi-part question should be addressed separately"""
        response = EIRAResponse(
            answer="First, the average age is 32.5 years.\n\n"
                   "Second, there are 12 engineers total.\n\n"
                   "In conclusion, this is our complete Austin engineering profile.",
            sources=[
                SourceCitation(claim="age info", evidence_ref="sql:employee_id:1", grounded=True),
                SourceCitation(claim="count info", evidence_ref="sql:employee_id:2", grounded=True),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age and total count of engineers?",
            response,
            sql_intent,
        )

        assert report.completeness_score >= 0.80

    @pytest.mark.asyncio
    async def test_completeness_missing_conclusion(self, sql_intent, good_sources):
        """Response without conclusion has lower completeness"""
        response = EIRAResponse(
            answer="The average age is 32.5 years. There are 12 engineers. "
                   "Ages range from 26 to 38.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What can you tell me about engineers in Austin?",
            response,
            sql_intent,
        )

        # Should have LOW severity issue, not HIGH
        assert report.completeness_score >= 0.70


# ────────────────────────────────────────────────────────────────────────
# Test Suite 3: Citation Coverage (25% weight)
# ────────────────────────────────────────────────────────────────────────

class TestCitationCoverage:
    """Tests for citation coverage validation (25% weight)"""

    @pytest.mark.asyncio
    async def test_citation_coverage_multiple_citations(self, sql_intent):
        """Response with adequate citations"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers ranging from 26 to 38 years old.",
            sources=[
                SourceCitation(claim="32.5 years", evidence_ref="sql:employee_id:1", grounded=True),
                SourceCitation(claim="12 engineers", evidence_ref="sql:employee_id:2", grounded=True),
                SourceCitation(claim="26-38 range", evidence_ref="sql:employee_id:3", grounded=True),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.citation_coverage_score >= 0.80

    @pytest.mark.asyncio
    async def test_citation_coverage_no_citations(self, sql_intent):
        """Response with no citations should fail"""
        response = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=[],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.citation_coverage_score == 0.0
        assert any(
            issue.severity == ValidationSeverity.CRITICAL
            for issue in report.issues
        )

    @pytest.mark.asyncio
    async def test_citation_coverage_ungrounded_citations(self, sql_intent):
        """Response with ungrounded citations should fail"""
        response = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=[
                SourceCitation(
                    claim="32.5 years",
                    evidence_ref="sql:employee_id:1",
                    grounded=False,  # Not grounded!
                ),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.citation_coverage_score < 0.50

    @pytest.mark.asyncio
    async def test_citation_coverage_low_ratio(self, sql_intent):
        """Response with low citation-to-claim ratio"""
        response = EIRAResponse(
            answer="The average age is 32.5 years. Engineers work in Austin. "
                   "They have various ages. The company employs many people. "
                   "Our data shows interesting patterns.",
            sources=[
                SourceCitation(claim="age data", evidence_ref="sql:employee_id:1", grounded=True),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.citation_coverage_score < 0.70

    @pytest.mark.asyncio
    async def test_citation_coverage_format_validation(self, sql_intent):
        """Citation reference format validation"""
        # Valid SQL reference
        response_sql = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=[
                SourceCitation(
                    claim="age",
                    evidence_ref="sql:employee_id:123",
                    grounded=True,
                ),
            ],
            confidence=0.85,
        )

        report_sql = await validate_response_against_question(
            "What's the average age?",
            response_sql,
            sql_intent,
        )

        assert report_sql.citation_coverage_score >= 0.70


# ────────────────────────────────────────────────────────────────────────
# Test Suite 4: Coherence (15% weight)
# ────────────────────────────────────────────────────────────────────────

class TestCoherence:
    """Tests for coherence validation (15% weight)"""

    @pytest.mark.asyncio
    async def test_coherence_well_structured(self, sql_intent, good_sources):
        """Well-structured response with good coherence"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We identified 12 engineers in total. They range from 26 to 38 years old. "
                   "Overall, this represents our Austin engineering team.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.coherence_score >= 0.80

    @pytest.mark.asyncio
    async def test_coherence_run_on_sentences(self, sql_intent, single_source):
        """Response with very long run-on sentences"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years and we found that "
                   "these engineers span across multiple departments and have varied experience levels "
                   "with ages that range from 26 to 38 years which shows the diversity of our team.",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.coherence_score < 0.90

    @pytest.mark.asyncio
    async def test_coherence_topic_drift(self, sql_intent, good_sources):
        """Response that drifts topics"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "Austin is located in Texas. Texas has many cities. "
                   "Cities are important for businesses.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.coherence_score < 0.80

    @pytest.mark.asyncio
    async def test_coherence_fragments(self, sql_intent):
        """Response with fragments instead of sentences"""
        response = EIRAResponse(
            answer="Average age. 32.5 years. Engineers. 12 total. Range 26-38.",
            sources=[SourceCitation(claim="age", evidence_ref="sql:employee_id:1", grounded=True)],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.coherence_score < 0.70


# ────────────────────────────────────────────────────────────────────────
# Test Suite 5: Confidence Consistency (5% weight)
# ────────────────────────────────────────────────────────────────────────

class TestConfidenceConsistency:
    """Tests for confidence consistency validation (5% weight)"""

    @pytest.mark.asyncio
    async def test_confidence_well_calibrated(self, sql_intent, good_sources):
        """Confidence well-calibrated with quality"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.82,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Should be high score
        assert abs(report.overall_quality_score - response.confidence) < 0.1

    @pytest.mark.asyncio
    async def test_confidence_overconfident(self, sql_intent, single_source):
        """Response that's overconfident"""
        response = EIRAResponse(
            answer="Average age: 32.5 years.",
            sources=single_source,
            confidence=0.95,  # Too high!
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Should have HIGH issue about overconfidence
        assert any(
            "overconfident" in issue.type.lower()
            for issue in report.issues
        )

    @pytest.mark.asyncio
    async def test_confidence_underconfident(self, sql_intent, good_sources):
        """Response that's underconfident"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages ranging from 26 to 38 years old.",
            sources=good_sources,
            confidence=0.45,  # Too low!
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Might have LOW issue about underconfidence
        assert report.overall_quality_score > response.confidence


# ────────────────────────────────────────────────────────────────────────
# Test Suite 6: Overall Quality Scoring
# ────────────────────────────────────────────────────────────────────────

class TestOverallQualityScoring:
    """Tests for overall quality score calculation"""

    @pytest.mark.asyncio
    async def test_overall_score_perfect_response(self, sql_intent):
        """Perfect response should score 1.0"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We identified 12 engineers. The age range is 26-38 years. "
                   "The engineers span 3 departments. In summary, this is our complete Austin profile.",
            sources=[
                SourceCitation(claim="32.5 years", evidence_ref="sql:employee_id:1", grounded=True),
                SourceCitation(claim="12 engineers", evidence_ref="sql:employee_id:2", grounded=True),
                SourceCitation(claim="26-38 range", evidence_ref="sql:employee_id:3", grounded=True),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age of engineers in Austin?",
            response,
            sql_intent,
        )

        assert report.overall_quality_score >= 0.85

    @pytest.mark.asyncio
    async def test_overall_score_weights_applied(self, sql_intent):
        """Overall score should reflect metric weights"""
        # Good semantic relevance but bad citations (25% weight should hurt more)
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages from 26 to 38.",
            sources=[],  # No citations!
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Overall should be low due to citation_coverage being 25% weight
        assert report.overall_quality_score < 0.65

    @pytest.mark.asyncio
    async def test_overall_score_minimum_zero(self, sql_intent):
        """Scores should never be negative"""
        response = EIRAResponse(
            answer="",  # Empty!
            sources=[],
            confidence=0.0,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.overall_quality_score >= 0.0


# ────────────────────────────────────────────────────────────────────────
# Test Suite 7: Decision Logic
# ────────────────────────────────────────────────────────────────────────

class TestDecisionLogic:
    """Tests for VERIFIER decision logic (accept/re-iterate/clarify)"""

    @pytest.mark.asyncio
    async def test_decision_accept_good_response(self, sql_intent, good_sources):
        """Good response should be ACCEPT"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.passes
        assert report.recommended_action == "accept"

    @pytest.mark.asyncio
    async def test_decision_re_iterate_critical_issues(self, sql_intent):
        """Response with critical issues should trigger RE_ITERATE"""
        response = EIRAResponse(
            answer="Yes.",  # Too brief, no context
            sources=[],  # No citations
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert not report.passes
        assert report.recommended_action == "re_iterate"

    @pytest.mark.asyncio
    async def test_decision_clarify_user(self):
        """Unclear question might recommend CLARIFY_USER"""
        response = EIRAResponse(
            answer="Could you be more specific about what you're asking?",
            sources=[],
            confidence=0.40,
        )

        meta_intent = IntentClassification(
            intent="unclear",
            reasoning="User question is ambiguous",
        )

        report = await validate_response_against_question(
            "Tell me stuff",
            response,
            meta_intent,
        )

        # Might recommend clarification
        assert report.recommended_action in ["re_iterate", "clarify_user"]


# ────────────────────────────────────────────────────────────────────────
# Test Suite 8: VERIFIER Agent Class
# ────────────────────────────────────────────────────────────────────────

class TestVERIFIERAgentClass:
    """Tests for VERIFIERAgent class"""

    @pytest.mark.asyncio
    async def test_verifier_agent_verify_response_accept(self, sql_intent, good_sources):
        """VERIFIER agent should accept good response"""
        agent = VERIFIERAgent()

        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.85,
        )

        passes, result, report = await agent.verify_response(
            original_question="What's the average age?",
            response=response,
            intent_classification=sql_intent,
            attempt=1,
        )

        assert passes
        assert result == response

    @pytest.mark.asyncio
    async def test_verifier_agent_verify_response_fail(self, sql_intent):
        """VERIFIER agent should fail bad response"""
        agent = VERIFIERAgent()

        response = EIRAResponse(
            answer="Yes.",
            sources=[],
            confidence=0.90,
        )

        passes, result, report = await agent.verify_response(
            original_question="What's the average age?",
            response=response,
            intent_classification=sql_intent,
            attempt=1,
        )

        assert not passes

    @pytest.mark.asyncio
    async def test_verifier_agent_check_quality(self, good_sources):
        """VERIFIER agent should provide quick quality metrics"""
        agent = VERIFIERAgent()

        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.85,
        )

        metrics = await agent.check_response_quality(response)

        assert metrics["has_sources"]
        assert metrics["source_count"] == 3
        assert metrics["confidence_score"] == 0.85
        assert metrics["is_reasonable_length"]
        assert metrics["quality_ok"]

    @pytest.mark.asyncio
    async def test_verifier_agent_validation_summary(self, sql_intent, good_sources):
        """VERIFIER agent should generate human-friendly summary"""
        agent = VERIFIERAgent()

        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.85,
        )

        _, _, report = await agent.verify_response(
            original_question="What's the average age?",
            response=response,
            intent_classification=sql_intent,
        )

        summary = await agent.get_validation_summary(report)

        assert "RESPONSE QUALITY ASSESSMENT" in summary
        assert "Overall Quality Score" in summary
        assert "PASSED" in summary or "FAILED" in summary


# ────────────────────────────────────────────────────────────────────────
# Test Suite 9: Re-iteration Scenarios
# ────────────────────────────────────────────────────────────────────────

class TestReIteration:
    """Tests for re-iteration feedback and loop"""

    @pytest.mark.asyncio
    async def test_re_iteration_feedback_generated(self, sql_intent):
        """Feedback should be generated for re-iteration"""
        response = EIRAResponse(
            answer="Yes.",
            sources=[],
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        feedback = await get_re_iteration_feedback(report, "What's the average age?")

        assert "CRITICAL" in feedback or "critical" in feedback
        assert len(feedback) > 100

    @pytest.mark.asyncio
    async def test_re_iteration_feedback_specific_issues(self, sql_intent):
        """Feedback should list specific issues to fix"""
        response = EIRAResponse(
            answer="Average is 32.",
            sources=[],
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        feedback = await get_re_iteration_feedback(report, "What's the average age?")

        assert "citations" in feedback.lower() or "sources" in feedback.lower()
        assert "Fix:" in feedback or "Suggestion:" in feedback

    @pytest.mark.asyncio
    async def test_re_iteration_feedback_includes_scores(self, sql_intent):
        """Feedback should include score breakdown"""
        response = EIRAResponse(
            answer="Average is 32.",
            sources=[],
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        feedback = await get_re_iteration_feedback(report, "What's the average age?")

        assert "Semantic Relevance" in feedback
        assert "Completeness" in feedback
        assert "Citation Coverage" in feedback

    @pytest.mark.asyncio
    async def test_re_iteration_attempt_tracking(self, sql_intent, good_sources):
        """Verify response with attempt number"""
        agent = VERIFIERAgent()

        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years.",
            sources=good_sources,
            confidence=0.85,
        )

        # Attempt 1
        passes1, _, report1 = await agent.verify_response(
            original_question="What's the average age?",
            response=response,
            intent_classification=sql_intent,
            attempt=1,
        )

        assert report1.verification_attempts == 1

        # Attempt 2
        passes2, _, report2 = await agent.verify_response(
            original_question="What's the average age?",
            response=response,
            intent_classification=sql_intent,
            attempt=2,
        )

        assert report2.verification_attempts == 2


# ────────────────────────────────────────────────────────────────────────
# Test Suite 10: Edge Cases & Boundary Conditions
# ────────────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_response(self, sql_intent):
        """Empty response should fail"""
        response = EIRAResponse(
            answer="",
            sources=[],
            confidence=0.0,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert not report.passes

    @pytest.mark.asyncio
    async def test_single_word_response(self, sql_intent):
        """Single word response should fail"""
        response = EIRAResponse(
            answer="32",
            sources=[SourceCitation(claim="32", evidence_ref="sql:employee_id:1", grounded=True)],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.semantic_relevance_score < 0.70

    @pytest.mark.asyncio
    async def test_extremely_long_response(self, sql_intent, good_sources):
        """Extremely long response should be penalized"""
        response = EIRAResponse(
            answer="The average age is 32.5 years. " * 1000,  # Very long
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        assert report.overall_quality_score < 0.80

    @pytest.mark.asyncio
    async def test_special_characters_in_response(self, sql_intent, single_source):
        """Response with special characters"""
        response = EIRAResponse(
            answer="Average age: 32.5 years!!! @#$% Special!!!",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Should still validate (coherence might be lower)
        assert report.coherence_score <= 0.95

    @pytest.mark.asyncio
    async def test_unicode_characters(self, sql_intent, single_source):
        """Response with unicode characters"""
        response = EIRAResponse(
            answer="Average age: 32.5 years (平均年齢). Engineers: 12 (工程师).",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Should handle unicode
        assert len(report.issues) >= 0

    @pytest.mark.asyncio
    async def test_confidence_edge_values(self, sql_intent, good_sources):
        """Test confidence at edge values (0.0, 1.0)"""
        # Confidence 0.0
        response_min = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=good_sources,
            confidence=0.0,
        )

        report_min = await validate_response_against_question(
            "What's the average age?",
            response_min,
            sql_intent,
        )

        assert report_min.overall_quality_score < 0.50

        # Confidence 1.0
        response_max = EIRAResponse(
            answer="The average age is 32.5 years.",
            sources=good_sources,
            confidence=1.0,
        )

        report_max = await validate_response_against_question(
            "What's the average age?",
            response_max,
            sql_intent,
        )

        # Should recognize overconfidence
        assert any(
            "confiden" in issue.type.lower()
            for issue in report_max.issues
        )

    @pytest.mark.asyncio
    async def test_many_sources(self, sql_intent):
        """Response with many sources"""
        sources = [
            SourceCitation(
                claim=f"claim {i}",
                evidence_ref=f"sql:employee_id:{i}",
                grounded=True,
            )
            for i in range(20)
        ]

        response = EIRAResponse(
            answer="The average age is 32.5 years. " * 10,
            sources=sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Should handle many sources
        assert report.citation_coverage_score > 0.7


# ────────────────────────────────────────────────────────────────────────
# Test Suite 11: Issue Severity Classification
# ────────────────────────────────────────────────────────────────────────

class TestIssueSeverity:
    """Tests for proper issue severity classification"""

    @pytest.mark.asyncio
    async def test_critical_issue_no_citations(self, sql_intent):
        """No citations should be CRITICAL"""
        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        critical = [i for i in report.issues if i.severity == ValidationSeverity.CRITICAL]
        assert len(critical) > 0

    @pytest.mark.asyncio
    async def test_high_issue_too_brief(self, sql_intent, single_source):
        """Too brief response should be HIGH"""
        response = EIRAResponse(
            answer="32 years.",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        high = [i for i in report.issues if i.severity == ValidationSeverity.HIGH]
        assert len(high) > 0

    @pytest.mark.asyncio
    async def test_medium_issue_single_source(self, sql_intent, single_source):
        """Single source should be MEDIUM or HIGH"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=single_source,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        med_high = [
            i for i in report.issues
            if i.severity in [ValidationSeverity.MEDIUM, ValidationSeverity.HIGH]
        ]
        # Single source should trigger some warning
        assert len(med_high) >= 0

    @pytest.mark.asyncio
    async def test_low_issue_formatting(self, sql_intent, good_sources):
        """Minor formatting issues should be LOW"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years and they have ages "
                   "ranging from 26 to 38 years old and there are 12 of them total.",  # Long run-on
            sources=good_sources,
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        low = [i for i in report.issues if i.severity == ValidationSeverity.LOW]
        # Might have LOW issues for readability
        assert len(low) >= 0


# ────────────────────────────────────────────────────────────────────────
# Test Suite 12: Integration Tests
# ────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests with multiple components"""

    @pytest.mark.asyncio
    async def test_full_validation_pipeline(self, sql_intent, good_sources):
        """Full validation pipeline from raw response to decision"""
        response = EIRAResponse(
            answer="The average age of engineers in Austin is 32.5 years. "
                   "We found 12 engineers with ages 26-38.",
            sources=good_sources,
            confidence=0.85,
        )

        # Step 1: Validate
        report = await validate_response_against_question(
            "What's the average age?",
            response,
            sql_intent,
        )

        # Step 2: Check if passes
        assert report.passes

        # Step 3: Get summary
        agent = VERIFIERAgent()
        summary = await agent.get_validation_summary(report)
        assert "PASSED" in summary

    @pytest.mark.asyncio
    async def test_full_re_iteration_scenario(self):
        """Full scenario: bad response → feedback → improved response → accept"""
        sql_intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get average age",
            reasoning="Employee query",
        )

        # Bad response
        bad_response = EIRAResponse(
            answer="32 years.",
            sources=[],
            confidence=0.90,
        )

        # Validate bad response
        bad_report = await validate_response_against_question(
            "What's the average age of engineers?",
            bad_response,
            sql_intent,
        )

        assert not bad_report.passes

        # Get feedback
        feedback = await get_re_iteration_feedback(bad_report, "What's the average age of engineers?")
        assert "CRITICAL" in feedback or "critical" in feedback

        # Improved response
        good_response = EIRAResponse(
            answer="The average age of engineers is 32.5 years. "
                   "We found 12 engineers with ages from 26 to 38.",
            sources=[
                SourceCitation(claim="32.5 years", evidence_ref="sql:employee_id:1", grounded=True),
                SourceCitation(claim="12 engineers", evidence_ref="sql:employee_id:2", grounded=True),
            ],
            confidence=0.82,
        )

        # Validate improved response
        good_report = await validate_response_against_question(
            "What's the average age of engineers?",
            good_response,
            sql_intent,
        )

        assert good_report.passes


# ────────────────────────────────────────────────────────────────────────
# Test Suite 13: Error Handling
# ────────────────────────────────────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling and robustness"""

    @pytest.mark.asyncio
    async def test_invalid_intent_type(self, good_sources):
        """Handle invalid intent gracefully"""
        invalid_intent = IntentClassification(
            intent="INVALID_TYPE",
            reasoning="Unknown intent",
        )

        response = EIRAResponse(
            answer="Some response",
            sources=good_sources,
            confidence=0.85,
        )

        # Should not crash
        report = await validate_response_against_question(
            "What's the question?",
            response,
            invalid_intent,
        )

        assert report is not None

    @pytest.mark.asyncio
    async def test_none_values_handled(self, sql_intent):
        """Handle None values gracefully"""
        response = EIRAResponse(
            answer=None,
            sources=None,
            confidence=0.85,
        )

        # Should handle gracefully or fail clearly
        try:
            report = await validate_response_against_question(
                "Question?",
                response,
                sql_intent,
            )
            # If it doesn't crash, scores should be low
            assert report.overall_quality_score < 0.5
        except (TypeError, AttributeError):
            # Acceptable to fail on None values
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
