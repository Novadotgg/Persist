import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.agents.orchestrator import (
    agent_graph,
    parse_llm_json,
    planner_node,
    executor_node,
    AgentState
)

# ==========================================
# 1. GRAPH COMPILATION TESTS
# ==========================================

def test_graph_compilation():
    """
    Verify the LangGraph compiles correctly and has registry nodes.
    """
    assert agent_graph is not None
    # Ensure planner and executor nodes exist in the workflow graph structure
    assert "planner" in agent_graph.nodes
    assert "executor" in agent_graph.nodes


# ==========================================
# 2. JSON PARSER UTILITY TESTS
# ==========================================

def test_parse_llm_json_clean():
    """
    Verify parse_llm_json parses clean JSON.
    """
    raw = '{"status": "COMPLETED", "response": "Hello"}'
    parsed = parse_llm_json(raw)
    assert parsed["status"] == "COMPLETED"
    assert parsed["response"] == "Hello"


def test_parse_llm_json_markdown():
    """
    Verify parse_llm_json extracts and parses JSON enclosed in markdown code fences.
    """
    raw = '```json\n{"status": "PLANNING", "tool_calls": []}\n```'
    parsed = parse_llm_json(raw)
    assert parsed["status"] == "PLANNING"
    assert parsed["tool_calls"] == []


# ==========================================
# 3. PLANNER NODE TESTS
# ==========================================

@pytest.mark.asyncio
@patch("app.agents.orchestrator.call_llm")
async def test_planner_node_generates_plan(mock_llm):
    """
    Verify planner_node parses planning tool calls correctly.
    """
    mock_llm.return_value = '{"status": "PLANNING", "tool_calls": [{"tool_name": "telegram_send_alert", "args": {}}]}'
    
    state = AgentState(
        user_query="Send telegram notification",
        chat_history=[],
        context=[],
        plan=[],
        current_step_index=0,
        tool_outputs=[],
        response="",
        pending_approval=None,
        status="PLANNING",
        db_session=None
    )
    
    res_state = await planner_node(state)
    
    assert res_state["status"] == "EXECUTING"
    assert len(res_state["plan"]) == 1
    assert res_state["plan"][0]["tool_name"] == "telegram_send_alert"
    assert res_state["current_step_index"] == 0


@pytest.mark.asyncio
@patch("app.agents.orchestrator.call_llm")
async def test_planner_node_direct_response(mock_llm):
    """
    Verify planner_node returns direct responses when no tools are needed.
    """
    mock_llm.return_value = '{"status": "COMPLETED", "response": "Yes, I can help."}'
    
    state = AgentState(
        user_query="Hello",
        chat_history=[],
        context=[],
        plan=[],
        current_step_index=0,
        tool_outputs=[],
        response="",
        pending_approval=None,
        status="PLANNING",
        db_session=None
    )
    
    res_state = await planner_node(state)
    
    assert res_state["status"] == "COMPLETED"
    assert res_state["response"] == "Yes, I can help."


# ==========================================
# 4. EXECUTOR NODE & HITL TESTS
# ==========================================

@pytest.mark.asyncio
@patch("app.agents.tools.TelegramSendAlertTool.run")
async def test_executor_node_runs_safe_tool(mock_run):
    """
    Verify executor_node executes non-sensitive tools inline.
    """
    mock_run.return_value = {"ok": True}
    
    state = AgentState(
        user_query="Send test alert",
        chat_history=[],
        context=[],
        plan=[{"tool_name": "telegram_send_alert", "args": {"bot_token": "token", "chat_id": "123", "text": "hi"}}],
        current_step_index=0,
        tool_outputs=[],
        response="",
        pending_approval=None,
        status="EXECUTING",
        db_session=None
    )
    
    res_state = await executor_node(state)
    
    assert res_state["status"] == "EXECUTING"
    assert res_state["current_step_index"] == 1
    assert len(res_state["tool_outputs"]) == 1
    assert res_state["tool_outputs"][0]["tool"] == "telegram_send_alert"
    assert res_state["tool_outputs"][0]["output"] == {"ok": True}
    mock_run.assert_called_once_with(bot_token="token", chat_id="123", text="hi", db=None, user_id=None)


@pytest.mark.asyncio
async def test_executor_node_pauses_on_hitl():
    """
    Verify executor_node pauses execution and populates pending_approval for sensitive tools.
    """
    state = AgentState(
        user_query="Create jira issue",
        chat_history=[],
        context=[],
        plan=[{"tool_name": "jira_create_issue", "args": {"project_key": "KAN", "summary": "Fix login"}}],
        current_step_index=0,
        tool_outputs=[],
        response="",
        pending_approval=None,
        status="EXECUTING",
        db_session=None
    )
    
    res_state = await executor_node(state)
    
    assert res_state["status"] == "PAUSED"
    assert res_state["current_step_index"] == 0
    assert res_state["pending_approval"] is not None
    assert res_state["pending_approval"]["integration"] == "jira"
    assert res_state["pending_approval"]["action_type"] == "jira_create_issue"
    assert res_state["pending_approval"]["payload"] == {"project_key": "KAN", "summary": "Fix login"}
