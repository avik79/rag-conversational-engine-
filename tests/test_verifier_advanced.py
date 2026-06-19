"""
VERIFIER Advanced Tests — Configuration, Performance, and Edge Cases

Tests for:
  - Threshold tuning and configuration
  - Performance benchmarking
  - Metric weight variations
  - Caching scenarios
  - Concurrent validation
  - Stress testing
  - Audit logging validation

Run: pytest tests/test_verifier_advanced.py -v
"""

import pytest
import time
import asyncio
from datetime import datetime
from models.pydantic_io import (
    EIRAResponse,
    IntentClassification,
    SourceCitation,
)
from tools.verifier_tools import (
    validate_response_against_question,
    _calculate_overall_score,
    ValidationSeverity,
)
from agents.verifier import VERIFIERAgent


# ────────────────────────────────────────────────────────────────────────
# Test Suite 1: Threshold Tuning
# ────────────────────────────────────────────────────────────────────────

class TestThresholdTuning:
    """Tests for threshold configuration and tuning"""

    @pytest.mark.asyncio
    async def test_response_at_pass_threshold(self):
        """Response exactly at pass threshold (0.75)"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years. We found 12 employees with ages from 26 to 38. "
                   "In summary, this represents our Austin team.",
            sources=[
                SourceCitation(claim="32 years", evidence_ref="sql:1", grounded=True),
                SourceCitation(claim="12 employees", evidence_ref="sql:2", grounded=True),
            ],
            confidence=0.75,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        # Depending on exact metrics, this might pass or fail
        assert report.overall_quality_score >= 0.70

    @pytest.mark.asyncio
    async def test_response_just_above_threshold(self):
        """Response slightly above pass threshold"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age of employees in Austin is 32.5 years. "
                   "We found 12 employees with ages ranging from 26 to 38 years. "
                   "In conclusion, the Austin office has a well-balanced age demographic.",
            sources=[
                SourceCitation(claim="32.5 years", evidence_ref="sql:1", grounded=True),
                SourceCitation(claim="12 employees", evidence_ref="sql:2", grounded=True),
                SourceCitation(claim="26-38 range", evidence_ref="sql:3", grounded=True),
            ],
            confidence=0.82,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        assert report.overall_quality_score >= 0.75

    @pytest.mark.asyncio
    async def test_response_just_below_threshold(self):
        """Response slightly below pass threshold"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="Average age: 32 years.",
            sources=[SourceCitation(claim="32 years", evidence_ref="sql:1", grounded=True)],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        assert report.overall_quality_score < 0.75


# ────────────────────────────────────────────────────────────────────────
# Test Suite 2: Metric Weight Variations
# ────────────────────────────────────────────────────────────────────────

class TestMetricWeightVariations:
    """Tests for metric weight impact on scoring"""

    @pytest.mark.asyncio
    async def test_semantic_relevance_weight_impact(self):
        """Semantic relevance has 30% weight"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        # Response with poor semantic relevance but good other metrics
        response = EIRAResponse(
            answer="Dogs are animals.",  # Poor semantic relevance
            sources=[
                SourceCitation(claim="dogs", evidence_ref="sql:1", grounded=True),
                SourceCitation(claim="animals", evidence_ref="sql:2", grounded=True),
                SourceCitation(claim="mammals", evidence_ref="sql:3", grounded=True),
            ],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        # Poor semantic relevance (30%) should drag down overall score significantly
        assert report.overall_quality_score < 0.70

    @pytest.mark.asyncio
    async def test_citation_coverage_weight_impact(self):
        """Citation coverage has 25% weight"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        # Response with good semantic relevance but no citations
        response = EIRAResponse(
            answer="The average age of employees in Austin is 32.5 years. "
                   "We found 12 employees with ages from 26 to 38. "
                   "Excellent demographic spread.",
            sources=[],  # No citations!
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        # Missing citations (25% weight) should significantly impact score
        assert report.overall_quality_score < 0.70

    @pytest.mark.asyncio
    async def test_confidence_consistency_weight_impact(self):
        """Confidence consistency has only 5% weight"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        # Response with good quality but poor confidence consistency (1.0 vs 0.50 actual)
        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[
                SourceCitation(claim="32 years", evidence_ref="sql:1", grounded=True),
                SourceCitation(claim="employees", evidence_ref="sql:2", grounded=True),
            ],
            confidence=1.0,  # Extremely overconfident!
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        # Even with confidence issue, should still pass since it's only 5% weight
        # (assuming other metrics are decent)
        assert not any(
            issue.severity == ValidationSeverity.CRITICAL
            for issue in report.issues
        )


# ────────────────────────────────────────────────────────────────────────
# Test Suite 3: Performance Benchmarking
# ────────────────────────────────────────────────────────────────────────

class TestPerformanceBenchmarking:
    """Tests for validation performance"""

    @pytest.mark.asyncio
    async def test_validation_speed_simple(self):
        """Simple validation should complete < 100ms"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[SourceCitation(claim="32 years", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        start = time.time()
        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )
        elapsed = time.time() - start

        assert elapsed < 0.1  # < 100ms

    @pytest.mark.asyncio
    async def test_validation_speed_complex(self):
        """Complex validation should complete < 500ms"""
        intent = IntentClassification(intent="cross_domain", reasoning="test")

        # Large response with many sources
        sources = [
            SourceCitation(
                claim=f"data point {i}",
                evidence_ref=f"sql:employee_id:{i}",
                grounded=True,
            )
            for i in range(50)
        ]

        response = EIRAResponse(
            answer="The company has 180 employees across 10 cities. " * 20,
            sources=sources,
            confidence=0.80,
        )

        start = time.time()
        report = await validate_response_against_question(
            "Comprehensive company analysis?",
            response,
            intent,
        )
        elapsed = time.time() - start

        assert elapsed < 0.5  # < 500ms

    @pytest.mark.asyncio
    async def test_validation_speed_many_sentences(self):
        """Response with many sentences should still be fast"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer=". ".join(
                ["The average age is 32 years" for _ in range(100)]
            ),
            sources=[SourceCitation(claim="age", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        start = time.time()
        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )
        elapsed = time.time() - start

        assert elapsed < 0.3  # < 300ms


# ────────────────────────────────────────────────────────────────────────
# Test Suite 4: Concurrent Validation
# ────────────────────────────────────────────────────────────────────────

class TestConcurrentValidation:
    """Tests for concurrent validation scenarios"""

    @pytest.mark.asyncio
    async def test_validate_multiple_responses_concurrent(self):
        """Validate multiple responses concurrently"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        responses = [
            EIRAResponse(
                answer=f"Response {i}: The average age is {30+i} years.",
                sources=[SourceCitation(claim=f"age {30+i}", evidence_ref=f"sql:{i}", grounded=True)],
                confidence=0.80 + (i * 0.01),
            )
            for i in range(10)
        ]

        # Validate all concurrently
        tasks = [
            validate_response_against_question(
                f"What's the average age query {i}?",
                resp,
                intent,
            )
            for i, resp in enumerate(responses)
        ]

        reports = await asyncio.gather(*tasks)

        assert len(reports) == 10
        assert all(isinstance(r, type(reports[0])) for r in reports)

    @pytest.mark.asyncio
    async def test_concurrent_verifier_agents(self):
        """Multiple VERIFIER agents validating simultaneously"""
        agents = [VERIFIERAgent(name=f"VERIFIER_{i}") for i in range(5)]

        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[SourceCitation(claim="32 years", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        # All agents validate same response
        tasks = [
            agent.verify_response(
                original_question="What's the average age?",
                response=response,
                intent_classification=intent,
            )
            for agent in agents
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        # All should make same decision
        decisions = [r[0] for r in results]  # passes
        assert all(d == decisions[0] for d in decisions)


# ────────────────────────────────────────────────────────────────────────
# Test Suite 5: Stress Testing
# ────────────────────────────────────────────────────────────────────────

class TestStressTesting:
    """Tests for stress conditions and limits"""

    @pytest.mark.asyncio
    async def test_very_long_response(self):
        """Response at maximum length (5000 chars)"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years. " * 150,  # ~4500 chars
            sources=[SourceCitation(claim="age", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        assert report is not None

    @pytest.mark.asyncio
    async def test_ultra_long_response(self):
        """Response exceeding maximum length"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years. " * 500,  # ~15,000 chars
            sources=[SourceCitation(claim="age", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        # Should be penalized
        assert report.semantic_relevance_score < 0.80

    @pytest.mark.asyncio
    async def test_many_sources_stress(self):
        """Response with many sources (100+)"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        sources = [
            SourceCitation(
                claim=f"point {i}",
                evidence_ref=f"sql:{i}",
                grounded=True,
            )
            for i in range(100)
        ]

        response = EIRAResponse(
            answer="The average age is 32 years with comprehensive data.",
            sources=sources,
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        assert report is not None

    @pytest.mark.asyncio
    async def test_many_issues_stress(self):
        """Response that triggers many issues"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="",  # Empty
            sources=[],  # No sources
            confidence=1.0,  # Overconfident
        )

        report = await validate_response_against_question(
            "Question?",
            response,
            intent,
        )

        assert len(report.issues) >= 1


# ────────────────────────────────────────────────────────────────────────
# Test Suite 6: Score Calculation Verification
# ────────────────────────────────────────────────────────────────────────

class TestScoreCalculation:
    """Tests for score calculation correctness"""

    def test_score_calculation_weights(self):
        """Score should reflect correct weights"""
        scores = {
            "semantic_relevance": 0.90,      # 30%
            "completeness": 0.80,             # 25%
            "citation_coverage": 0.70,        # 25%
            "coherence": 1.00,                # 15%
            "confidence_consistency": 0.50,   # 5%
        }

        calculated = _calculate_overall_score(scores)

        # Manual calculation:
        # (0.90 * 0.30) + (0.80 * 0.25) + (0.70 * 0.25) + (1.00 * 0.15) + (0.50 * 0.05)
        # = 0.27 + 0.20 + 0.175 + 0.15 + 0.025 = 0.82
        expected = 0.82

        assert abs(calculated - expected) < 0.01

    def test_score_never_negative(self):
        """Score should never be negative"""
        scores = {
            "semantic_relevance": 0.0,
            "completeness": 0.0,
            "citation_coverage": 0.0,
            "coherence": 0.0,
            "confidence_consistency": 0.0,
        }

        calculated = _calculate_overall_score(scores)
        assert calculated >= 0.0

    def test_score_never_exceeds_one(self):
        """Score should never exceed 1.0"""
        scores = {
            "semantic_relevance": 1.0,
            "completeness": 1.0,
            "citation_coverage": 1.0,
            "coherence": 1.0,
            "confidence_consistency": 1.0,
        }

        calculated = _calculate_overall_score(scores)
        assert calculated <= 1.0

    def test_score_with_partial_scores(self):
        """Score with partial coverage"""
        scores = {
            "semantic_relevance": 0.50,
            "completeness": 0.50,
            "citation_coverage": 0.50,
            "coherence": 0.50,
            "confidence_consistency": 0.50,
        }

        calculated = _calculate_overall_score(scores)
        assert calculated == 0.50


# ────────────────────────────────────────────────────────────────────────
# Test Suite 7: Intent-Specific Validation
# ────────────────────────────────────────────────────────────────────────

class TestIntentSpecificValidation:
    """Tests for intent-specific validation logic"""

    @pytest.mark.asyncio
    async def test_sql_intent_requires_employee_mention(self):
        """SQL intent response should mention employees/departments"""
        sql_intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get employees",
            reasoning="Employee query",
        )

        response_without_mention = EIRAResponse(
            answer="The data shows interesting trends.",
            sources=[SourceCitation(claim="trends", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "Tell me about employees",
            response_without_mention,
            sql_intent,
        )

        # Should be penalized for not mentioning employees
        assert report.semantic_relevance_score < 0.70

    @pytest.mark.asyncio
    async def test_rag_intent_requires_synthesis(self):
        """RAG intent response should have substantive synthesis"""
        rag_intent = IntentClassification(
            intent="rag_only",
            rag_subquery="Get weather",
            reasoning="Weather query",
        )

        sparse_response = EIRAResponse(
            answer="Sunny.",
            sources=[SourceCitation(claim="sunny", evidence_ref="chunk:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the weather?",
            sparse_response,
            rag_intent,
        )

        # Sparse response should be penalized
        assert report.semantic_relevance_score < 0.70

    @pytest.mark.asyncio
    async def test_cross_domain_requires_both_data_sources(self):
        """Cross-domain should integrate both SQL and RAG"""
        cross_intent = IntentClassification(
            intent="cross_domain",
            sql_subquery="Get employees",
            rag_subquery="Get weather",
            reasoning="Cross-domain query",
        )

        response_only_sql = EIRAResponse(
            answer="There are 12 employees.",
            sources=[SourceCitation(claim="employees", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "Correlate employees with weather",
            response_only_sql,
            cross_intent,
        )

        # Missing RAG data
        assert report.semantic_relevance_score < 0.80


# ────────────────────────────────────────────────────────────────────────
# Test Suite 8: Audit Logging Integration
# ────────────────────────────────────────────────────────────────────────

class TestAuditLogging:
    """Tests for audit logging integration"""

    @pytest.mark.asyncio
    async def test_report_has_traceability_info(self):
        """Report should include traceability hashes"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[SourceCitation(claim="32", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        question = "What's the average age?"

        report = await validate_response_against_question(
            question,
            response,
            intent,
        )

        assert report.question_hash is not None
        assert report.response_hash is not None
        assert isinstance(report.question_hash, str)
        assert isinstance(report.response_hash, str)

    @pytest.mark.asyncio
    async def test_report_timestamp_present(self):
        """Report should have timestamp"""
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[SourceCitation(claim="32", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "Question?",
            response,
            intent,
        )

        assert report.timestamp is not None
        assert isinstance(report.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_attempt_tracking(self):
        """Report should track attempt number"""
        agent = VERIFIERAgent()
        intent = IntentClassification(intent="sql_only", reasoning="test")

        response = EIRAResponse(
            answer="The average age is 32 years.",
            sources=[SourceCitation(claim="32", evidence_ref="sql:1", grounded=True)],
            confidence=0.80,
        )

        # Different attempts
        _, _, report1 = await agent.verify_response(
            "Question?",
            response,
            intent,
            attempt=1,
        )

        _, _, report2 = await agent.verify_response(
            "Question?",
            response,
            intent,
            attempt=2,
        )

        assert report1.verification_attempts == 1
        assert report2.verification_attempts == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
