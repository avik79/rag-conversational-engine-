"""Wire tool dependencies and agent-as-tool references into EIRA"""
from agents import handoff
from agent_definitions.eira import EIRA, HandoffMetadata
from agent_definitions.vega import VEGA
from agent_definitions.nova import NOVA
from agent_definitions.kira import KIRA
from agent_definitions.axiom import AXIOM
from agent_definitions.sentinel import SENTINEL
from agent_definitions.iris import IRIS
from tools import (
    execute_employee_query,
    validate_sql_query,
    get_schema_snapshot,
    search_weather_embeddings,
    search_news_embeddings,
    validate_chroma_query,
    upsert_to_chroma,
    validate_location_contract,
    generate_embeddings,
    fetch_tavily_weather,
    fetch_tavily_news,
    hitl_gate,
)


def wire_eira_tools():
    """Inject all function tools and agent-as-tool references into EIRA"""
    from agents.extensions.handoff_filters import remove_all_tools

    # Agent-as-tool wrapping
    vega_tool = VEGA.as_tool(
        tool_name="query_employees",
        tool_description="Query employee database via SQL specialist.",
    )
    nova_tool = NOVA.as_tool(
        tool_name="retrieve_rag_context",
        tool_description="Retrieve weather/news context from vector database.",
    )
    kira_tool = KIRA.as_tool(
        tool_name="resolve_location",
        tool_description="Resolve employee office location to canonical city.",
    )
    axiom_tool = AXIOM.as_tool(
        tool_name="validate_query",
        tool_description="Pre-execution validation of SQL and Chroma queries.",
    )
    sentinel_tool = SENTINEL.as_tool(
        tool_name="validate_response",
        tool_description="Post-generation validation of response groundedness.",
    )
    iris_tool = IRIS.as_tool(
        tool_name="trigger_ingestion",
        tool_description="Trigger Tavily ingestion to Chroma.",
    )

    # Wire tools into EIRA
    EIRA.tools = [
        vega_tool,
        nova_tool,
        kira_tool,
        axiom_tool,
        sentinel_tool,
        iris_tool,
        execute_employee_query,
        validate_sql_query,
        get_schema_snapshot,
        search_weather_embeddings,
        search_news_embeddings,
        validate_chroma_query,
        upsert_to_chroma,
        validate_location_contract,
        generate_embeddings,
        fetch_tavily_weather,
        fetch_tavily_news,
        hitl_gate,
    ]

    # Build handoff declarations
    EIRA.handoffs = [
        handoff(
            agent=VEGA,
            tool_name_override="handoff_to_vega",
            tool_description_override=(
                "Hand off to VEGA for complex SQL queries requiring joins, "
                "aggregations, or multi-step employee data retrieval."
            ),
            on_handoff=lambda ctx, data: ctx.context.update({"last_handoff": {"to": "VEGA", "reason": data.reason}}),
            input_type=HandoffMetadata,
            input_filter=remove_all_tools,
        ),
        handoff(
            agent=NOVA,
            tool_name_override="handoff_to_nova",
            tool_description_override=(
                "Hand off to NOVA for conversational RAG queries about news "
                "or weather where NOVA should own the response."
            ),
            on_handoff=lambda ctx, data: ctx.context.update({"last_handoff": {"to": "NOVA", "reason": data.reason}}),
            input_type=HandoffMetadata,
            input_filter=remove_all_tools,
        ),
        handoff(
            agent=IRIS,
            tool_name_override="handoff_to_iris",
            tool_description_override=(
                "Hand off to IRIS to trigger Tavily data ingestion or "
                "re-ingestion of weather/news embeddings."
            ),
            on_handoff=lambda ctx, data: ctx.context.update({"last_handoff": {"to": "IRIS", "reason": data.reason}}),
            input_type=HandoffMetadata,
        ),
    ]


def wire_vega_tools():
    """Inject SQL tools into VEGA"""
    VEGA.tools = [
        validate_sql_query,
        execute_employee_query,
        get_schema_snapshot,
        axiom_tool := AXIOM.as_tool(
            tool_name="validate_sql",
            tool_description="Validate SQL query before execution.",
        ),
    ]


def wire_nova_tools():
    """Inject Chroma tools into NOVA"""
    NOVA.tools = [
        search_weather_embeddings,
        search_news_embeddings,
        validate_chroma_query,
        axiom_tool := AXIOM.as_tool(
            tool_name="validate_chroma",
            tool_description="Validate Chroma filter before query.",
        ),
    ]


def wire_kira_tools():
    """Inject embedding tools into KIRA"""
    from tools.embedding_tools import semantic_location_match
    KIRA.tools = [
        generate_embeddings,
        semantic_location_match,
    ]


def wire_iris_tools():
    """Inject ingestion tools into IRIS"""
    IRIS.tools = [
        fetch_tavily_weather,
        fetch_tavily_news,
        generate_embeddings,
        validate_location_contract,
        upsert_to_chroma,
        hitl_gate,
    ]


def wire_axiom_tools():
    """AXIOM has no sub-tools (pure validator)"""
    AXIOM.tools = []


def wire_sentinel_tools():
    """SENTINEL has no sub-tools (pure validator)"""
    SENTINEL.tools = []


def wire_all_tools():
    """Wire all tools and agents in dependency order"""
    wire_axiom_tools()
    wire_sentinel_tools()
    wire_eira_tools()
    wire_vega_tools()
    wire_nova_tools()
    wire_kira_tools()
    wire_iris_tools()
