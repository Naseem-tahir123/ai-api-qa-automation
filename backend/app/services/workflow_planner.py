import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

from app.models.endpoint import Endpoint


@dataclass
class StepDefinition:
    endpoint: Endpoint
    depends_on_endpoint_ids: list[int] = field(default_factory=list)
    capture_rules: list[dict[str, Any]] = field(default_factory=list)
    injection_rules: list[dict[str, Any]] = field(default_factory=list)
    is_cleanup: bool = False


class WorkflowPlanner:
    """Build small deterministic workflows without placing a full API spec in LLM context."""

    PARAMETER_PATTERN = re.compile(r"\{([^}]+)\}")
    IGNORED_SEGMENTS = {"api", "v1", "v2", "v3", "internal", "public"}

    @classmethod
    def resource_name(cls, path: str) -> str:
        segments = [segment for segment in path.strip("/").split("/") if segment and not segment.startswith("{")]
        candidates = [segment for segment in segments if segment.lower() not in cls.IGNORED_SEGMENTS]
        return (candidates[-1] if candidates else "resource").replace("-", "_").lower()

    @staticmethod
    def canonical(name: str) -> str:
        name = name.lower().replace("-", "_")
        return name[:-3] + "y" if name.endswith("ies") else name[:-1] if name.endswith("s") else name

    @classmethod
    def build(cls, endpoints: list[Endpoint]) -> tuple[list[StepDefinition], dict[str, Any]]:
        definitions = {endpoint.id: StepDefinition(endpoint=endpoint) for endpoint in endpoints}
        producers: dict[str, Endpoint] = {}

        for endpoint in endpoints:
            resource = cls.resource_name(endpoint.path)
            if endpoint.method.upper() == "POST" and not cls.PARAMETER_PATTERN.findall(endpoint.path):
                producers[cls.canonical(resource)] = endpoint
                definitions[endpoint.id].capture_rules.append({
                    "context_key": f"{cls.canonical(resource)}.id",
                    "selectors": ["$.id", "$.data.id", f"$.{cls.canonical(resource)}.id"],
                })

        for endpoint in endpoints:
            definition = definitions[endpoint.id]
            resource_key = cls.canonical(cls.resource_name(endpoint.path))
            producer = producers.get(resource_key)
            for parameter in cls.PARAMETER_PATTERN.findall(endpoint.path):
                if producer and producer.id != endpoint.id:
                    definition.depends_on_endpoint_ids.append(producer.id)
                    definition.injection_rules.append({"target": f"path.{parameter}", "context_key": f"{resource_key}.id"})
            definition.depends_on_endpoint_ids = sorted(set(definition.depends_on_endpoint_ids))
            definition.is_cleanup = endpoint.method.upper() == "DELETE"

        ordered = cls._topological_order(definitions)
        graph = {
            "nodes": [{"endpoint_id": item.endpoint.id, "method": item.endpoint.method, "path": item.endpoint.path} for item in ordered],
            "edges": [{"from": dependency, "to": item.endpoint.id} for item in ordered for dependency in item.depends_on_endpoint_ids],
            "strategy": "deterministic-resource-graph",
        }
        return ordered, graph

    @staticmethod
    def _topological_order(definitions: dict[int, StepDefinition]) -> list[StepDefinition]:
        children: dict[int, list[int]] = defaultdict(list)
        indegree = {endpoint_id: 0 for endpoint_id in definitions}
        for endpoint_id, definition in definitions.items():
            for dependency in definition.depends_on_endpoint_ids:
                if dependency in definitions:
                    children[dependency].append(endpoint_id)
                    indegree[endpoint_id] += 1
        queue = deque(sorted((endpoint_id for endpoint_id, degree in indegree.items() if degree == 0), key=lambda item: definitions[item].is_cleanup))
        ordered_ids = []
        while queue:
            current = queue.popleft(); ordered_ids.append(current)
            for child in children[current]:
                indegree[child] -= 1
                if indegree[child] == 0: queue.append(child)
        if len(ordered_ids) != len(definitions):
            ordered_ids.extend(endpoint_id for endpoint_id in definitions if endpoint_id not in ordered_ids)
        normal = [definitions[item] for item in ordered_ids if not definitions[item].is_cleanup]
        cleanup = [definitions[item] for item in reversed(ordered_ids) if definitions[item].is_cleanup]
        return normal + cleanup
