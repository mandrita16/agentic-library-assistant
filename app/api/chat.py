from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.agent.agent import run_agent
from app.auth.dependencies import get_current_student


router = APIRouter(
    prefix="/chat",
    tags=["chat"]
)


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Student's message"
    )

    history: list[dict] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )


@router.post("")
def chat_with_mindsync(
    req: ChatRequest,
    current_student_id: str = Depends(get_current_student),
):

    try:

        result = run_agent(
            req.message,
            req.history,
            current_student_id,
        )

        return result

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"MindSync agent error: {str(exc)}"
        )