# ADR 0003: Native Controller Code (`<dt>.py`) vs Server Script Documents in Exported Apps

## Status
Accepted

## Context
Frappe supports two methods for custom business logic execution:
1. **Native Python Controller Code**: Python files inside the app's module directory (`<module>/doctype/<doctype>/<doctype>.py`), inheriting from `frappe.model.document.Document` with lifecycle hooks (`validate()`, `before_save()`, `on_submit()`, `on_cancel()`).
2. **Server Script DocType Records**: In-database Python scripts saved as `Server Script` documents in the Frappe database, executed in a restricted runtime sandbox.

## Decision
For standard installable Frappe apps (`mode: "app"`), business logic is exported strictly into **Native Python Controller files (`<doctype>.py`)**.

For live site extension (`mode: "customization"`), logic is exported into **Server Script & Client Script fixtures** stored in `fixtures/server_script.json`.

## Rationale
1. **Idiomatic Frappe Standards**: Production Frappe applications (`erpnext`, `hrms`, `payments`, etc.) place business logic in version-controlled Python controller classes, never in in-database `Server Script` documents.
2. **Performance & AST Analysis**: Native controller code executes directly as compiled Python bytecode without runtime database fetches or eval string overhead, and can be typechecked with `mypy` and formatted with `ruff`.
3. **Security Constraints**: By default, Frappe disables `Server Script` execution in production unless `server_script_enabled: true` is explicitly configured in `common_site_config.json`. An exported app should install without forcing manual changes to the host bench security policy.

## Consequences
- The ScriptWriter agent targets standard Document controller methods in `<doctype>.py`.
- Full Git version control, unit testing with `FrappeTestCase`, and static code analysis work out of the box.
- The alternative `mode: "customization"` remains available for users who specifically need no-code database fixtures for existing live sites.
