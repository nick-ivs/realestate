"""Form definitions: where each blank is, and what deal information fills it."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..pdf import Field


@dataclass(frozen=True)
class Input:
    """One piece of information a form asks for, as a person would enter it."""

    key: str
    label: str
    section: str
    hint: str
    required: bool = True
    kind: str = "text"  # "text" or "date"
    choices: tuple[str, ...] = ()


@dataclass
class Missing:
    key: str  # the info key that would supply it, so a prompt can fill it in
    label: str
    hint: str


@dataclass
class FormResult:
    name: str
    template: str
    fields: list[Field]
    values: dict[str, str] = field(default_factory=dict)
    missing: list[Missing] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    not_on_form: dict[str, str] = field(default_factory=dict)
