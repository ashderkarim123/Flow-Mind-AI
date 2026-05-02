from fastapi import APIRouter

from app.schemas.workflow import WorkflowCreate, WorkflowExecuteRequest
from app.services.execution_engine import ExecutionEngine

router = APIRouter(prefix="/api/v1/flowmind", tags=["FlowMind Execution"])
engine = ExecutionEngine()


@router.get("/models")
async def list_models():
    return engine.model_router.available_models()


@router.post("/execute")
async def execute_workflow(workflow: WorkflowCreate, input_request: WorkflowExecuteRequest):
    return await engine.run(workflow=workflow, runtime_input=input_request.input)
