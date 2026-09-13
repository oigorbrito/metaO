# Operational pilot provider-target policy

Credential-backed project-pilot runs that produce operational evidence are fail-closed to an explicit provider-target allowlist.

Approved targets:

- OpenAI: `gpt-5.6-luna`
- Gemini: `gemma-4-26b-a4b-it`

The operational entrypoint validates both targets before invoking the provider-backed pilot. Unknown targets abort before any provider call. The bounded result must retain the selected targets and mark `provider_targets_approved=true` with `operational_target_policy=ALLOWLISTED`.

This evidence-producing operational path has no experimental override flag. Experiments with other models/targets must use a separate non-operational path and must not emit or be represented as operational pilot PASS evidence.

Model selection does not alter scheduler authority, executor/provider identity registration, independent verification, corrective-replan semantics, checkpoint authority, or project-acceptance rules.