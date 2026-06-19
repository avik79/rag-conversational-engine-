"""LLM configuration with Claude primary"""
import os
from agents import ModelSettings, Runner, RunConfig
import logging

logger = logging.getLogger(__name__)

ANTHROPIC_MODEL = "claude-opus-4-8"

# Shared model settings across all agents
SHARED_MODEL_SETTINGS = ModelSettings(
    temperature=0.3,
    top_p=0.95,
    max_tokens=2048,
)


def get_claude_model():
    """Primary LLM: return model ID string (claude-sonnet-4-5)"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key or "sk-ant" not in api_key:
        logger.warning("ANTHROPIC_API_KEY not properly configured")
    return ANTHROPIC_MODEL


