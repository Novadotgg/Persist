import structlog
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any, List, Optional
import uuid

from app.db.session import get_db
from app.models.models import User, ActionApproval
from app.agents.orchestrator import agent_graph, AgentState
from app.agents.tools import tools_registry
from app.api.deps import get_current_user

logger = structlog.get_logger()
router = APIRouter()

# Schema definitions
class ChatRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    status: str                       # "COMPLETED", "PAUSED", "FAILED"
    response: str
    pending_approval_id: Optional[str] = None
    pending_approval_type: Optional[str] = None
    pending_approval_payload: Optional[Dict[str, Any]] = None

class ApprovalResponse(BaseModel):
    id: str
    integration: str
    action_type: str
    payload: Dict[str, Any]
    status: str
    created_at: str

@router.post("/chat", response_model=ChatResponse)
async def chat_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a user query to the LangGraph agent state machine.
    Runs planning and execution loops. Halts and returns paused details if a tool requires approval.
    """
    logger.info("New agent chat request received", query=request.query, user_id=str(current_user.id))
    
    # Initialize state with authenticated user's ID
    initial_state = AgentState(
        user_query=request.query,
        chat_history=request.chat_history or [],
        context=[],
        plan=[],
        current_step_index=0,
        tool_outputs=[],
        response="",
        pending_approval=None,
        status="PLANNING",
        db_session=db,
        user_id=str(current_user.id)
    )

    try:
        # Run graph execution loop
        final_state = await agent_graph.ainvoke(initial_state)
        
        # If the execution halted on a pending approval, write approval record to DB
        if final_state["status"] == "PAUSED" and final_state["pending_approval"]:
            pending = final_state["pending_approval"]
            
            # Serialize the paused state so we can resume it later
            serialized_state = {
                "user_query": final_state["user_query"],
                "chat_history": final_state["chat_history"],
                "context": final_state["context"],
                "plan": final_state["plan"],
                "current_step_index": final_state["current_step_index"],
                "tool_outputs": final_state["tool_outputs"],
                "user_id": str(current_user.id)
            }
            
            # Save approval
            approval = ActionApproval(
                integration=pending["integration"],
                action_type=pending["action_type"],
                payload={
                    "tool_args": pending["payload"],
                    "agent_state": serialized_state
                },
                status="PENDING"
            )
            
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
            
            approval_id_str = str(approval.id)
            logger.info("Agent execution paused for approval", approval_id=approval_id_str)
            
            return ChatResponse(
                status="PAUSED",
                response="Action requires approval before execution.",
                pending_approval_id=approval_id_str,
                pending_approval_type=pending["action_type"],
                pending_approval_payload=pending["payload"]
            )
            
        return ChatResponse(
            status=final_state["status"],
            response=final_state["response"]
        )
    except Exception as e:
        logger.error("Error executing agent state graph", error=str(e))
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")

@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_pending_approvals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all active pending approvals for the current authenticated user.
    """
    logger.info("Listing pending action approvals", user_id=str(current_user.id))
    query = select(ActionApproval).where(ActionApproval.status == "PENDING").order_by(ActionApproval.created_at.desc())
    result = await db.execute(query)
    approvals = result.scalars().all()
    
    # Filter approvals in memory based on user_id embedded in the agent_state payload
    user_approvals = []
    for a in approvals:
        agent_state = a.payload.get("agent_state", {})
        if agent_state.get("user_id") == str(current_user.id):
            user_approvals.append(
                ApprovalResponse(
                    id=str(a.id),
                    integration=a.integration,
                    action_type=a.action_type,
                    payload=a.payload.get("tool_args", {}),
                    status=a.status,
                    created_at=a.created_at.isoformat() if a.created_at else ""
                )
            )
    return user_approvals

@router.post("/approvals/{approval_id}/approve", response_model=ChatResponse)
async def approve_action(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Approves a pending action. Executes the action, updates state, and resumes the agent.
    """
    logger.info("Action approval received", approval_id=approval_id, user_id=str(current_user.id))
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID UUID format.")

    query = select(ActionApproval).where(
        ActionApproval.id == approval_uuid,
        ActionApproval.status == "PENDING"
    )
    result = await db.execute(query)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Pending approval record not found.")

    agent_state_dict = approval.payload.get("agent_state", {})
    
    # Verify ownership
    if agent_state_dict.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to approve this action."
        )

    tool_args = approval.payload.get("tool_args", {})
    action_type = approval.action_type

    tool = tools_registry.get(action_type)
    if not tool:
         raise HTTPException(status_code=500, detail=f"Tool {action_type} not found in registry.")

    # Inject db session and user_id for tools
    tool_args["db"] = db
    tool_args["user_id"] = str(current_user.id)

    # 1. Execute the approved tool
    try:
        output = await tool.run(**tool_args)
    except Exception as e:
        logger.error("Failed executing approved action", tool=action_type, error=str(e))
        output = {"error": str(e)}

    # 2. Update approval DB state
    approval.status = "APPROVED"
    approval.processed_at = datetime.now(timezone.utc)
    await db.commit()

    # 3. Resume the Agent state loop
    resumed_state = AgentState(
        user_query=agent_state_dict.get("user_query", ""),
        chat_history=agent_state_dict.get("chat_history", []),
        context=agent_state_dict.get("context", []),
        plan=agent_state_dict.get("plan", []),
        current_step_index=agent_state_dict.get("current_step_index", 0) + 1, # Increment step past approved tool
        tool_outputs=agent_state_dict.get("tool_outputs", []) + [{"tool": action_type, "output": output}],
        response="",
        pending_approval=None,
        status="EXECUTING",
        db_session=db,
        user_id=str(current_user.id)
    )

    try:
        logger.info("Resuming agent state machine execution graph")
        final_state = await agent_graph.ainvoke(resumed_state)
        
        # Check if it paused again on a NEXT step
        if final_state["status"] == "PAUSED" and final_state["pending_approval"]:
            pending = final_state["pending_approval"]
            serialized_state = {
                "user_query": final_state["user_query"],
                "chat_history": final_state["chat_history"],
                "context": final_state["context"],
                "plan": final_state["plan"],
                "current_step_index": final_state["current_step_index"],
                "tool_outputs": final_state["tool_outputs"],
                "user_id": str(current_user.id)
            }
            
            new_approval = ActionApproval(
                integration=pending["integration"],
                action_type=pending["action_type"],
                payload={
                    "tool_args": pending["payload"],
                    "agent_state": serialized_state
                },
                status="PENDING"
            )
            db.add(new_approval)
            await db.commit()
            await db.refresh(new_approval)
            
            return ChatResponse(
                status="PAUSED",
                response="Action approved, but next step requires approval.",
                pending_approval_id=str(new_approval.id),
                pending_approval_type=pending["action_type"],
                pending_approval_payload=pending["payload"]
            )
            
        return ChatResponse(
            status=final_state["status"],
            response=final_state["response"]
        )
    except Exception as e:
        logger.error("Failed to resume agent execution", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to resume agent: {str(e)}")

@router.post("/approvals/{approval_id}/reject", response_model=ChatResponse)
async def reject_action(
    approval_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Rejects a pending action. Resumes the agent loop with failure status.
    """
    logger.info("Action rejection received", approval_id=approval_id, user_id=str(current_user.id))
    try:
        approval_uuid = uuid.UUID(approval_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid approval ID UUID format.")

    query = select(ActionApproval).where(
        ActionApproval.id == approval_uuid,
        ActionApproval.status == "PENDING"
    )
    result = await db.execute(query)
    approval = result.scalar_one_or_none()

    if not approval:
        raise HTTPException(status_code=404, detail="Pending approval record not found.")

    agent_state_dict = approval.payload.get("agent_state", {})
    
    # Verify ownership
    if agent_state_dict.get("user_id") != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to reject this action."
        )

    action_type = approval.action_type

    # 1. Update DB
    approval.status = "REJECTED"
    approval.processed_at = datetime.now(timezone.utc)
    await db.commit()

    # 2. Resume with rejected output info
    resumed_state = AgentState(
        user_query=agent_state_dict.get("user_query", ""),
        chat_history=agent_state_dict.get("chat_history", []),
        context=agent_state_dict.get("context", []),
        plan=agent_state_dict.get("plan", []),
        current_step_index=agent_state_dict.get("current_step_index", 0) + 1,
        tool_outputs=agent_state_dict.get("tool_outputs", []) + [{"tool": action_type, "error": "User rejected this action"}],
        response="",
        pending_approval=None,
        status="EXECUTING",
        db_session=db,
        user_id=str(current_user.id)
    )

    try:
        final_state = await agent_graph.ainvoke(resumed_state)
        return ChatResponse(
            status=final_state["status"],
            response=final_state["response"]
        )
    except Exception as e:
        logger.error("Failed to resume agent after rejection", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to resume agent: {str(e)}")
