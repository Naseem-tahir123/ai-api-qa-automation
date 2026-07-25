import json
import yaml
import jsonref
from typing import List, Dict

class OpenAPIParser:
    @staticmethod
    def _strip_proxies(obj):
        """
        Recursively jsonref proxy objects ko pure Python dicts/lists mein tabdeel karta hai
        taake SQLAlchemy inko asani se database ke JSON column mein save kar sake.
        """
        if isinstance(obj, dict):
            return {k: OpenAPIParser._strip_proxies(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [OpenAPIParser._strip_proxies(item) for item in obj]
        else:
            return obj

    @staticmethod
    def parse_spec(file_path: str) -> List[Dict]:
        """
        OpenAPI file ko read karta hai, $ref resolve karta hai, aur endpoints nikalta hai.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.endswith(('.yaml', '.yml')):
                raw_data = yaml.safe_load(f)
            else:
                raw_data = json.load(f)

        # 1. $refs ko resolve karna (Yeh proxy objects return karega)
        resolved_spec = jsonref.replace_refs(raw_data)
        
        # 2. Proxy objects ko pure dictionary mein convert karna (Error Fix)
        pure_spec = OpenAPIParser._strip_proxies(resolved_spec)

        endpoints_list = []
        paths = pure_spec.get('paths', {})

        # 3. Paths aur Methods par loop lagana
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.lower() not in ['get', 'post', 'put', 'delete', 'patch']:
                    continue
                
                endpoint_data = {
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", "No Summary"),
                    "request_schema": details.get("requestBody", {}),
                    "response_schema": details.get("responses", {})
                }
                endpoints_list.append(endpoint_data)
                
        return endpoints_list