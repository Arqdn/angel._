"""Tool registry: the ONLY doorway between the model and this computer.

Every tool is a strongly-typed, explicitly registered function. The model
never gets shell access; it can only call what's here, arguments are
validated against each tool's JSON schema, and anything flagged `dangerous`
goes through the user-confirmation flow before executing.
"""

from __future__ import annotations

import inspect
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

log = logging.getLogger("angel.tools")


@dataclass
class ToolResult:
    ok: bool
    output: str
    attach_image: str | None = None  # path of a screenshot to show the model

    def for_model(self) -> str:
        prefix = "" if self.ok else "ERROR: "
        return f"{prefix}{self.output}"


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]           # JSON schema for "properties"
    func: Callable[..., ToolResult]
    required: list[str] = field(default_factory=list)
    dangerous: bool = False              # requires explicit user confirmation
    enabled: bool = True
    confirm_template: str = ""           # e.g. "shut down this computer"

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": self.required,
                },
            },
        }

    def describe_action(self, args: dict[str, Any]) -> str:
        """Human sentence for the confirmation prompt."""
        if self.confirm_template:
            try:
                return self.confirm_template.format(**args)
            except (KeyError, IndexError):
                pass
        pretty = ", ".join(f"{k}={v!r}" for k, v in args.items())
        return f"run {self.name}({pretty})"


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "number": (int, float),
    "integer": (int,),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def validate_args(spec: ToolSpec, args: dict[str, Any]) -> str | None:
    """Returns an error message, or None when args are valid."""
    if not isinstance(args, dict):
        return "arguments must be an object"
    for key in spec.required:
        if key not in args:
            return f"missing required argument '{key}'"
    for key, value in args.items():
        schema = spec.parameters.get(key)
        if schema is None:
            return f"unknown argument '{key}'"
        expected = schema.get("type")
        if expected in _JSON_TYPES and value is not None:
            allowed = _JSON_TYPES[expected]
            if expected == "number" and isinstance(value, bool):
                return f"argument '{key}' must be a number"
            if expected == "integer" and isinstance(value, bool):
                return f"argument '{key}' must be an integer"
            if not isinstance(value, allowed):
                return f"argument '{key}' must be of type {expected}"
        enum = schema.get("enum")
        if enum and value not in enum:
            return f"argument '{key}' must be one of {enum}"
        if expected in ("number", "integer"):
            low, high = schema.get("minimum"), schema.get("maximum")
            if low is not None and value < low:
                return f"argument '{key}' must be >= {low}"
            if high is not None and value > high:
                return f"argument '{key}' must be <= {high}"
    return None


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool '{spec.name}' registered twice")
        self._tools[spec.name] = spec

    def add(self, name: str, description: str, parameters: dict | None = None,
            required: list[str] | None = None, dangerous: bool = False,
            confirm_template: str = "") -> Callable:
        """Decorator: @registry.add('open_url', 'Open…', {...}, ['url'])"""
        def wrap(func: Callable[..., ToolResult]) -> Callable[..., ToolResult]:
            self.register(ToolSpec(
                name=name, description=description,
                parameters=parameters or {}, required=required or [],
                dangerous=dangerous, confirm_template=confirm_template,
                func=func,
            ))
            return func
        return wrap

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self._tools:
            self._tools[name].enabled = enabled

    def apply_disabled_list(self, disabled: list[str]) -> None:
        for spec in self._tools.values():
            spec.enabled = spec.name not in (disabled or [])

    def openai_tools(self) -> list[dict[str, Any]]:
        return [t.openai_schema() for t in self._tools.values() if t.enabled]

    def parse_call_args(self, raw_arguments: str) -> tuple[dict | None, str | None]:
        try:
            parsed = json.loads(raw_arguments or "{}")
        except json.JSONDecodeError as exc:
            return None, f"arguments were not valid JSON: {exc}"
        if not isinstance(parsed, dict):
            return None, "arguments must be a JSON object"
        return parsed, None

    def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Run a tool. Confirmation for dangerous tools happens in the
        orchestrator BEFORE this is called."""
        spec = self._tools.get(name)
        if spec is None:
            return ToolResult(False, f"no tool named '{name}' exists")
        if not spec.enabled:
            return ToolResult(False, f"the tool '{name}' is disabled in settings")
        problem = validate_args(spec, args)
        if problem:
            return ToolResult(False, f"invalid arguments: {problem}")
        try:
            # Only pass args the function actually accepts.
            sig = inspect.signature(spec.func)
            accepted = {k: v for k, v in args.items() if k in sig.parameters}
            result = spec.func(**accepted)
            if not isinstance(result, ToolResult):
                result = ToolResult(True, str(result))
            log.info("Tool %s -> %s", name, "ok" if result.ok else "failed")
            return result
        except Exception as exc:
            log.exception("Tool %s crashed", name)
            return ToolResult(False, f"{name} failed: {exc}")
