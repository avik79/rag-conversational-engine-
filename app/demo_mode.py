"""Demo mode: Mock agent responses without requiring LLM APIs"""
from models.pydantic_io import EIRAResponse, SourceCitation
import random


def get_demo_response(user_input: str) -> EIRAResponse:
    """Generate demo response based on user input"""

    lower_input = user_input.lower()

    # SQL-only queries
    if any(word in lower_input for word in ["find", "engineer", "employee", "who", "department", "seattle", "austin", "york"]):
        return EIRAResponse(
            answer="Found 12 engineers in Seattle. Names: Alice Johnson (age 32), Bob Smith (age 45), Carol White (age 28). All work in the Engineering department.",
            sources=[
                SourceCitation(
                    claim="12 engineers found",
                    evidence_ref="sql:query:engineering_seattle",
                    grounded=True
                )
            ],
            confidence=0.95,
            model_used="claude-sonnet-4-5"
        )

    # RAG queries
    if any(word in lower_input for word in ["weather", "temperature", "forecast", "rain", "sunny"]):
        return EIRAResponse(
            answer="Current weather in Austin, TX: Sunny, 95°F (35°C). Wind: 8 mph. Low: 72°F. Humidity: 45%. Perfect weather for outdoor activities!",
            sources=[
                SourceCitation(
                    claim="Sunny, 95°F",
                    evidence_ref="chroma:weather_embeddings:austin_20260612",
                    grounded=True
                )
            ],
            confidence=0.88,
            model_used="claude-sonnet-4-5"
        )

    # Cross-domain
    if any(word in lower_input for word in ["employee", "weather", "office", "location"]) or \
       ("employee" in lower_input and "weather" in lower_input):
        return EIRAResponse(
            answer="We have 50 employees in Austin, TX. Current weather: Sunny 95°F. Perfect conditions! Our Seattle office (12 employees) has partly cloudy skies and 68°F.",
            sources=[
                SourceCitation(
                    claim="50 employees in Austin",
                    evidence_ref="sql:employees:austin_count",
                    grounded=True
                ),
                SourceCitation(
                    claim="Sunny 95°F",
                    evidence_ref="chroma:weather_embeddings:austin",
                    grounded=True
                )
            ],
            confidence=0.92,
            model_used="claude-sonnet-4-5"
        )

    # Default response
    return EIRAResponse(
        answer=f"You asked: '{user_input}'. This is a demo mode response. In production, this would query our employee database and weather APIs for real data.",
        sources=[
            SourceCitation(
                claim="Demo mode active",
                evidence_ref="system:demo_mode",
                grounded=True
            )
        ],
        confidence=0.50,
        model_used="claude-sonnet-4-5"
    )
