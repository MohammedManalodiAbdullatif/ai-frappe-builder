# AppSpec 2.0 Specification & Contract Reference

`AppSpec 2.0` is the single source of truth for the entire application generation pipeline.

## 1. Top-Level Specification Model
```json
{
  "$schema": "https://raw.githubusercontent.com/ai-frappe-builder/schemas/main/appspec-2.0.json",
  "spec_version": "2.0",
  "status": "ready",
  "archetype": "car_rental",
  "assumptions": [
    "Currency is USD",
    "Security deposit required upon booking"
  ],
  "questions": [],
  "app": {
    "app_name": "car_rental",
    "title": "Car Rental",
    "description": "Comprehensive fleet rental management system",
    "publisher": "Frappe Builder",
    "email": "developer@example.com",
    "license": "MIT",
    "version": "1.0.0",
    "requires_erpnext": true,
    "modules": ["Fleet"],
    "roles": ["Fleet Manager", "Rental Agent"],
    "doctypes": [],
    "workflows": [],
    "reports": [],
    "workspaces": []
  }
}
```

## 2. DocTypeSpec Schema
- `name`: Title Case singular name (e.g. `Rental Agreement`).
- `module`: Target module (e.g. `Fleet`).
- `kind`: `master` | `transaction` | `child` | `settings` | `log`.
- `istable`: `true` for 1-to-many child table grids; `false` otherwise.
- `is_submittable`: `true` for documents with submit/cancel lifecycle.
- `autoname`: Naming scheme (`naming_series:...`, `field:fieldname`, `hash`, `autoincrement`, `Prompt`).
- `fields`: Array of `FieldSpec`.
- `permissions`: Array of `PermissionSpec`.

## 3. RFC 6902 SpecPatch
Incremental mutations are expressed as RFC 6902 JSON Patches:
```json
{
  "description": "Add gps_tracking_id to Rental Vehicle",
  "operations": [
    {
      "op": "add",
      "path": "/app/doctypes/0/fields/-",
      "value": {
        "fieldname": "gps_tracking_id",
        "label": "GPS Tracking ID",
        "fieldtype": "Data",
        "reqd": false
      }
    }
  ]
}
```
Supported operators: `add`, `remove`, `replace`.
