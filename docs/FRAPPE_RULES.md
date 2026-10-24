# Frappe v15 Deterministic Schema Rules & Knowledge Catalog

The Deterministic Validator (`ai_frappe_builder/validator/rule_engine.py`) evaluates 20+ invariant rules with zero LLM dependence.

## 1. Core Frappe Rules

| Rule ID | Name | Constraint & Rationale | Severity |
|---|---|---|---|
| `doctype_name_title_case` | Title Case Naming | DocType names must be Title Case (e.g., `Rental Agreement`). CamelCase or snake_case is rejected. | Error |
| `doctype_name_length` | DocType Name Bounds | Name length must be between 2 and 60 characters. | Error |
| `reserved_fieldname` | Reserved Names | Fieldnames cannot conflict with Frappe internals (`name`, `owner`, `creation`, `modified`, `docstatus`, `idx`, `parent`, `doctype`, etc.). | Error |
| `fieldname_snake_case` | Field Syntax | Must be lowercase snake_case starting with a letter (`^[a-z][a-z0-9_]*$`). | Error |
| `link_missing_options` | Link Options Target | `Link` fields must specify target DocType in `options`. | Error |
| `link_unknown_target` | Referential Target | `Link` options must exist in the spec or standard ERPNext core catalog (`knowledge/erpnext_doctypes.yaml`). | Error |
| `table_target_not_child` | Child Table Integrity | `Table` and `Table MultiSelect` options must target a DocType defined with `istable: true`. | Error |
| `child_table_permissions` | Child Permissions | DocTypes with `istable: 1` must NOT have permission rows (permissions are inherited from parent document). | Error |
| `child_table_autoname_hash` | Child Autoname | Child tables must use `autoname: "hash"`. | Error |
| `workflow_submittable_mismatch` | Submittable Lifecycle | If a workflow transitions to `doc_status: 1` (Submitted), the target DocType MUST have `is_submittable: true`. | Error |
| `missing_system_manager_role` | Administrator Access | Non-child DocTypes must include a permission row granting `System Manager` full CRUD (`read`, `write`, `create`, `delete`). | Error |
| `circular_mandatory_link` | Mandatory Deadlock | Prevents circular mandatory link dependencies (e.g. DocType A requires Link B on create, and DocType B requires Link A on create). | Error |
| `invalid_first_break` | Layout Break Order | DocType cannot start with a `Column Break` without an opening `Section Break` or `Tab Break`. | Error |
| `break_field_cannot_be_required` | Required Breaks | Layout break fields (`Section Break`, `Column Break`, `Tab Break`) cannot have `reqd: true`. | Error |
| `orphan_child_table` | Orphan Child Table | Warns if an `istable: 1` child table is defined but not embedded by any parent `Table` field. | Warning |
| `max_fields_exceeded` | Recommended Field Cap | Warns if a single DocType exceeds 40 data fields. | Warning |
