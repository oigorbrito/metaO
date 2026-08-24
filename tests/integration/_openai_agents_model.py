from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from openai.types.responses import ResponseOutputMessage, ResponseOutputText

from agents.agent_output import AgentOutputSchemaBase
from agents.handoffs import Handoff
from agents.items import ModelResponse, TResponseInputItem, TResponseOutputItem, TResponseStreamEvent
from agents.model_settings import ModelSettings
from agents.models.interface import Model, ModelTracing
from agents.tool import Tool
from agents.usage import Usage


def assistant_message(text: str, *, item_id: str = "metao-scripted-message") -> TResponseOutputItem:
    return ResponseOutputMessage(
        id=item_id,
        type="message",
        role="assistant",
        status="completed",
        content=[
            ResponseOutputText(
                text=text,
                type="output_text",
                annotations=[],
                logprobs=[],
            )
        ],
    )


class ScriptedModel(Model):
    """Minimal provider-free deterministic model for metaO runtime integration tests."""

    def __init__(self, steps: list[list[TResponseOutputItem] | Exception]) -> None:
        self._steps = list(steps)
        self.calls: list[dict[str, Any]] = []

    @property
    def remaining_steps(self) -> int:
        return len(self._steps)

    def assert_complete(self) -> None:
        if self._steps:
            raise AssertionError(f"unconsumed model steps: {len(self._steps)}")

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> ModelResponse:
        self.calls.append(
            {
                "system_instructions": system_instructions,
                "input": input,
                "model_settings": model_settings,
                "tools": tools,
                "output_schema": output_schema,
                "handoffs": handoffs,
                "tracing": tracing,
                "previous_response_id": previous_response_id,
                "conversation_id": conversation_id,
                "prompt": prompt,
            }
        )
        if not self._steps:
            raise AssertionError("unexpected OpenAI Agents model call")
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return ModelResponse(output=list(step), usage=Usage(), response_id="metao-scripted-response")

    async def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        if False:
            yield  # pragma: no cover
        raise NotImplementedError("metaO deterministic test model does not stream")
