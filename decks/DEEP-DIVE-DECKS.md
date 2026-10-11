# Deep-dive decks · register

One entry per deep-dive deck edition, newest first. Maintained by the `azure-ai-deep-dive-deck`
skill (path in `kit.yaml` → `paths.deep_dive_register`); entries are appended, never rewritten.
A new edition of a deck gets a new dated file and a new entry — the previous edition is the
rollback. `Conformance` states whether the deck meets the skill version named.

---

## hosted-agents-deep-dive-2026-10 · edition 2026-10

**Kit file:** `Microsoft Foundry Hosted Agents.pptx` (legacy name) · **Sources verified:** 2026-10-09 · **Slides:** 7
**Pairs with:** notebooks 2 and 3
**Sources:** learn.microsoft.com/azure/foundry/agents/concepts/hosted-agents · how-to/deploy-hosted-agent · concepts/limits-quotas-regions · how-to/virtual-networks · add-hosted-agent-guardrails · agents/overview
**Conformance:** skill 1.0.0 — `deck_qa.py` 0 FAIL, 0 WARN
**Open verify items:**
- Which identity pulls the container image (project managed identity or agent identity — pages differ).
- Status of skills for hosted agents.
- Per-hour rates on the Foundry Agent Service pricing page (not published for the default region on 2026-10-09).
- Whether the agent endpoint is private when deployed with azd (pages differ).

## ai-gateway-deep-dive-2026-10 · edition 2026-10

**Kit file:** `Microsoft Foundry AI Gateway.pptx` (legacy name) · **Sources verified:** 2026-10-03 · **Slides:** 9
**Pairs with:** notebook 8
**Sources:** learn.microsoft.com/azure/api-management/genai-gateway-capabilities · llm-token-limit-policy · llm-emit-token-metric-policy · mcp-server-overview · agent-to-agent-api · azure/foundry/configuration/enable-ai-api-management-gateway-portal · agents/how-to/tools/governance · control-plane/register-custom-agent · guardrails/guardrails-overview · github.com/Azure-Samples/foundry-citadel-platform
**Conformance:** kept as published by owner decision (2026-10-11); speaker notes on slides 3 and 4 predate wording rule 4 — apply it in the next edition
**Open verify items:**
- AI Gateway in Foundry status (configuration page has no preview label; readiness table marks it preview).
- Whether semantic caching or content safety policies can be added to model traffic managed by the Foundry gateway.
- Whether Foundry agents' own model calls route through the gateway.
- `llm-token-limit` sample values against the policy reference.
- API Center MCP registry status; bring-your-own-model status; guardrail status for agents.
- Citadel repository and aka.ms/ai-hub-gateway links still current.

## voice-live-voice-agents-deep-dive-2026-10 · edition 2026-10

**Kit file:** `Microsoft Foundry Voice Live-Voice Agents.pptx` (legacy name) · **Sources verified:** 2026-10-02 · **Slides:** 9
**Pairs with:** notebook 7
**Sources:** learn.microsoft.com/azure/ai-services/speech-service/voice-live · voice-live-how-to · voice-live-api-reference-2026-07-15 · voice-live-faq · how-to-voice-agent-integration · speech-services-quotas-and-limits · regions · azure/foundry/agents/how-to/configure-voice-agent · voice-agent-telephony-channels
**Conformance:** skill 1.0.0 — `deck_qa.py` 0 FAIL (two status cells on the status slide, allowed)
**Open verify items:**
- Per-token prices on the Azure Speech pricing page.
- Voice agent property names (preview) against configure-voice-agent.
- SDK signature against the current azure-ai-voicelive release.
- Migration guide live on Learn (published on GitHub on 2026-09-30).
- Region and quota tables on the day.

## content-understanding-deep-dive-2026-09 · edition 2026-09-30

**Kit file:** `Microsoft Foundry Content-Understanding.pptx` (legacy name) · **Edition date:** 2026-09-30 · **Slides:** 12
**Pairs with:** notebook 6
**Sources:** learn.microsoft.com/azure/ai-services/content-understanding/overview · concepts/analyzer-reference · concepts/prebuilt-analyzers · concepts/agentic-mode · document/analyzer-improvement · choosing-right-ai-tool · pricing-explainer · service-limits · quickstart/use-rest-api
**Conformance:** kept as published by owner decision (2026-10-11); built before the slide-wording rules — apply skill 1.0.0 in the next edition

## a2a-deep-dive-2026-09 · edition 2026-09-18

**Kit file:** `Microsoft Foundry Agent2Agent-A2A.pptx` (legacy name) · **Edition date:** 2026-09-18 · **Slides:** 21
**Pairs with:** notebook 5
**Sources:** a2a-protocol.org/latest/specification · topics/what-is-a2a · life-of-a-task · agent-discovery · streaming-and-async · a2a-and-mcp · github.com/a2aproject/A2A · Microsoft Learn Foundry A2A pages
**Conformance:** kept as published by owner decision (2026-10-11); built before the slide-wording rules — apply skill 1.0.0 in the next edition

---

<!-- Template — copy, fill in, insert directly under the header (newest first).

## <topic-kebab-case>-deep-dive-<yyyy>-<mm> · edition <yyyy>-<mm>[-<dd>]

**Kit file:** `<file name in decks/>` · **Sources verified:** <yyyy-mm-dd> · **Slides:** <n>
**Pairs with:** notebook <n> | none yet
**Sources:** <Learn and GitHub paths fetched during the build>
**Conformance:** skill <version> — `deck_qa.py` <n> FAIL, <n> WARN
**Open verify items:**
- …
-->
