from __future__ import annotations

from dataclasses import dataclass


APPROVED_OPENAI_MODELS = frozenset({"gpt-5.6-luna"})
APPROVED_GEMINI_TARGETS = frozenset({"gemma-4-26b-a4b-it"})


@dataclass(frozen=True, slots=True)
class ApprovedProviderTargets:
    openai_model: str
    gemini_target: str


def validate_operational_provider_targets(
    openai_model: str,
    gemini_target: str,
) -> ApprovedProviderTargets:
    openai_model = openai_model.strip()
    gemini_target = gemini_target.strip()
    if openai_model not in APPROVED_OPENAI_MODELS:
        raise RuntimeError("OpenAI model is not approved for operational pilot evidence")
    if gemini_target not in APPROVED_GEMINI_TARGETS:
        raise RuntimeError("Gemini target is not approved for operational pilot evidence")
    return ApprovedProviderTargets(openai_model, gemini_target)
