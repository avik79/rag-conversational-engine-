"""Integration layer for running agents with Anthropic SDK (no OpenAI dependency)"""
import asyncio
import os
from typing import Any
import json
import logging
from anthropic import Anthropic
from db.engine import get_sync_engine
from models.employee import Employee
from models.pydantic_io import SourceCitation
from sqlalchemy import func
from sqlalchemy.orm import Session

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

logger = logging.getLogger(__name__)


class AgentRunContext:
    """Context for agent execution with hook tracking"""
    def __init__(self, user_input: str, turn_count: int, user_name: str = "User"):
        self.user_input = user_input
        self.turn_count = turn_count
        self.user_name = user_name
        self.tool_calls = []
        self.hitl_decisions = []
        self.hitl_gates = []  # New: track HITL gates triggered
        self.response = None
        self.requires_approval = False  # Flag if response blocked by HITL


def get_weather_for_location(location: str) -> str:
    """Get weather for a location using Tavily API"""
    try:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key or not TavilyClient:
            return None

        client = TavilyClient(api_key=api_key)
        response = client.search(f"current weather in {location}", max_results=1)

        if response and response.get("results"):
            result = response["results"][0]
            content_str = result.get('content', '')

            # Parse the string representation of dict
            try:
                # Use ast.literal_eval for safer parsing
                import ast
                content = ast.literal_eval(content_str)
            except:
                try:
                    content = json.loads(content_str)
                except:
                    return f"Weather for {location}: {content_str[:150]}"

            # Extract weather data
            if isinstance(content, dict) and 'current' in content:
                current = content['current']
                temp_f = current.get('temp_f', 'N/A')
                condition_info = current.get('condition', {})
                if isinstance(condition_info, dict):
                    condition = condition_info.get('text', 'Unknown')
                else:
                    condition = str(condition_info)
                humidity = current.get('humidity', 'N/A')
                wind_mph = current.get('wind_mph', 'N/A')

                return f"Weather in {location}: {condition}, {temp_f}°F, Humidity: {humidity}%, Wind: {wind_mph} mph"
            else:
                return f"Weather for {location}: Data available"

        return None
    except Exception as e:
        logger.warning(f"Weather API failed: {type(e).__name__}: {e}")
        return None


def get_employee_location(name: str) -> str:
    """Get employee location from database"""
    engine = get_sync_engine()
    try:
        with Session(engine) as session:
            emp = session.query(Employee).filter(
                Employee.name.ilike(f"%{name}%")
            ).first()

            if emp:
                return emp.office_location
        return None
    except Exception as e:
        logger.error(f"Failed to get employee location: {e}")
        return None


def query_employee_database(query: str) -> str:
    """Query employee database based on natural language query"""
    engine = get_sync_engine()
    query_lower = query.lower()

    try:
        # List top 10 employees from a location
        if ("list" in query_lower or "show" in query_lower) and "employee" in query_lower:
            for city_full in ["New York, NY", "Austin, TX", "Seattle, WA", "Boston, MA",
                           "Atlanta, GA", "Denver, CO", "Chicago, IL", "London, UK",
                           "Miami, FL", "Toronto, CA"]:
                if city_full.split(",")[0].lower() in query_lower:
                    with Session(engine) as session:
                        employees = session.query(Employee).filter(
                            Employee.office_location == city_full
                        ).limit(10).all()

                    if employees:
                        result = f"Top 10 employees in {city_full}:\n"
                        for emp in employees:
                            result += f"- {emp.name} ({emp.department}), Age: {emp.age}\n"
                        return result
                    else:
                        return f"No employees found in {city_full}."

        # Count engineers in a specific location
        if "engineer" in query_lower:
            for city_full in ["New York, NY", "Austin, TX", "Seattle, WA", "Boston, MA",
                           "Atlanta, GA", "Denver, CO", "Chicago, IL", "London, UK",
                           "Miami, FL", "Toronto, CA"]:
                if city_full.split(",")[0].lower() in query_lower:
                    with Session(engine) as session:
                        count = session.query(func.count(Employee.employee_id)).filter(
                            (Employee.department == "Engineering") &
                            (Employee.office_location == city_full)
                        ).scalar()
                    return f"There are {count} engineers in {city_full}."

        # Count employees in a specific location
        if "employee" in query_lower and any(city in query_lower for city in
            ["austin", "new york", "seattle", "boston", "atlanta", "denver",
             "chicago", "london", "miami", "toronto"]):
            for city_full in ["New York, NY", "Austin, TX", "Seattle, WA", "Boston, MA",
                           "Atlanta, GA", "Denver, CO", "Chicago, IL", "London, UK",
                           "Miami, FL", "Toronto, CA"]:
                if city_full.split(",")[0].lower() in query_lower:
                    with Session(engine) as session:
                        count = session.query(func.count(Employee.employee_id)).filter(
                            Employee.office_location == city_full
                        ).scalar()
                    return f"There are {count} employees in {city_full}."

        # Count employees in a department
        departments = ["Engineering", "Sales", "Finance", "Marketing", "Operations",
                      "Product", "Human Resources", "Legal"]
        for dept in departments:
            if dept.lower() in query_lower:
                with Session(engine) as session:
                    count = session.query(func.count(Employee.employee_id)).filter(
                        Employee.department == dept
                    ).scalar()
                    # Get some sample employees
                    samples = session.query(Employee).filter(
                        Employee.department == dept
                    ).limit(3).all()

                result = f"There are {count} employees in the {dept} department.\n"
                if samples:
                    result += "Sample employees:\n"
                    for emp in samples:
                        result += f"- {emp.name}, {emp.office_location}, Age: {emp.age}\n"
                return result

        # Default: show general stats
        with Session(engine) as session:
            total = session.query(func.count(Employee.employee_id)).scalar()
            avg_age = session.query(func.avg(Employee.age)).scalar()

            # Get breakdown by department
            dept_stats = session.query(Employee.department, func.count(Employee.employee_id)).group_by(Employee.department).all()

        result = f"We have {total} employees with an average age of {avg_age:.1f} years.\n\nBreakdown by department:\n"
        for dept, count in dept_stats:
            result += f"- {dept}: {count}\n"
        return result

    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return f"I can query employee data. Ask about employees by department, location, or try 'list employees in Austin'"


async def run_eira_agent(
    user_input: str,
    turn_count: int,
    user_name: str = "User",
    hooks: dict = None,
) -> AgentRunContext:
    """Execute EIRA agent using Anthropic SDK directly"""
    from models.pydantic_io import EIRAResponse

    context = AgentRunContext(user_input, turn_count, user_name)

    # Set a default response in case anything fails
    context.response = EIRAResponse(
        answer=f"I'm EIRA, your conversational assistant. You asked: '{user_input[:80]}'",
        sources=[],
        confidence=0.6,
        model_used="claude-3.5-sonnet",
    )

    try:
        logger.info(f"Running EIRA: turn={turn_count}, user={user_name}")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set, using demo mode")
            return context

        # Try to call Claude API
        response = None
        client = None

        try:
            client = Anthropic(api_key=api_key)
        except Exception as e:
            logger.warning(f"Failed to create Anthropic client: {e}")
            return context

        # Check for weather query for an employee (FIRST PRIORITY)
        if "weather" in user_input.lower():
            # Extract employee name - try multiple patterns
            words = user_input.split()
            potential_name = None

            # Pattern 1: "for/of/at NAME"
            for i, word in enumerate(words):
                if word.lower() in ["for", "of", "at"]:
                    potential_name = " ".join(words[i+1:]).strip()
                    if potential_name:
                        break

            # Pattern 2: If still not found, take everything after "weather"
            if not potential_name:
                try:
                    weather_idx = user_input.lower().find("weather")
                    after_weather = user_input[weather_idx+7:].strip()
                    # Remove punctuation and common words
                    potential_name = after_weather.replace("?", "").replace(".", "").strip()
                except:
                    pass

            if potential_name:
                # Clean punctuation from name
                potential_name = potential_name.strip().rstrip("?.,!")
                logger.info(f"Extracted potential employee name: {potential_name}")
                location = get_employee_location(potential_name)
                if location:
                    weather = get_weather_for_location(location)
                    if weather:
                        context.response = EIRAResponse(
                            answer=weather,
                            sources=[SourceCitation(
                                claim=weather,
                                evidence_ref=f"tavily:{location}",
                                grounded=True
                            )],
                            confidence=0.85,
                            model_used="weather-api",
                        )
                        logger.info(f"Returned weather for {potential_name}")
                        return context
                    else:
                        # Employee found but weather API failed
                        context.response = EIRAResponse(
                            answer=f"Employee {potential_name} is located in {location}. Weather data unavailable at this time.",
                            sources=[SourceCitation(
                                claim=f"Located in {location}",
                                evidence_ref="sql:employee_table",
                                grounded=True
                            )],
                            confidence=0.7,
                            model_used="database-query",
                        )
                        logger.info(f"Weather API failed for {potential_name}")
                        return context
                else:
                    logger.debug(f"Employee not found: {potential_name}")

        # Try database query for employee data
        db_answer = query_employee_database(user_input)
        if db_answer and "Can query employee data" not in db_answer:
            response = EIRAResponse(
                answer=db_answer,
                sources=[SourceCitation(
                    claim=db_answer,
                    evidence_ref="sql:employee_table",
                    grounded=True
                )],
                confidence=0.95,
                model_used="database-query",
            )

            # Apply HITL checks before returning
            await apply_hitl_checks(context, response)

            context.response = response
            return context

        system_prompt = f"""You are EIRA, an intelligent assistant.
You have access to employee data (500 employees), weather services, and news.
Turn: {turn_count}, User: {user_name}
Respond as JSON: {{"answer": "response", "confidence": 0.0-1.0, "sources": []}}"""

        # Try available models
        for model_name in ["claude-3-5-sonnet-20241022", "claude-3-sonnet-20240229"]:
            try:
                response = await asyncio.to_thread(
                    client.messages.create,
                    model=model_name,
                    max_tokens=1024,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_input}]
                )
                logger.info(f"Got response from {model_name}")
                response_text = response.content[0].text

                # Parse response
                try:
                    result = json.loads(response_text)
                    context.response = EIRAResponse(
                        answer=result.get("answer", response_text),
                        sources=result.get("sources", []),
                        confidence=float(result.get("confidence", 0.8)),
                        model_used="claude-3.5-sonnet",
                    )
                except (json.JSONDecodeError, ValueError, TypeError):
                    context.response = EIRAResponse(
                        answer=response_text,
                        sources=[],
                        confidence=0.7,
                        model_used="claude-3.5-sonnet",
                    )

                logger.info("EIRA completed successfully")
                return context

            except Exception as e:
                logger.warning(f"Model {model_name} failed: {type(e).__name__}: {str(e)[:60]}")
                continue

        # If we get here, all models failed - return default response
        logger.warning("All models failed, using demo response")
        return context

    except Exception as e:
        logger.error(f"Unexpected error in run_eira_agent: {type(e).__name__}: {e}")
        # Return the default response that was set at the start
        return context


async def handle_hitl_decision(
    decision_id: str,
    approved: bool,
    approval_reason: str = None,
) -> HITLDecision:
    """Process HITL gate decision"""
    logger.info(f"HITL Decision: id={decision_id}, approved={approved}")

    return HITLDecision(
        decision_id=decision_id,
        trigger_reason="user_approved" if approved else "user_denied",
        approved=approved,
        approval_reason=approval_reason,
    )


def format_tool_trace(trace: dict) -> str:
    """Format tool execution trace for display"""
    return f"""
    **Tool**: {trace['tool']}
    **Latency**: {trace['latency_ms']:.0f}ms
    **Timestamp**: {trace['timestamp']}
    **Status**: {trace.get('status', 'unknown')}
    """


def format_response(response: EIRAResponse) -> str:
    """Format agent response for display"""
    output = f"**Response**:\n{response.answer}\n\n"

    if response.sources:
        output += "**Sources**:\n"
        for source in response.sources:
            output += f"- {source.evidence_ref}\n"
        output += "\n"

    output += f"**Confidence**: {response.confidence:.1%}"

    return output


async def apply_hitl_checks(context: AgentRunContext, response: EIRAResponse) -> None:
    """Apply human-in-the-loop checks to a response"""
    from tools.hitl_tools import (
        check_confidence_threshold,
        create_approval_request,
    )

    CONFIDENCE_THRESHOLD = 0.75

    # Check confidence level
    gate = await check_confidence_threshold(response.confidence, CONFIDENCE_THRESHOLD)
    if gate:
        approval_request = await create_approval_request(gate)
        context.hitl_gates.append(gate)
        context.hitl_decisions.append(approval_request)
        context.requires_approval = True
        logger.warning(
            f"HITL gate triggered: {gate.trigger_reason} "
            f"(confidence {response.confidence:.2f} < {CONFIDENCE_THRESHOLD})"
        )

    # Additional checks could be added here (data freshness, SQL validation, etc.)
