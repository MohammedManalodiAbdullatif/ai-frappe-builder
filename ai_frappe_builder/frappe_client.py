"""
frappe_client.py — Async wrapper around the Frappe REST API.

Authentication uses token-based auth:
  Authorization: token {api_key}:{api_secret}

All Frappe responses follow the shape:
  {"data": <single-record-dict>}   for GET /api/resource/<DocType>/<name>
  {"data": [<list-of-dicts>]}      for GET /api/resource/<DocType>
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class FrappeAPIError(Exception):
    """Raised when the Frappe REST API returns an error response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Frappe API error {status_code}: {detail}")


class FrappeClient:
    """
    Async Frappe REST API client.

    Usage:
        async with FrappeClient(url, key, secret) as client:
            apps = await client.get_installed_apps()
    """

    def __init__(self, base_url: str, api_key: str, api_secret: str):
        self.base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> FrappeClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "FrappeClient must be used as an async context manager"
            )
        return self._client

    async def _get(self, path: str, params: dict | None = None) -> Any:
        client = self._ensure_client()
        resp = await client.get(path, params=params)
        self._raise_for_status(resp)
        return resp.json()

    async def _post(self, path: str, json: dict) -> Any:
        client = self._ensure_client()
        resp = await client.post(path, json=json)
        self._raise_for_status(resp)
        return resp.json()

    async def _put(self, path: str, json: dict) -> Any:
        client = self._ensure_client()
        resp = await client.put(path, json=json)
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code >= 400:
            try:
                detail = resp.json().get("exception") or resp.text
            except Exception:
                detail = resp.text
            raise FrappeAPIError(resp.status_code, detail)

    # ------------------------------------------------------------------
    # Site introspection
    # ------------------------------------------------------------------

    async def get_installed_apps(self) -> list[str]:
        """Return list of installed Frappe app names."""
        try:
            data = await self._get(
                "/api/method/frappe.utils.get_installed_apps_info"
            )
            apps = data.get("message", [])
            return [a.get("app_name", "") for a in apps if isinstance(a, dict)]
        except FrappeAPIError:
            pass

        try:
            data = await self._get(
                "/api/resource/Installed Applications/Installed Applications"
            )
            apps = data.get("data", {}).get("installed_applications", [])
            if apps:
                return [a.get("app_name", "") for a in apps if a.get("app_name")]
        except FrappeAPIError:
            pass

        try:
            data = await self._get("/api/method/frappe.get_installed_apps")
            return data.get("message", [])
        except FrappeAPIError:
            return ["frappe"]

    async def get_all_doctypes(self) -> list[dict]:
        """Return list of all DocType meta dicts (name + module at minimum)."""
        data = await self._get(
            "/api/resource/DocType",
            params={"fields": '["name","module","istable"]', "limit_page_length": 2000},
        )
        return data.get("data", [])

    async def get_doctype_meta(self, doctype: str) -> dict:
        """Return full meta for a single DocType."""
        data = await self._get(f"/api/resource/DocType/{doctype}")
        return data.get("data", {})

    async def get_all_modules(self) -> list[str]:
        """Return list of all module names on the site."""
        data = await self._get(
            "/api/resource/Module Def",
            params={"fields": '["name"]', "limit_page_length": 500},
        )
        return [m["name"] for m in data.get("data", [])]

    async def module_exists(self, module_name: str) -> bool:
        """Check if a Module Def exists on the site."""
        try:
            await self._get(f"/api/resource/Module Def/{module_name}")
            return True
        except FrappeAPIError as exc:
            if exc.status_code == 404:
                return False
            raise

    async def create_module(self, module_name: str, app_name: str = "frappe") -> dict:
        """Create a new Module Def if missing."""
        payload = {
            "doctype": "Module Def",
            "module_name": module_name,
            "app_name": app_name,
            "custom": 1,
        }
        return await self._post("/api/resource/Module Def", payload)

    async def get_all_roles(self) -> list[str]:
        """Return list of all Role names on the site."""
        data = await self._get(
            "/api/resource/Role",
            params={"fields": '["name"]', "limit_page_length": 500},
        )
        return [r["name"] for r in data.get("data", [])]

    async def doctype_exists(self, name: str) -> bool:
        """Check whether a DocType already exists on the site."""
        try:
            data = await self._get(f"/api/resource/DocType/{name}")
            return bool(data.get("data"))
        except FrappeAPIError as exc:
            if exc.status_code == 404:
                return False
            raise

    async def role_exists(self, role: str) -> bool:
        """Check whether a Role already exists on the site."""
        try:
            data = await self._get(f"/api/resource/Role/{role}")
            return bool(data.get("data"))
        except FrappeAPIError as exc:
            if exc.status_code == 404:
                return False
            raise

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    async def create_role(self, role_name: str) -> dict:
        """Create a new Role on the Frappe site."""
        return await self._post(
            "/api/resource/Role",
            {"doctype": "Role", "role_name": role_name},
        )

    async def create_doctype(self, spec: dict) -> dict:
        """
        Create a DocType using the Frappe REST API.

        `spec` must already be in Frappe's wire format (not the AppSpec format).
        """
        logger.info("Creating DocType: %s", spec.get("name"))
        return await self._post("/api/resource/DocType", spec)

    async def create_workflow(self, spec: dict) -> dict:
        """Create a Workflow on the Frappe site."""
        logger.info("Creating Workflow: %s", spec.get("name"))
        return await self._post("/api/resource/Workflow", spec)

    async def create_document(self, doctype: str, data: dict) -> dict:
        """Create any Frappe document (for seeding sample data)."""
        payload = {"doctype": doctype, **data}
        return await self._post(f"/api/resource/{doctype}", payload)

    async def post(self, endpoint: str, data: dict) -> dict:
        """Generic public POST to any Frappe endpoint."""
        return await self._post(endpoint, data)

    async def get(self, endpoint: str, params: dict | None = None) -> dict:
        """Generic public GET from any Frappe endpoint."""
        return await self._get(endpoint, params)

    async def delete(self, endpoint: str) -> dict:
        """Generic public DELETE from any Frappe endpoint."""
        client = self._ensure_client()
        resp = await client.delete(endpoint)
        self._raise_for_status(resp)
        try:
            return resp.json()
        except Exception:
            return {"message": "ok"}

    async def create_server_script(self, spec: dict) -> dict:
        """Create a Server Script DocType record on Frappe."""
        payload = {
            "doctype": "Server Script",
            "name": spec.get("name"),
            "script_type": spec.get("script_type", "DocType Event"),
            "reference_doctype": spec.get("reference_doctype"),
            "doctype_event": spec.get("doctype_event", "Before Save"),
            "script": spec.get("script", ""),
            "disabled": 0,
        }
        return await self._post("/api/resource/Server Script", payload)

    async def create_client_script(self, spec: dict) -> dict:
        """Create a Client Script DocType record on Frappe."""
        payload = {
            "doctype": "Client Script",
            "name": spec.get("name"),
            "dt": spec.get("reference_doctype"),
            "script": spec.get("script", ""),
            "enabled": 1,
            "view": spec.get("view", "Form"),
        }
        return await self._post("/api/resource/Client Script", payload)

    # ------------------------------------------------------------------
    # Site introspection bundle
    # ------------------------------------------------------------------

    async def introspect_site(self) -> dict:
        """
        Return a dict with:
          installed_apps, doctypes (list of {name, module, istable}),
          modules, roles
        Used by the planner to understand what already exists on the site.
        """
        installed_apps: list[str] = []
        doctypes: list[dict] = []
        modules: list[str] = []
        roles: list[str] = []

        try:
            installed_apps = await self.get_installed_apps()
        except Exception as exc:
            logger.warning("Could not fetch installed apps: %s", exc)

        try:
            doctypes = await self.get_all_doctypes()
        except Exception as exc:
            logger.warning("Could not fetch doctypes: %s", exc)

        try:
            modules = await self.get_all_modules()
        except Exception as exc:
            logger.warning("Could not fetch modules: %s", exc)

        try:
            roles = await self.get_all_roles()
        except Exception as exc:
            logger.warning("Could not fetch roles: %s", exc)

        return {
            "installed_apps": installed_apps,
            "doctypes": doctypes,
            "modules": modules,
            "roles": roles,
        }
