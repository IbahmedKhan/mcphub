"""API Gateway — Universal REST API connector that lets AI call any API."""
import json
import time
import sys
import os
from typing import Any

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from orchestrator.security import validate_url


class APIGateway:
    """Connects AI to any REST API — register endpoints, call them, chain workflows."""

    def __init__(self):
        self._apis: dict[str, dict] = {}
        self._call_history: list[dict] = []
        self._max_history = 1000

    async def dispatch(self, tool: str, params: dict) -> Any:
        methods = {
            "call_api": self.call_api,
            "register_api": self.register_api,
            "list_apis": self.list_apis,
            "test_endpoint": self.test_endpoint,
            "create_workflow": self.create_workflow,
        }
        if tool not in methods:
            raise ValueError(f"Unknown tool: {tool}")
        return await methods[tool](**params)

    async def register_api(self, name: str, base_url: str, description: str = "",
                            auth_type: str = "none", auth_value: str = "",
                            default_headers: dict = None) -> dict:
        """Register an external API for AI to use."""
        self._apis[name] = {
            "name": name,
            "base_url": base_url.rstrip("/"),
            "description": description,
            "auth_type": auth_type,
            "auth_value": auth_value,
            "default_headers": default_headers or {},
            "registered_at": time.time(),
            "call_count": 0,
        }
        return {"status": "registered", "name": name, "base_url": base_url,
                "description": description}

    async def call_api(self, name: str = None, url: str = None, method: str = "GET",
                        path: str = "", params: dict = None, body: dict = None,
                        headers: dict = None) -> dict:
        """Call a registered API or any URL directly."""
        start = time.time()

        # SSRF protection: validate URL before requesting
        if url:
            validate_url(url)

        # Build request
        if name and name in self._apis:
            api = self._apis[name]
            full_url = f"{api['base_url']}/{path.lstrip('/')}" if path else api["base_url"]
            req_headers = {**api.get("default_headers", {})}
            if api["auth_type"] == "bearer":
                req_headers["Authorization"] = f"Bearer {api['auth_value']}"
            elif api["auth_type"] == "api_key":
                req_headers["X-API-Key"] = api["auth_value"]
            api["call_count"] += 1
        elif url:
            full_url = url
            req_headers = {}
        else:
            return {"error": "Provide either 'name' (registered API) or 'url' (direct)."}

        if headers:
            req_headers.update(headers)
        req_headers.setdefault("Content-Type", "application/json")

        try:
            resp = requests.request(
                method=method.upper(),
                url=full_url,
                params=params,
                json=body if body and method.upper() in ("POST", "PUT", "PATCH") else None,
                headers=req_headers,
                timeout=30,
            )
            elapsed = round((time.time() - start) * 1000, 2)

            # Parse response
            try:
                resp_body = resp.json()
            except (json.JSONDecodeError, ValueError):
                resp_body = resp.text[:5000]

            entry = {
                "url": full_url, "method": method.upper(), "status": resp.status_code,
                "response_ms": elapsed, "timestamp": time.time(),
            }
            self._call_history.append(entry)
            if len(self._call_history) > self._max_history:
                self._call_history = self._call_history[-self._max_history:]

            return {
                "status_code": resp.status_code,
                "success": 200 <= resp.status_code < 300,
                "response": resp_body,
                "headers": dict(resp.headers),
                "response_ms": elapsed,
                "url": full_url,
                "method": method.upper(),
            }
        except requests.Timeout:
            return {"error": "Request timed out (30s)", "url": full_url}
        except requests.ConnectionError:
            return {"error": f"Cannot connect to {full_url}", "url": full_url}
        except Exception as e:
            return {"error": str(e), "url": full_url}

    async def list_apis(self) -> dict:
        """List all registered APIs."""
        apis = []
        for name, api in self._apis.items():
            apis.append({
                "name": api["name"],
                "base_url": api["base_url"],
                "description": api["description"],
                "auth_type": api["auth_type"],
                "call_count": api["call_count"],
            })
        return {"apis": apis, "count": len(apis)}

    async def test_endpoint(self, url: str, method: str = "GET") -> dict:
        """Test if an API endpoint is reachable and responsive."""
        validate_url(url)
        start = time.time()
        try:
            resp = requests.request(method, url, timeout=10)
            elapsed = round((time.time() - start) * 1000, 2)
            return {
                "url": url, "reachable": True, "status_code": resp.status_code,
                "response_ms": elapsed,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": len(resp.content),
            }
        except Exception as e:
            return {"url": url, "reachable": False, "error": str(e)}

    async def create_workflow(self, name: str, steps: list[dict]) -> dict:
        """Create a multi-step API workflow (chain multiple API calls).

        Each step: {"api": "name", "method": "GET", "path": "/endpoint", "params": {}}
        Results from previous steps can be referenced as {{step_N.field}}.
        """
        results = []
        context = {}

        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i+1}")
            # Resolve references to previous step results
            resolved_step = self._resolve_refs(step, context)

            result = await self.call_api(
                name=resolved_step.get("api"),
                url=resolved_step.get("url"),
                method=resolved_step.get("method", "GET"),
                path=resolved_step.get("path", ""),
                params=resolved_step.get("params"),
                body=resolved_step.get("body"),
            )
            context[step_name] = result
            results.append({"step": step_name, "result": result})

            # Stop on failure if configured
            if step.get("stop_on_error") and not result.get("success", True):
                results.append({"step": "workflow_stopped", "reason": f"{step_name} failed"})
                break

        return {"workflow": name, "steps_executed": len(results), "results": results}

    def _resolve_refs(self, step: dict, context: dict) -> dict:
        """Replace {{step_name.field}} references with actual values."""
        step_str = json.dumps(step)
        for ctx_name, ctx_data in context.items():
            if isinstance(ctx_data, dict):
                for key, value in ctx_data.items():
                    ref = f"{{{{{ctx_name}.{key}}}}}"
                    if ref in step_str:
                        step_str = step_str.replace(ref, json.dumps(value) if not isinstance(value, str) else value)
        return json.loads(step_str)
