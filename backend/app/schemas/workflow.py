from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

NodeType = Literal['input', 'prompt', 'ai_model', 'condition', 'output', 'webhook']
ExecutionStatus = Literal['pending', 'running', 'completed', 'failed']


class NodePosition(BaseModel):
    x: float
    y: float


class WorkflowNodeData(BaseModel):
    label: str
    description: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_template: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    compare_mode: bool = False
    config: Dict[str, Any] = Field(default_factory=dict)


class WorkflowNode(BaseModel):
    id: str
    type: NodeType
    position: NodePosition
    data: WorkflowNodeData


class WorkflowEdge(BaseModel):
    id: str
    source: str
    target: str
    condition: Optional[str] = None


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    nodes: List[WorkflowNode] = Field(default_factory=list)
    edges: List[WorkflowEdge] = Field(default_factory=list)


class WorkflowExecuteRequest(BaseModel):
    workflow_id: str
    input: Dict[str, Any] = Field(default_factory=dict)
    compare_mode: bool = False


class ExecutionLog(BaseModel):
    node_id: str
    node_type: NodeType
    status: ExecutionStatus
    output: Dict[str, Any] = Field(default_factory=dict)


class WorkflowExecuteResponse(BaseModel):
    execution_id: str
    status: ExecutionStatus
    logs: List[ExecutionLog] = Field(default_factory=list)
