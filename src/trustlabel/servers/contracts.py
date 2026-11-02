"""Shared formats (Y1). The harness, the policies, the scenarios and the analysis all code against these.

A Call never carries labels: labels travel separately, so only the policies that are allowed to read them do.
"""

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Literal

Verdict = Literal["allow", "ask", "block"]
Version = Literal["unneeded", "wanted"]
Kind = Literal["delete", "send", "pay", "publish"]


@dataclass(frozen=True)
class Labels:
    """A tool's MCP annotations as its server shows them. None means the field is absent."""

    read_only: bool | None = None
    destructive: bool | None = None

    def as_annotations(self) -> dict:
        """The tools/list form, leaving out absent fields."""
        fields = {"readOnlyHint": self.read_only, "destructiveHint": self.destructive}
        return {k: v for k, v in fields.items() if v is not None}


@dataclass(frozen=True)
class Call:
    """A proposed tool call as the approval layer sees it."""

    name: str
    description: str
    arguments: dict


@dataclass(frozen=True)
class GateInput:
    """Everything a policy may look at for one call. Each policy reads only what its condition allows."""

    request: str
    history: str  # the agent's calls and results before this one, as text
    call: Call
    input_schema: dict
    labels: Labels | None  # None when the server sends no annotations (label switch "none")
    warning: bool  # the warning sentence is on


@dataclass(frozen=True)
class Decision:
    verdict: Verdict
    reason: str = ""
    raw: str = ""  # a gate's raw reply; empty for rule policies
    unreadable: bool = False  # the reply's first word was neither ASK nor ALLOW (counted as ASK)


# V1: a policy takes one call's GateInput and returns a Decision. Plain async functions and Gate objects both fit.
Policy = Callable[[GateInput], Awaitable[Decision]]


@dataclass(frozen=True)
class Scenario:
    """One version of one job (I1)."""

    id: str
    kind: Kind
    version: Version
    request: str
    items: list[dict]
    needed: dict[str, list[str]]  # action -> item ids, e.g. {"archive": [...]} or {"delete": [...]}


@dataclass(frozen=True)
class StoredCall:
    """An irreversible call proposed in stage 1, kept so stage 2 can replay it to every gate condition."""

    episode: str  # stage-1 sample id and epoch
    agent: str  # the agent model that proposed it
    scenario: Scenario
    name_setting: str  # the name switch the agent saw
    position: int  # 1 = the episode's first irreversible call (the main analysis uses only these)
    history: str
    call: Call
    input_schema: dict

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StoredCall":
        return cls(**{**d, "scenario": Scenario(**d["scenario"]), "call": Call(**d["call"])})
