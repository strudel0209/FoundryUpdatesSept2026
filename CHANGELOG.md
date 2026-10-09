# Microsoft Foundry — What's New · deck changelog

One entry per dated edition, newest first. Each entry lists what changed since the previous edition, the source consulted for each change, the run date, and any items still to verify before presenting. Maintained by the `foundry-whats-new-deck` skill; entries are appended, never rewritten.

Deck file pattern: `Microsoft-Foundry-Whats-New-<yyyy>-<mm>.pptx` · 23 slides · 16:9 · speaker notes on every slide.

---

## Edition 2026-09 — initial edition

**File:** `Microsoft-Foundry-Whats-New-2026-09.pptx`
**Facts verified:** 11 September 2026 (Microsoft Learn, Foundry developer blog, GitHub)
**Baseline for next detect run:** 11 September 2026
**Next detect run due:** 25 September 2026

### Scope
Covers Microsoft Foundry releases and announcements through Build 2026 (2 June 2026) and the July–August 2026 roundup (published 9 September 2026). Ignite 2026 had not taken place at edition date.

### Structure
| Section | Slides |
|---|---|
| 01 Microsoft Foundry architecture | 3–6 |
| 02 Foundry Models | 7–10 |
| 03 Foundry Tools and Microsoft IQ | 11–13 |
| 04 Agent Service and Agent Framework | 14–17 |
| 05 Foundry Control Plane | 18–21 |
| Wrap-up | 22–23 |

### Sources consulted
- learn.microsoft.com/azure/foundry — what-is-foundry · concepts/architecture · concepts/capability-reference · how-to/develop/sdk-overview · whats-new-foundry
- learn.microsoft.com/azure/foundry/foundry-models/concepts — deployment-types · models-sold-directly-by-azure · models-from-partners
- learn.microsoft.com/azure/foundry/openai/concepts — model-router · priority-processing
- learn.microsoft.com/azure/foundry/agents — overview · concepts/hosted-agents · concepts/tool-catalog · concepts/toolbox-overview · how-to/use-your-own-resources · how-to/migrate · how-to/memory-usage · how-to/tools/work-iq · how-to/tools/fabric-iq · how-to/foundry-iq-connect · concepts/long-running-agent-resilience · how-to/manage-task-state
- learn.microsoft.com/azure/search — agentic-retrieval-overview · agentic-knowledge-source-overview
- learn.microsoft.com/agent-framework/overview · github.com/microsoft/agent-framework/releases
- learn.microsoft.com/azure/foundry/control-plane/overview · guardrails/guardrails-overview · ai-services/content-safety/overview
- learn.microsoft.com/azure/foundry/concepts — built-in-evaluators · observability · ai-red-teaming-agent
- learn.microsoft.com/azure/foundry/observability/how-to — cloud-evaluation-targets · evaluate-agent · trace-agent-client-side · how-to-monitor-agents-dashboard
- learn.microsoft.com/azure/architecture/ai-ml/architecture/baseline-microsoft-foundry-chat
- learn.microsoft.com/azure/api-management/genai-gateway-capabilities
- devblogs.microsoft.com/foundry — What's new in Microsoft Foundry: Build 2026 · July–August 2026
- devblogs.microsoft.com/agent-framework — Microsoft Agent Framework version 1.0

### Verify before presenting
Items the documentation did not confirm at edition date. Also listed in the speaker notes of slide 23.
- Foundry Agent Service SLA — no SLA page found; do not quote a figure
- Publishing to Microsoft Teams and Microsoft 365 Copilot — GA planned for June 2026, not confirmed on Learn
- Assistants API retirement date — not published on Learn
- SLA percentages per deployment type — see the Azure OpenAI Service SLA document
- Model Router region count — blog states 28 Global Standard regions; the Learn table lists 33
- Legacy ToolSet class in the classic azure-ai-agents SDK — not confirmed
- Default guardrail severity — "medium" is not documented; default guardrail is Microsoft.DefaultV2
- Foundry Control Plane announcement date — do not attribute to Ignite 2025
- Logic Apps connector count (1,400+) — appears only on the product page, not on Learn

### Preview features at edition date
Memory · A2A · agent guardrails (tool call / tool response points) · long-running agents · Work IQ · Fabric IQ · client-side tracing · agent monitoring dashboard · most Foundry IQ knowledge sources · AI gateway in Foundry · Skills · tool search · managed compute · instant access models · MAI model family

---

<!-- Template for the next edition. Copy it, fill it in, and insert it directly under the header so the newest edition is first.

## Edition <yyyy>-<mm>

**File:** `Microsoft-Foundry-Whats-New-<yyyy>-<mm>.pptx`
**Run date:** <yyyy-mm-dd> · **Baseline:** <previous run date> · **Next detect run due:** <run date + 14 days>

### Changes since edition <previous>
| Slide | Change | Status | Source (fetched this run) |
|---|---|---|---|
| 7 | … | GA / preview / retired | https://learn.microsoft.com/… |

### Items detected but not applied
| Item | Reason |
|---|---|

### Verify before presenting
- …

### Preview features at edition date
…
-->
