"""
patch.py — RFC 6902 JSON Patch data models and utilities for AppSpec mutation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal, cast

import jsonpatch
from pydantic import BaseModel, Field


class PatchOperation(BaseModel):
    """A single RFC 6902 JSON Patch operation."""

    op: Literal["add", "remove", "replace", "move", "copy", "test"]
    path: str
    value: Any | None = None
    from_: str | None = Field(None, alias="from")

    model_config = {"populate_by_name": True}

    def to_rfc6902_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"op": self.op, "path": self.path}
        if self.value is not None:
            d["value"] = self.value
        if self.from_ is not None:
            d["from"] = self.from_
        return d


class SpecPatch(BaseModel):
    """A collection of RFC 6902 operations modifying an AppSpec."""

    patch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str = "Spec update"
    operations: list[PatchOperation] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def to_rfc6902_list(self) -> list[dict[str, Any]]:
        return [op.to_rfc6902_dict() for op in self.operations]

    def apply(self, target: dict[str, Any]) -> dict[str, Any]:
        """Apply patch operations to target dictionary in-place / returning updated dict."""
        patch_list = self.to_rfc6902_list()
        jp = jsonpatch.JsonPatch(patch_list)
        return cast(dict[str, Any], jp.apply(target))


def make_spec_patch(
    source: dict[str, Any], target: dict[str, Any], description: str = "Diff patch"
) -> SpecPatch:
    """Create a SpecPatch representing the minimal RFC 6902 delta between source and target."""
    raw_patch = jsonpatch.make_patch(source, target)
    operations: list[PatchOperation] = []
    for item in raw_patch.patch:
        op_dict = dict(item)
        operations.append(PatchOperation(**op_dict))
    return SpecPatch(description=description, operations=operations)
