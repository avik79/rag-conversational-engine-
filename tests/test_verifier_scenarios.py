"""
VERIFIER Scenario Tests — Real-world use cases

Tests specific real-world scenarios and domain-specific use cases:
  - Employee queries (SQL domain)
  - Weather queries (RAG domain)
  - Cross-domain queries
  - Multi-part questions
  - Ambiguous questions
  - Domain-specific validation

Run: pytest tests/test_verifier_scenarios.py -v
"""

import pytest
from models.pydantic_io import (
    EIRAResponse,
    IntentClassification,
    SourceCitation,
    EmployeeQueryResult,
    EmployeeRow,
)
from tools.verifier_tools import validate_response_against_question


# ────────────────────────────────────────────────────────────────────────
# Scenario 1: Employee SQL Queries
# ────────────────────────────────────────────────────────────────────────

class TestEmployeeQueryScenarios:
    """Tests for employee database query scenarios"""

    @pytest.mark.asyncio
    async def test_avg_age_query_good_response(self):
        """Avg age query with good response"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="SELECT AVG(age) FROM employees WHERE office_location = 'Austin, TX'",
            reasoning="Statistical query on employee age",
        )

        response = EIRAResponse(
            answer="The average age of employees in Austin is 34.2 years. "
                   "We analyzed 18 employees in that location. The ages range from 24 to 58. "
                   "The median age is 33 years. In conclusion, Austin has a relatively experienced team.",
            sources=[
                SourceCitation(
                    claim="34.2 years average",
                    evidence_ref="sql:employee_id:101",
                    grounded=True,
                ),
                SourceCitation(
                    claim="18 employees",
                    evidence_ref="sql:employee_id:102",
                    grounded=True,
                ),
                SourceCitation(
                    claim="age range 24-58",
                    evidence_ref="sql:employee_id:103",
                    grounded=True,
                ),
            ],
            confidence=0.88,
            model_used="claude-3-5-sonnet",
        )

        report = await validate_response_against_question(
            "What's the average age of employees in Austin?",
            response,
            intent,
        )

        assert report.passes
        assert report.overall_quality_score >= 0.80

    @pytest.mark.asyncio
    async def test_department_distribution_query(self):
        """Department distribution query"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="SELECT department, COUNT(*) FROM employees GROUP BY department",
            reasoning="Aggregation query",
        )

        response = EIRAResponse(
            answer="The company has employees across 8 departments. Engineering leads with "
                   "45 employees. Sales has 28 employees. Marketing has 15. HR has 12. Finance "
                   "has 18. Operations has 22. Legal has 8. Product has 32. This shows a strong "
                   "engineering-focused organization.",
            sources=[
                SourceCitation(
                    claim="45 in Engineering",
                    evidence_ref="sql:employee_id:1",
                    grounded=True,
                ),
                SourceCitation(
                    claim="28 in Sales",
                    evidence_ref="sql:employee_id:2",
                    grounded=True,
                ),
                SourceCitation(
                    claim="other departments",
                    evidence_ref="sql:employee_id:3",
                    grounded=True,
                ),
            ],
            confidence=0.90,
        )

        report = await validate_response_against_question(
            "How many employees are in each department?",
            response,
            intent,
        )

        assert report.passes

    @pytest.mark.asyncio
    async def test_single_employee_query(self):
        """Query for specific employee"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="SELECT * FROM employees WHERE name LIKE '%John%'",
            reasoning="Entity search query",
        )

        response = EIRAResponse(
            answer="I found one employee named John. He is 35 years old and works in the "
                   "Engineering department. He is located in Austin, Texas. Based on the records, "
                   "John has been with the company in a technical role.",
            sources=[
                SourceCitation(
                    claim="John, 35 years old",
                    evidence_ref="sql:employee_id:456",
                    grounded=True,
                ),
                SourceCitation(
                    claim="Engineering, Austin",
                    evidence_ref="sql:employee_id:456",
                    grounded=True,
                ),
            ],
            confidence=0.95,
        )

        report = await validate_response_against_question(
            "Tell me about an employee named John",
            response,
            intent,
        )

        assert report.passes

    @pytest.mark.asyncio
    async def test_ambiguous_name_query(self):
        """Query for ambiguous name (multiple matches)"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="SELECT * FROM employees WHERE name LIKE '%Smith%'",
            reasoning="Name search with potential ambiguity",
        )

        response = EIRAResponse(
            answer="Found 3 employees with the surname Smith. First, Sarah Smith is 28 years old "
                   "in Marketing/New York. Second, John Smith is 42 years old in Sales/Boston. "
                   "Third, Michael Smith is 31 years old in Operations/Chicago.",
            sources=[
                SourceCitation(claim="Sarah Smith", evidence_ref="sql:employee_id:201", grounded=True),
                SourceCitation(claim="John Smith", evidence_ref="sql:employee_id:202", grounded=True),
                SourceCitation(claim="Michael Smith", evidence_ref="sql:employee_id:203", grounded=True),
            ],
            confidence=0.92,
        )

        report = await validate_response_against_question(
            "Who is Smith?",
            response,
            intent,
        )

        assert report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 2: Weather/News RAG Queries
# ────────────────────────────────────────────────────────────────────────

class TestWeatherRAGScenarios:
    """Tests for weather/news RAG query scenarios"""

    @pytest.mark.asyncio
    async def test_weather_query_good_response(self):
        """Weather information query"""
        intent = IntentClassification(
            intent="rag_only",
            rag_subquery="Current weather in Austin, Texas",
            reasoning="Weather context query",
        )

        response = EIRAResponse(
            answer="The current weather in Austin is sunny with a temperature of 28°C (82°F). "
                   "The humidity is at 65% and wind speeds are 5-10 mph from the south. "
                   "No precipitation is expected in the next 24 hours. Perfect conditions for outdoor activities.",
            sources=[
                SourceCitation(
                    claim="sunny, 28°C",
                    evidence_ref="chunk_12345678-1234-5678-1234-567812345678",
                    grounded=True,
                ),
                SourceCitation(
                    claim="humidity 65%, wind 5-10 mph",
                    evidence_ref="chunk_87654321-4321-8765-4321-876543218765",
                    grounded=True,
                ),
            ],
            confidence=0.87,
        )

        report = await validate_response_against_question(
            "What's the weather in Austin?",
            response,
            intent,
        )

        assert report.passes

    @pytest.mark.asyncio
    async def test_news_query_response(self):
        """News information query"""
        intent = IntentClassification(
            intent="rag_only",
            rag_subquery="Recent technology news",
            reasoning="News retrieval query",
        )

        response = EIRAResponse(
            answer="Recent technology news shows continued growth in AI. Last week, three major "
                   "announcements were made: a new AI model was released, cloud computing adoption "
                   "increased by 23%, and cybersecurity threats rose. These trends indicate a dynamic "
                   "tech landscape with both opportunities and challenges.",
            sources=[
                SourceCitation(
                    claim="AI model released",
                    evidence_ref="chunk_aaaa1111-bbbb-2222-cccc-3333dddd4444",
                    grounded=True,
                ),
                SourceCitation(
                    claim="cloud adoption +23%",
                    evidence_ref="chunk_bbbb2222-cccc-3333-dddd-4444eeee5555",
                    grounded=True,
                ),
                SourceCitation(
                    claim="cybersecurity threats",
                    evidence_ref="chunk_cccc3333-dddd-4444-eeee-5555ffff6666",
                    grounded=True,
                ),
            ],
            confidence=0.81,
        )

        report = await validate_response_against_question(
            "What's new in technology?",
            response,
            intent,
        )

        assert report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 3: Cross-domain Queries
# ────────────────────────────────────────────────────────────────────────

class TestCrossDomainScenarios:
    """Tests for cross-domain query scenarios (SQL + RAG)"""

    @pytest.mark.asyncio
    async def test_employee_with_weather_context(self):
        """Employee data correlated with weather"""
        intent = IntentClassification(
            intent="cross_domain",
            sql_subquery="SELECT COUNT(*), office_location FROM employees GROUP BY office_location",
            rag_subquery="Current weather in major cities",
            reasoning="Correlate employees with local weather",
        )

        response = EIRAResponse(
            answer="Austin has 18 employees and current weather is sunny, 28°C. New York has 22 employees "
                   "with partly cloudy conditions, 15°C. Seattle has 15 employees with rainy, 12°C. "
                   "Denver has 12 employees with clear skies, 20°C. The sunny locations show strong headcount, "
                   "particularly Austin and New York.",
            sources=[
                SourceCitation(
                    claim="Austin 18 employees",
                    evidence_ref="sql:employee_id:101",
                    grounded=True,
                ),
                SourceCitation(
                    claim="Austin sunny 28°C",
                    evidence_ref="chunk_weather_austin",
                    grounded=True,
                ),
                SourceCitation(
                    claim="NY 22 employees",
                    evidence_ref="sql:employee_id:102",
                    grounded=True,
                ),
                SourceCitation(
                    claim="NY cloudy 15°C",
                    evidence_ref="chunk_weather_ny",
                    grounded=True,
                ),
            ],
            confidence=0.84,
        )

        report = await validate_response_against_question(
            "Compare employee counts and weather across cities",
            response,
            intent,
        )

        assert report.passes

    @pytest.mark.asyncio
    async def test_department_with_news_context(self):
        """Department insights with technology news context"""
        intent = IntentClassification(
            intent="cross_domain",
            sql_subquery="SELECT department, COUNT(*) FROM employees GROUP BY department",
            rag_subquery="Latest industry trends and tech news",
            reasoning="Correlate org structure with market trends",
        )

        response = EIRAResponse(
            answer="Our company has 180 total employees. Engineering (45 employees) aligns well with "
                   "the AI boom reported in recent news. Sales (28 employees) is positioned for the digital "
                   "transformation wave. Product (32 employees) benefits from the increased focus on "
                   "user-centric innovation. Our org structure reflects market demands well.",
            sources=[
                SourceCitation(
                    claim="45 in Engineering",
                    evidence_ref="sql:employee_id:dept_eng",
                    grounded=True,
                ),
                SourceCitation(
                    claim="AI boom trend",
                    evidence_ref="chunk_news_ai",
                    grounded=True,
                ),
                SourceCitation(
                    claim="28 in Sales, 32 in Product",
                    evidence_ref="sql:employee_id:dept_other",
                    grounded=True,
                ),
            ],
            confidence=0.79,
        )

        report = await validate_response_against_question(
            "How does our org structure reflect industry trends?",
            response,
            intent,
        )

        assert report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 4: Multi-part Questions
# ────────────────────────────────────────────────────────────────────────

class TestMultiPartQuestionScenarios:
    """Tests for multi-part question scenarios"""

    @pytest.mark.asyncio
    async def test_three_part_employee_question(self):
        """Question with 3 parts"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get avg age, dept distribution, and location spread",
            reasoning="Multi-part aggregation query",
        )

        response = EIRAResponse(
            answer="First, the average employee age is 33.5 years across the company. "
                   "Second, Engineering leads with 45 employees, followed by Product (32), Sales (28), "
                   "Operations (22), Finance (18), HR (12), Marketing (15), and Legal (8). "
                   "Third, employees are distributed across 10 canonical cities with Austin, New York, "
                   "and Seattle having the most. In summary, we're a young, engineering-heavy, geographically "
                   "diverse team.",
            sources=[
                SourceCitation(claim="avg age 33.5", evidence_ref="sql:employee_id:agg1", grounded=True),
                SourceCitation(claim="dept distribution", evidence_ref="sql:employee_id:agg2", grounded=True),
                SourceCitation(claim="locations", evidence_ref="sql:employee_id:agg3", grounded=True),
            ],
            confidence=0.86,
        )

        report = await validate_response_against_question(
            "What's the average age, department distribution, and location spread?",
            response,
            intent,
        )

        assert report.passes
        assert report.completeness_score >= 0.80

    @pytest.mark.asyncio
    async def test_two_part_comparison_question(self):
        """Comparison between two things"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Compare Engineering vs Sales departments",
            reasoning="Comparative analysis query",
        )

        response = EIRAResponse(
            answer="Engineering vs Sales comparison: "
                   "Engineering has 45 employees with average age 32 years, mostly in Austin and Seattle. "
                   "Sales has 28 employees with average age 36 years, distributed across all cities. "
                   "Engineering is 60% larger and tends to be younger. "
                   "In conclusion, Engineering is our largest department with a younger demographic.",
            sources=[
                SourceCitation(claim="Eng 45, age 32", evidence_ref="sql:employee_id:comp1", grounded=True),
                SourceCitation(claim="Sales 28, age 36", evidence_ref="sql:employee_id:comp2", grounded=True),
            ],
            confidence=0.83,
        )

        report = await validate_response_against_question(
            "Compare Engineering department with Sales department",
            response,
            intent,
        )

        assert report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 5: Problem Responses (Should Fail)
# ────────────────────────────────────────────────────────────────────────

class TestProblematicScenarios:
    """Tests for responses that should fail validation"""

    @pytest.mark.asyncio
    async def test_hallucinated_numbers(self):
        """Response with hallucinated numbers (no sources)"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get employee count",
            reasoning="Count query",
        )

        response = EIRAResponse(
            answer="There are exactly 447 employees in Austin, with average age 31.333 years "
                   "and median salary $147,500. The data shows perfect distribution.",
            sources=[],  # No sources!
            confidence=0.92,  # Overconfident!
        )

        report = await validate_response_against_question(
            "How many employees in Austin?",
            response,
            intent,
        )

        assert not report.passes
        assert any(
            issue.severity.value == "critical"
            for issue in report.issues
        )

    @pytest.mark.asyncio
    async def test_contradictory_response(self):
        """Response that contradicts itself"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get average age",
            reasoning="Statistical query",
        )

        response = EIRAResponse(
            answer="The average age is 32 years. But also 28 years. "
                   "Actually, it could be anywhere from 20 to 40 years. "
                   "Or maybe 35. In conclusion, it's definitely 50 years old.",
            sources=[
                SourceCitation(
                    claim="32 years",
                    evidence_ref="sql:employee_id:1",
                    grounded=True,
                ),
            ],
            confidence=0.75,
        )

        report = await validate_response_against_question(
            "What's the average age?",
            response,
            intent,
        )

        assert not report.passes

    @pytest.mark.asyncio
    async def test_incomplete_answer_partial_response(self):
        """Question asked for multiple things, only answered one"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get age, department, and location",
            reasoning="Multi-part query",
        )

        response = EIRAResponse(
            answer="The average age is 33 years.",
            sources=[
                SourceCitation(
                    claim="33 years",
                    evidence_ref="sql:employee_id:1",
                    grounded=True,
                ),
            ],
            confidence=0.80,
        )

        report = await validate_response_against_question(
            "What's the average age, main department, and primary location?",
            response,
            intent,
        )

        assert not report.passes
        assert report.completeness_score < 0.70

    @pytest.mark.asyncio
    async def test_completely_wrong_domain(self):
        """Response in wrong domain entirely"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get employee data",
            reasoning="Employee query",
        )

        response = EIRAResponse(
            answer="The weather in Austin is sunny today with a high of 28°C.",
            sources=[
                SourceCitation(
                    claim="weather info",
                    evidence_ref="chunk_weather",
                    grounded=True,
                ),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "Tell me about employees in Austin",
            response,
            intent,
        )

        assert not report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 6: Ambiguous & Unclear Questions
# ────────────────────────────────────────────────────────────────────────

class TestAmbiguousQueryScenarios:
    """Tests for ambiguous question scenarios"""

    @pytest.mark.asyncio
    async def test_ambiguous_name_acknowledgment(self):
        """Response acknowledging name ambiguity"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Search for employees named John",
            reasoning="Name search with potential matches",
        )

        response = EIRAResponse(
            answer="There are 3 employees named John. Without more context (like last name or department), "
                   "I can't determine which one you're asking about. The Johns are: "
                   "John Smith (Engineering, 35), John Davis (Sales, 42), John Wilson (Product, 28). "
                   "Could you please clarify which John you're interested in?",
            sources=[
                SourceCitation(claim="John Smith", evidence_ref="sql:employee_id:101", grounded=True),
                SourceCitation(claim="John Davis", evidence_ref="sql:employee_id:102", grounded=True),
                SourceCitation(claim="John Wilson", evidence_ref="sql:employee_id:103", grounded=True),
            ],
            confidence=0.72,
        )

        report = await validate_response_against_question(
            "Tell me about John",
            response,
            intent,
        )

        # Response is good even if it's asking for clarification
        assert report.passes


# ────────────────────────────────────────────────────────────────────────
# Scenario 7: Large Result Set Responses
# ────────────────────────────────────────────────────────────────────────

class TestLargeResultSetScenarios:
    """Tests for responses with large result sets"""

    @pytest.mark.asyncio
    async def test_large_employee_list(self):
        """Response listing many employees"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get all employees in Austin",
            reasoning="List query",
        )

        # Create many sources for large result
        sources = [
            SourceCitation(
                claim=f"Employee {i} info",
                evidence_ref=f"sql:employee_id:{i}",
                grounded=True,
            )
            for i in range(20)
        ]

        response = EIRAResponse(
            answer="Austin office has 20 employees: "
                   + ", ".join([f"Employee {i} (age {30+i})" for i in range(20)])
                   + ". They span across Engineering (8), Product (6), and Sales (6). "
                   "Average age is 39 years.",
            sources=sources,
            confidence=0.88,
        )

        report = await validate_response_against_question(
            "List all employees in Austin office",
            response,
            intent,
        )

        assert report.passes

    @pytest.mark.asyncio
    async def test_department_with_many_subdivisions(self):
        """Response with complex hierarchical info"""
        intent = IntentClassification(
            intent="sql_only",
            sql_subquery="Get Engineering teams",
            reasoning="Hierarchical department query",
        )

        response = EIRAResponse(
            answer="Engineering has 45 employees in 4 teams: "
                   "Backend (12 engineers), Frontend (11), Infrastructure (15), DevOps (7). "
                   "Backend team's average age is 32, Frontend is 28, Infrastructure is 35, DevOps is 33. "
                   "Each team is led by an experienced head with 10+ years experience. "
                   "Overall, Engineering is our strongest department.",
            sources=[
                SourceCitation(claim="45 total", evidence_ref="sql:employee_id:eng_total", grounded=True),
                SourceCitation(claim="team breakdown", evidence_ref="sql:employee_id:eng_teams", grounded=True),
            ],
            confidence=0.85,
        )

        report = await validate_response_against_question(
            "Break down the Engineering team structure",
            response,
            intent,
        )

        assert report.passes


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
