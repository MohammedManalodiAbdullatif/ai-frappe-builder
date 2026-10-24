# Frontend Design System & Architecture Specification

## 1. Visual Direction & Aesthetic Philosophy
A modern, dense, high-clarity developer tool workbench inspired by Linear, Frappe Desk, and modern cloud consoles.
- **Typography**: Inter / Plus Jakarta Sans for UI, JetBrains Mono / Fira Code for code, JSON, and schemas.
- **Color Palette**:
  - Dark Canvas: `#0f172a` (Slate 900) / Surface: `#1e293b` (Slate 800) / Elevated: `#334155` (Slate 700)
  - Light Accent: `#f8fafc` (Slate 50) / Border: `#334155` / Muted: `#94a3b8`
  - Frappe Blue: `#0089ff` / Emerald (Valid): `#10b981` / Amber (Warning): `#f59e0b` / Rose (Error): `#f43f5e`
  - Spacing: 4px base grid (4px, 8px, 12px, 16px, 24px)
  - Radii: 6px (cards), 4px (inputs, badges), 9999px (pills)

## 2. Three-Panel Layout Architecture
```
+----------------------------------------------------------------------------------------------------+
|  Top Header: App Title | Session ID | Connection Badge | Token Counter | Theme Toggle | Actions    |
+--------------------------+------------------------------------------------+------------------------+
| LEFT PANEL (320px-380px) | CENTRE WORKBENCH (Fluid flex-1)                | RIGHT PANEL (320px)    |
|                          |                                                |                        |
| • Orchestrator Stepper   | Tab Bar:                                       | • Real-time Validation |
|   (Discovery -> Done)    | [ERD Model] [Form Preview] [Workflow] [Files]  |   (Errors & Fix Hints) |
| • Conversation Stream    |                                                | • Bench QA Results     |
| • Question Card          | Active Tab Content:                            | • Version History      |
|   (Interactive Options)  | • ERD Diagram (Interactive Nodes & Relations)  | • One-Click Export     |
| • Assumption Chips       | • Desk Form Simulator                          |   (Download .zip)      |
| • Chat Input Box         | • Code / File Tree Inspector                   |                        |
+--------------------------+------------------------------------------------+------------------------+
```

## 3. Real-Time Streaming Contract (SSE)
- Uses native browser `EventSource` connected to `/api/v1/sessions/:id/events`.
- Events:
  - `state_change`: Updates orchestrator stepper.
  - `token`: Streams conversational output.
  - `question`: Renders interactive discovery question card with pill choices.
  - `validation`: Updates right-panel validation report.
  - `spec_patch`: Triggers visual animation of modified spec elements.
