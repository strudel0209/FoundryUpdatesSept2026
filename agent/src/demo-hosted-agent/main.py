"""Demo hosted agent — Microsoft Agent Framework, Responses protocol.

Shape verified against the Foundry hosted-agent samples (agent-framework/responses/01-basic)
and the Agent Framework hosting docs. The platform injects FOUNDRY_PROJECT_ENDPOINT and an
Application Insights connection string; the hosting library emits OpenTelemetry spans by default.
"""
import os
from typing import Annotated

from azure.identity import DefaultAzureCredential
from agent_framework import Agent
from agent_framework.foundry import FoundryChatClient
from agent_framework_foundry_hosting import ResponsesHostServer   # provided by agent-framework-foundry-hosting

# FOUNDRY_PROJECT_ENDPOINT is injected by the hosted runtime; AZURE_AI_PROJECT_ENDPOINT covers local runs.
project_endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT") or os.environ["AZURE_AI_PROJECT_ENDPOINT"]
model = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]


def deployment_type_hint(
    workload: Annotated[str, "Short description of the workload, e.g. 'batch summarisation overnight'"],
) -> str:
    """Suggest a Foundry deployment type for a workload. Demo tool — deterministic, no external call."""
    w = workload.lower()
    if "batch" in w or "overnight" in w:
        return "GlobalBatch — asynchronous, 50% discount, 24-hour target, no real-time SLA."
    if "latency" in w or "interactive" in w or "chat" in w:
        return "Provisioned (PTU) for guaranteed throughput; or GlobalStandard with Priority Processing on pay-as-you-go."
    if "eu" in w or "residency" in w or "switzerland" in w:
        return "DataZoneStandard (EU) — inference stays inside the EU Data Boundary; data at rest stays in your geography."
    return "GlobalStandard — pay per token, highest quota, best effort."


client = FoundryChatClient(project_endpoint=project_endpoint, model=model, credential=DefaultAzureCredential())

agent = Agent(
    client=client,
    name="demo-hosted-agent",
    instructions=(
        "You are a concise Microsoft Foundry architect. Answer in at most four sentences. "
        "When asked which deployment type to use, call the deployment_type_hint tool and quote its answer."
    ),
    tools=[deployment_type_hint],
)

if __name__ == "__main__":
    ResponsesHostServer(agent).run()      # serves the Responses protocol on port 8088
