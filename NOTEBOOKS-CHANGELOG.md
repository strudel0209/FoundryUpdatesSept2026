# Demo notebooks · changelog

One entry per notebook change or dependency audit, newest first. Maintained by the
`deck-companion-notebook` skill (path in `kit.yaml` → `paths.notebooks_changelog`); entries are
appended, never rewritten. Deck editions are logged in `decks/CHANGELOG.md`, not here.

**Last dependency audit:** none yet — run *"check the kit's dependencies"* before the next customer session.

---

## 2026-10-11 · baseline — eight notebooks registered

**Paired decks:** see `kit.yaml` → `notebooks` (notebook 1 ↔ what's-new edition 2026-10; notebooks 2–8 ↔ deep-dive decks)
**Dependency changes:** none (baseline)
**Env changes:** none (baseline); collisions recorded in `kit.yaml` → `env`
**Regression:** static gate `scripts/kit_check.py` over 8/8 notebooks on the OneDrive kit copy — verdict FAIL (4 FAIL, 29 WARN, 27 INFO), all pre-existing. The owner then removed notebook 2's gateway section and cleared all outputs (repository commit of 2026-10-11), which resolves the notebook 2 findings below; re-run the gate on the repository to confirm · resolver: resolved by reading, not executed · notebooks not executed against Azure
**Pre-existing FAILs:**
- notebook 1, cell 2: `FOUNDRY_ACCOUNT_NAME` read but missing from `.env.example`
- notebook 5, cells 2 and 23: per-notebook `%pip install` (one floors `azure-ai-projects>=2.5.0` against the root `>=2.7.0,<3`)
**Notable WARNs:** env collision `AZURE_RESOURCE_GROUP` (notebooks 1 and 8); preview surfaces in notebook 1 without a minor cap on `azure-ai-projects`; requirements without notebook tags. Resolved by the owner's changes: `APIM_GATEWAY_URL` collision and `APIM_SUBSCRIPTION_KEY` (notebook 2 gateway removed), stored outputs (cleared)
**Open verify items:** `# verify` lines — notebook 1: 2, notebook 2: 3
**Next free notebook number:** 9

<!-- Template — copy, fill in, insert directly under the separator (newest first).

## <yyyy-mm-dd> · foundry-demo-<n>-<topic>.ipynb — added | updated
**Paired deck:** <file> · edition <yyyy-mm> · slide map: step 1 → slide <x>; step 2 → slides <y, z>; …
**Dependency changes:** <package old → new, or none>
**Env changes:** <variable added/reused, or none>
**Regression:** <n>/<n> notebooks pass static gate · pre-existing: <list or none> · resolver: executed | resolved by reading, not executed · new notebook not executed against Azure
**Open verify items:** <list or none>
**Last dependency audit:** <yyyy-mm-dd>
-->
