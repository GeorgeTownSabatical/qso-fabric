from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TemplateRecord:
    template_id: str
    version: str
    graph_hash: str
    owner_uri: str


@dataclass
class TemplateRegistry:
    templates: dict[str, TemplateRecord] = field(default_factory=dict)

    def register(self, record: TemplateRecord) -> None:
        key = f"{record.template_id}:{record.version}"
        if key in self.templates:
            raise ValueError("template version already exists")
        self.templates[key] = record

    def get(self, template_id: str, version: str) -> TemplateRecord:
        key = f"{template_id}:{version}"
        if key not in self.templates:
            raise KeyError(key)
        return self.templates[key]
