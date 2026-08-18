import json
import yaml
import jsonref
from typing import List, Dict
from langsmith import traceable


class OpenAPIParser:
    @staticmethod
    def _strip_proxies(obj):
        """
        Recursively converts jsonref proxy objects into native Python dictionaries
        and lists so they can be safely stored in SQLAlchemy JSON columns.
        """
        if isinstance(obj, dict):
            return {k: OpenAPIParser._strip_proxies(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [OpenAPIParser._strip_proxies(item) for item in obj]
        else:
            return obj
    @traceable(name="parse_openai_spec")
    @staticmethod
    def parse_spec(file_path: str) -> List[Dict]:
        """
        Reads an OpenAPI specification file, resolves references,
        and extracts API endpoint details.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.endswith(('.yaml', '.yml')):
                raw_data = yaml.safe_load(f)
            else:
                raw_data = json.load(f)

        # 1. Resolve OpenAPI $ref references (returns proxy objects).
        resolved_spec = jsonref.replace_refs(raw_data)

        # 2. Convert proxy objects into standard Python dictionaries.
        # This prevents errors when saving data into JSON database columns.
        pure_spec = OpenAPIParser._strip_proxies(resolved_spec)

        endpoints_list = []
        paths = pure_spec.get('paths', {})
        global_security = pure_spec.get('security', [])

        # 3. Iterate through all API paths and supported HTTP methods.
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue

                operation_security = details.get("security", global_security)

                endpoint_data = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", "No Summary"),
                    "request_schema": details.get("requestBody", {}),
                    "response_schema": details.get("responses", {}),
                    "parameters": details.get("parameters", []),
                    "security": operation_security
                }

                endpoints_list.append(endpoint_data)

        return endpoints_list