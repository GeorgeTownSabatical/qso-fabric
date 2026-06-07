from __future__ import annotations

from typing import Any, Callable

from solis.agent.sandbox.state_hash import state_hash


Reducer = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def replay_events(initial_state: dict[str, Any], events: list[dict[str, Any]], reducer: Reducer) -> tuple[dict[str, Any], str]:
    state = dict(initial_state)
    for event in events:
        state = reducer(state, event)
    return state, state_hash(state)
