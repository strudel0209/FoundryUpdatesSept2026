# Foundry demo — hosted agents (companion to notebook 2)

Two hosted agents in one azd project, deployed to your **existing** Foundry project.

## One-time setup
```bash
azd auth login
azd extension install azure.ai.agents          # >= 1.0.0-beta.9
azd ext install microsoft.foundry              # provides the microsoft.foundry infra provider
cd agent
azd init -e demo                               # creates .azure/demo
azd env set FOUNDRY_PROJECT_ENDPOINT https://<account>.services.ai.azure.com/api/projects/<project>
azd env set AZURE_AI_MODEL_DEPLOYMENT_NAME <chat-deployment-name>
azd env set AZURE_SUBSCRIPTION_ID <subscription id>
azd env set AZURE_AI_PROJECT_ID <Foundry project id>
azd env set AZURE_LOCATION <Foundry region>
azd up                                         # provisions nothing new; builds and deploys both agents
```
`azd up` prints one Responses endpoint per agent — copy them into the notebook's `.env`:
```
HOSTED_AGENT_NAME=demo-hosted-agent
LONG_RUNNING_AGENT_NAME=demo-long-running-agent
```
Endpoints follow the documented pattern
`{project_endpoint}/agents/{name}/endpoint/protocols/openai/responses`.

## Business demo: a sourcing decision brief

The long-running agent helps a procurement manager prepare a **preliminary decision brief**:

1. **Risk assessment:** prioritized risks, business impacts, assumptions and missing evidence.
2. **Mitigation plan:** sourcing options, accountable roles and decision gates.
3. **Decision brief:** a reviewed recommendation, trade-offs and next actions for human approval.

Each stage makes a real model call and uses the completed sections from preceding stages.
The notebook begins with battery-module sourcing for a Swiss manufacturer. Steering redirects
the work to selecting a battery-recycling partner before the original brief finishes.
Each turn is a separate brief; steering stops unfinished work rather than silently blending topics.

### Why run it in the background?

A multi-step decision workflow can outlast an interactive request, especially when extended with
supplier documents, external lookups and review loops. A procurement manager can leave and return
to the same response. Completed sections are checkpointed; recovery restores their content and IDs
without requesting those sections from the model again. An interrupted, uncheckpointed call may
need to be repeated and billed again. Steering lets the manager change priorities without waiting
for an obsolete report to finish. Cancelling the local model request does not guarantee that the
model service stops computation or billing immediately.

A single short summary does **not** need this architecture. This demo uses three sequential model
calls to make the pattern visible, not to claim every brief must be a long-running job.

### Prerequisites and boundaries

- The service uses the existing `AZURE_AI_MODEL_DEPLOYMENT_NAME`, with the project endpoint injected
	by the runtime. Its hosted identity needs permission to invoke that deployment.
- There are no live supplier, pricing, regulatory or research tools. Outputs use supplied facts
	and model knowledge, explicitly identify assumptions, and require human verification.
- No supplier is approved, purchase order placed, or saving guaranteed. Each completed brief
	normally makes three model calls, plus any retries or interrupted stages.
- `DEMO_STAGE_DELAY_SECONDS` is set to `10` in the manifest solely to leave time for live steering.
	Set it to `0` for normal use. Actual duration depends on the model; the delay is not business work.
- Each completed section is committed with `stream.checkpoint()`. Local crash testing is described
	below. Use a new conversation after upgrading from the old simulated-stage demo.

After changing the agent, run `azd deploy demo-long-running-agent`, then notebook cells 9, 10 and 11.
Run cell 10 promptly for steering, or skip it and run cell 11 to finish the original brief.
Cell 11 renders sections as they arrive and can reconnect to the same response after its timeout.

Run focused local tests from the repository root:

```bash
OTEL_SDK_DISABLED=true python3 -m unittest discover -s agent/src/demo-long-running-agent -p 'test_*.py'
```

## Run locally (optional)
```bash
azd ai agent run --no-client                   # one agent at a time; serves http://localhost:8088
SIMULATE_CRASH_AFTER_STAGE=0 azd ai agent run --no-client   # long-running agent: crash after stage 1, restart to see recovery
```

## Cleanup
```bash
azd down                                       # removes only what this environment created
```
Long-running agents are **preview**: APIs and package versions may change.
