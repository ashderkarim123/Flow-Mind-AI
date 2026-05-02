from uuid import uuid4
from typing import Dict, Any, List

from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowExecuteResponse,
    ExecutionLog,
)
from app.services.model_router import ModelRouter


class ExecutionEngine:
    def __init__(self) -> None:
        self.model_router = ModelRouter()

    async def run(self, workflow: WorkflowCreate, runtime_input: Dict[str, Any]) -> WorkflowExecuteResponse:
        logs: List[ExecutionLog] = []

        for node in workflow.nodes:
            if node.type == "ai_model":
                prompt = node.data.prompt_template or runtime_input.get("prompt", "")
                provider = node.data.provider or "mock"
                model = node.data.model or "mock-basic"
                result = await self.model_router.generate(provider=provider, model=model, prompt=prompt)
                logs.append(
                    ExecutionLog(
                        node_id=node.id,
                        node_type=node.type,
                        status="completed",
                        output=result,
                    )
                )
            else:
                logs.append(
                    ExecutionLog(
                        node_id=node.id,
                        node_type=node.type,
                        status="completed",
                        output={"message": f"Processed {node.type} node"},
                    )
                )

        return WorkflowExecuteResponse(
            execution_id=str(uuid4()),
            status="completed",
            logs=logs,
        )
