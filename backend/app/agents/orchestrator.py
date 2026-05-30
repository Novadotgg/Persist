import json
import re
import structlog
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.services.ai_service import call_llm
from app.agents.tools import tools_registry, DB_TOOLS

logger = structlog.get_logger()

# Define the state dictionary format
class AgentState(TypedDict):
    user_query: str
    chat_history: List[Dict[str, str]]
    context: List[str]
    plan: List[Dict[str, Any]]
    current_step_index: int
    tool_outputs: List[Dict[str, Any]]
    response: str
    pending_approval: Optional[Dict[str, Any]]
    status: str  # "PLANNING", "EXECUTING", "PAUSED", "COMPLETED", "FAILED"
    db_session: Any  # Carries active DB session for DB-based tools
    user_id: str


def parse_llm_json(raw_text: str) -> Dict[str, Any]:
    """
    Robustly extracts and parses a JSON object from LLM output.
    Handles markdown fences, prose before/after JSON, and partial/truncated responses.
    """
    def repair_json(text_to_repair: str) -> str:
        in_string = False
        escape = False
        stack = []
        for char in text_to_repair:
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char in '{[':
                    stack.append(char)
                elif char in ']}':
                    if not stack:
                        continue
                    if char == '}' and stack[-1] == '{':
                        stack.pop()
                    elif char == ']' and stack[-1] == '[':
                        stack.pop()
        for opener in reversed(stack):
            if opener == '{':
                text_to_repair += '}'
            elif opener == '[':
                text_to_repair += ']'
        return text_to_repair

    text = raw_text.strip()

    # 1. Strip markdown code fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # 2. Try direct parse first
    try:
        return json.loads(text)
    except Exception:
        pass

    # 3. Try direct parse after repairing
    try:
        return json.loads(repair_json(text))
    except Exception:
        pass

    # 4. Extract the first {...} block (with matching braces if possible)
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 5. Extract from the first '{' to the end of string, and attempt to repair it
    first_brace = text.find('{')
    if first_brace != -1:
        candidate = text[first_brace:]
        try:
            return json.loads(candidate)
        except Exception:
            pass
        try:
            return json.loads(repair_json(candidate))
        except Exception:
            pass

    # 6. Final fallback — treat the raw text as the assistant's answer
    logger.error("Failed to parse LLM response as JSON", raw_text=raw_text[:200])
    return {
        "status": "COMPLETED",
        "response": text
    }

async def planner_node(state: AgentState) -> AgentState:
    """
    State node that decides the execution path (plan) or constructs final response.
    """
    logger.info("Planner Node: Evaluating state", step=state["current_step_index"])
    
    # 1. If we already completed or paused, do not re-plan
    if state["status"] in ["COMPLETED", "PAUSED", "FAILED"]:
        return state

    # 2. If the plan was created and all steps are executed, generate final response
    if state["plan"] and state["current_step_index"] >= len(state["plan"]):
        # Summarize executed tool outputs for user
        outputs_str = json.dumps(state["tool_outputs"], indent=2)
        system_prompt = "You are a Personal AI Assistant. Write a concise, helpful summary of the tasks completed."
        prompt = (
            f"User Query: {state['user_query']}\n"
            f"Completed Tasks Outputs:\n{outputs_str}\n\n"
            "Provide your final friendly response to the user."
        )
        response_text = await call_llm(
            model=settings.PRIMARY_MODEL,
            prompt=prompt,
            system_prompt=system_prompt,
            timeout=60.0
        )
        state["response"] = response_text
        state["status"] = "COMPLETED"
        return state

    # 3. If plan is empty, generate initial steps list using LLM
    from app.core.config import settings as _s
    tg_token = _s.TELEGRAM_BOT_TOKEN or "YOUR_BOT_TOKEN"
    tg_chat  = _s.TELEGRAM_CHAT_ID or "YOUR_CHAT_ID"

    system_prompt = (
        "You are a Personal Assistant Planner. Output ONLY a single valid JSON object — no markdown, no prose.\n\n"
        "=== OUTPUT FORMAT ===\n"
        "If tools are needed:\n"
        '{"status":"PLANNING","tool_calls":[{"tool_name":"TOOL","args":{}}]}\n'
        "If you can answer directly without tools:\n"
        '{"status":"COMPLETED","response":"Your answer here."}\n\n'
        "=== TOOL SELECTION RULES (follow exactly) ===\n"
        "1. User asks about emails / inbox / unread / mail → use fetch_emails with args {}\n"
        "2. User asks about calendar / schedule / events / today / tomorrow → use fetch_calendar_events with args {}\n"
        f"3. User wants to send a Telegram / notification / alert → use telegram_send_alert with args {{\"text\":\"<the actual message to send>\"}}\n"
        "4. User wants to create a Jira issue / ticket / task → use jira_create_issue with args {\"project_key\":\"KAN\",\"summary\":\"<title>\",\"description\":\"<details>\"}\n"
        "5. User asks about past preferences, history, or something you discussed before → use memory_search with args {\"query_text\":\"<topic>\"}\n"
        f"6. User asks about unread Telegram messages / messages sent to the bot → use fetch_telegram_bot_messages with args {{\"bot_token\":\"{tg_token}\"}}\n"
        "7. User asks a general knowledge question or greetings → respond directly with status COMPLETED\n\n"
        "=== HARD RULES ===\n"
        "- You CANNOT send, draft, write, reply, or forward emails. If asked, respond with COMPLETED explaining you can only READ emails.\n"
        "- You CANNOT read the user's personal Telegram chats or conversations with other people. A bot can only see messages sent directly TO the bot.\n"
        "- Never fabricate confirmations or pretend to perform actions. Never say 'I sent' or 'I drafted' unless you used a tool.\n"
        "- Always use fetch_emails (not memory_search) when the user asks about their inbox or unread messages.\n"
        "- Output ONLY the JSON object. No explanation text before or after.\n"
    )

    prompt = (
        f"User Query: {state['user_query']}\n"
        f"Chat History: {state['chat_history']}\n\n"
        "Output your JSON plan:"
    )

    raw_response = await call_llm(
        model=settings.PRIMARY_MODEL,
        prompt=prompt,
        system_prompt=system_prompt,
        timeout=120.0  # gpt-oss on CPU can be slow with longer prompts
    )

    # ── CRITICAL DEBUG: log exactly what the LLM returned ──
    logger.info("Planner raw LLM output", raw_response=raw_response[:500])

    parsed = parse_llm_json(raw_response)

    # ── Log the parsed plan ──
    logger.info("Planner parsed result", status=parsed.get("status"), tool_calls=parsed.get("tool_calls", []))

    if parsed.get("status") == "COMPLETED":
        state["response"] = parsed.get("response", "Task completed.")
        state["status"] = "COMPLETED"
        logger.info("Planner chose direct response (no tools needed)")
    else:
        state["plan"] = parsed.get("tool_calls", [])
        state["current_step_index"] = 0
        state["status"] = "EXECUTING" if state["plan"] else "COMPLETED"
        if not state["plan"] and not state["response"]:
            state["response"] = "I am not sure how to assist with that request."
            state["status"] = "COMPLETED"
            logger.warning("Planner returned no tool_calls and no direct response")
        else:
            logger.info("Planner created execution plan", steps=[s.get("tool_name") for s in state["plan"]])

    return state

async def executor_node(state: AgentState) -> AgentState:
    """
    State node that executes the next step in the plan. Handles HITL approvals.
    """
    if state["status"] != "EXECUTING":
        return state
        
    idx = state["current_step_index"]
    if idx >= len(state["plan"]):
        return state
        
    step = state["plan"][idx]
    tool_name = step.get("tool_name")
    args = step.get("args", {})
    
    tool = tools_registry.get(tool_name)
    if not tool:
        logger.error("Unknown tool requested in execution", tool_name=tool_name)
        state["tool_outputs"].append({"tool": tool_name, "error": "Tool not found in registry."})
        state["current_step_index"] += 1
        return state

    # Check for Human-In-The-Loop approval requirement
    if tool.requires_approval:
        logger.warn("Tool requires approval. Halting execution.", tool_name=tool_name)
        state["status"] = "PAUSED"
        state["pending_approval"] = {
            "integration": "jira" if "jira" in tool_name else "google",
            "action_type": tool_name,
            "payload": args
        }
        return state

    # Execute safe tool inline
    try:
        # Inject DB session and user_id for all database-dependent tools
        if tool_name in DB_TOOLS or tool_name in ["telegram_send_alert", "jira_create_issue"]:
            args["db"] = state["db_session"]
        args["user_id"] = state.get("user_id")

        logger.info("Executing tool", tool=tool_name, args={k: v for k, v in args.items() if k not in ["db", "user_id"]})
        output = await tool.run(**args)
        logger.info("Tool execution succeeded", tool=tool_name, output_preview=str(output)[:300])
        state["tool_outputs"].append({"tool": tool_name, "output": output})

        # If it was a memory search, enrich context
        if tool_name == "memory_search" and isinstance(output, list):
            state["context"].extend([m.get("content", "") for m in output if "content" in m])

    except Exception as e:
        logger.error("Tool execution FAILED", tool=tool_name, error=str(e), exc_info=True)
        state["tool_outputs"].append({"tool": tool_name, "error": str(e)})

    # Increment index and route back
    state["current_step_index"] += 1
    return state

# Routing logic helper
def route_next(state: AgentState) -> str:
    """
    LangGraph conditional edge router.
    """
    if state["status"] == "PAUSED":
        return "paused"
    elif state["status"] == "COMPLETED" or state["status"] == "FAILED":
        return "end"
    
    # If executing, continue to executor node
    if state["plan"] and state["current_step_index"] < len(state["plan"]):
        return "execute"
        
    return "plan"

# Build LangGraph State Graph
workflow = StateGraph(AgentState)

# Register nodes
workflow.add_node("planner", planner_node)
workflow.add_node("executor", executor_node)

# Set entry point
workflow.set_entry_point("planner")

# Register edges
workflow.add_conditional_edges(
    "planner",
    route_next,
    {
        "execute": "executor",
        "paused": END,
        "end": END
    }
)

workflow.add_conditional_edges(
    "executor",
    route_next,
    {
        "plan": "planner",
        "paused": END,
        "end": END
    }
)

# Compile Graph
agent_graph = workflow.compile()
logger.info("LangGraph agent state graph compiled successfully")
