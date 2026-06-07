from __future__ import annotations

from solis.agent.dsl.ast import AgentAST, AllocationRule, RiskConfig


def parse_agent_dsl(text: str) -> AgentAST:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines or not lines[0].startswith("agent "):
        raise ValueError("dsl: missing agent declaration")

    name = lines[0].split()[1]

    version = _extract_after(lines, "version")
    assets = _extract_block_items(lines, "assets:", stop_tokens={"allocation:", "rebalance", "risk:"})
    alloc_lines = _extract_block_items(lines, "allocation:", stop_tokens={"rebalance", "risk:"})

    allocation: list[AllocationRule] = []
    for row in alloc_lines:
        parts = row.split()
        if len(parts) != 2:
            raise ValueError(f"dsl: invalid allocation row: {row}")
        allocation.append(AllocationRule(asset=parts[0], percent=parts[1]))

    rebalance_row = _extract_line_start(lines, "rebalance interval ")
    rebalance_interval = rebalance_row.removeprefix("rebalance interval ").strip()

    risk_lines = _extract_block_items(lines, "risk:", stop_tokens={"}"})
    risk_map: dict[str, str] = {}
    for row in risk_lines:
        parts = row.split()
        if len(parts) != 2:
            raise ValueError(f"dsl: invalid risk row: {row}")
        risk_map[parts[0]] = parts[1]

    required = {"max_drawdown", "collapse_threshold", "no_margin"}
    missing = sorted(required - set(risk_map.keys()))
    if missing:
        raise ValueError(f"dsl: missing risk fields: {','.join(missing)}")

    return AgentAST(
        name=name,
        version=version,
        assets=tuple(assets),
        allocation=tuple(allocation),
        rebalance_interval=rebalance_interval,
        risk=RiskConfig(
            max_drawdown=risk_map["max_drawdown"],
            collapse_threshold=risk_map["collapse_threshold"],
            no_margin=risk_map["no_margin"].lower() == "true",
        ),
    )


def _extract_after(lines: list[str], prefix: str) -> str:
    target = _extract_line_start(lines, prefix + " ")
    return target.removeprefix(prefix + " ").strip()


def _extract_line_start(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return line
    raise ValueError(f"dsl: missing line '{prefix}...' ")


def _extract_block_items(lines: list[str], header: str, stop_tokens: set[str]) -> list[str]:
    out: list[str] = []
    in_block = False
    for line in lines:
        if line == header:
            in_block = True
            continue
        if not in_block:
            continue
        if any(line.startswith(stop) for stop in stop_tokens):
            break
        out.append(line)
    if not out:
        raise ValueError(f"dsl: block '{header}' empty or missing")
    return out
