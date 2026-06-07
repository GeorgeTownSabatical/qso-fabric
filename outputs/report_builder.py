from __future__ import annotations


def build(sections: dict[str, str]) -> str:
    return "\n\n".join(f"{title}\n{body}" for title, body in sections.items())
