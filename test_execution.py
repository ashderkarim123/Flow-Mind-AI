import asyncio
import json
import uuid
import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv("backend/.env")

# Must set the pythonpath to find the backend modules
import sys
sys.path.append(os.path.abspath("backend"))

from backend.executor.engine import WorkflowEngine, WorkflowDefinition, WorkflowNode, WorkflowConnection
from backend.executor.context import ExecutionContext
from backend.nodes.registry import NodeRegistry

async def main():
    registry = NodeRegistry()
    engine = WorkflowEngine(registry)
    
    workflow_id = str(uuid.uuid4())
    execution_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    
    context = ExecutionContext(execution_id=execution_id, workflow_id=workflow_id, user_id=user_id)
    
    workflow = WorkflowDefinition(
        id=workflow_id,
        name="Test Workflow",
        nodes=[
            WorkflowNode(id="n1", type="ManualTrigger", config={}),
            WorkflowNode(id="n2", type="Logger", config={"level": "info", "message": "Test execution successful: {{$trigger.input_data.test}}"})
        ],
        connections=[
            WorkflowConnection(from_node="n1", to_node="n2")
        ]
    )
    
    initial_input = {"test": "It works!"}
    
    print(f"Executing workflow {workflow_id}")
    result = await engine.execute(workflow, initial_input, context)
    
    print("\nExecution Result Status:", result.status)
    print("Logs:")
    for log in result.logs:
        print(f"[{log.node_type}] {log.status}: {log.output if log.status == 'completed' else log.error}")
        
    if result.status != "completed":
        print("Error:", result.error)

if __name__ == "__main__":
    asyncio.run(main())
