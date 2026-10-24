# ADR 0001: Server-Sent Events (SSE) vs WebSocket for Streaming Pipeline Events

## Status
Accepted

## Context
The AI Frappe App Builder runs long-running multi-agent pipelines (Interview turns, Architect schema generation, validation, healing, AST script synthesis, and benchmark tests). The frontend needs real-time feedback:
- Streamed thinking and reasoning tokens.
- Immediate notification of state changes (`discovery -> drafting -> validating -> exporting`).
- Live progress updates on background jobs and bench tests.

We evaluated two primary streaming protocols:
1. **Server-Sent Events (SSE)** via `EventSource` over HTTP/1.1 or HTTP/2.
2. **WebSockets (WS)** for full-duplex communication over a persistent TCP connection.

## Decision
We chose **Server-Sent Events (SSE)** via `GET /api/v1/sessions/{session_id}/events` as the standard streaming transport.

## Rationale
1. **Unidirectional Simplicity**: User commands in our architecture are standard HTTP REST calls (`POST /api/v1/chat/message`, `POST /api/v1/spec/patch`, etc.) which return immediately with standard HTTP status codes, validation errors, and idempotency guarantees. The client does not need full-duplex socket multiplexing.
2. **Native Browser & Proxy Support**: SSE works over standard HTTP/HTTPS ports (80/443), seamlessly traverses firewalls, load balancers, corporate HTTP proxies, and cloud gateways without requiring WebSocket upgrade headers (`Upgrade: websocket`).
3. **Automatic Reconnection**: Browsers have built-in `EventSource` reconnection logic with `Last-Event-ID` tracking, allowing state recovery if a transient network drop occurs.
4. **Structured JSON Framing**: SSE natively frames messages by event type (`event: token`, `event: state_change`, `event: spec_patch`, `event: qa_progress`) which maps directly to our typed frontend event listeners.

## Consequences
- The client uses `EventSource` (or `fetch-event-source` for header auth) to listen for progress.
- All user mutations remain standard REST endpoints with explicit request/response typing.
- If bidirectional binary streaming is required in the future, it will be isolated to a dedicated socket endpoint.
