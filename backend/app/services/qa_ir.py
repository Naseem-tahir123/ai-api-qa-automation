"""Deterministic OpenAPI endpoint normalisation used by planning and AI jobs."""
import hashlib
import json
import re
from collections import defaultdict
from typing import Any, Iterable


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
SENSITIVE_WORDS = {"payment", "billing", "card", "auth", "login", "token", "admin", "role", "permission"}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _resource(path: str) -> str:
    parts = [part for part in path.split("/") if part and not part.startswith("{")]
    return parts[-1].rstrip("s") or "root" if parts else "root"


def _classify(endpoint: dict[str, Any]) -> dict[str, Any]:
    method, path = endpoint["method"], endpoint["path"]
    searchable = " ".join([path, endpoint.get("summary") or "", " ".join(endpoint.get("tags") or [])]).lower()
    security = endpoint.get("security") or []
    action = "read" if method in SAFE_METHODS else "destructive" if method == "DELETE" else "write"
    crud = ("create" if method == "POST" and "{" not in path else "read" if method == "GET"
            else "update" if method in {"PUT", "PATCH"} else "delete" if method == "DELETE" else "action")
    high_risk = action == "destructive" or bool(SENSITIVE_WORDS.intersection(searchable.split()))
    return {"resource": _resource(path), "crud": crud, "access": "protected" if security else "public",
            "action": action, "high_risk": high_risk,
            "async": any(code in (endpoint.get("responses") or {}) for code in ("202", 202)),
            "domains": sorted(word for word in SENSITIVE_WORDS if word in searchable)}


def build_qa_ir(endpoints: Iterable[Any], spec_version: str) -> dict[str, Any]:
    """Create a compact, serialisable QA model without retaining raw OpenAPI."""
    records: list[dict[str, Any]] = []
    resource_graph: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for ep in endpoints:
        raw = {
            "id": ep.id, "path": ep.path, "method": ep.method.upper(), "summary": ep.summary,
            "parameters": ep.parameters or [], "request_schema": ep.request_schema or {},
            "responses": ep.response_schema or {}, "security": ep.security or [],
            "tags": ep.tags or [],
        }
        traits = _classify(raw)
        raw.update(traits)
        raw["schema_fingerprint"] = fingerprint({key: raw[key] for key in ("parameters", "request_schema", "responses", "security")})
        raw["resource_ids"] = [p.get("name") for p in raw["parameters"] if p.get("in") == "path" and p.get("name")]
        records.append(raw)
        resource_graph[traits["resource"]][traits["crud"]].append(f"{raw['method']} {raw['path']}")
    document = {"schema_version": "qa-ir/v1", "spec_version": spec_version, "endpoints": records,
                "resource_graph": {key: dict(value) for key, value in resource_graph.items()}}
    document["fingerprint"] = fingerprint(document)
    return document


def diff_qa_ir(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, list[str]]:
    old = {f"{e['method']} {e['path']}": e["schema_fingerprint"] for e in (previous or {}).get("endpoints", [])}
    new = {f"{e['method']} {e['path']}": e["schema_fingerprint"] for e in current.get("endpoints", [])}
    return {"added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
            "changed": sorted(key for key in new.keys() & old.keys() if new[key] != old[key])}
