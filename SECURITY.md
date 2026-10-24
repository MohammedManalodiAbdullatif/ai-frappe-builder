# Security Policy

## 1. Secrets Management
- All sensitive credentials (API keys, Frappe site secrets, tokens) **MUST NEVER** be committed to version control.
- Store secrets exclusively in local `.env` files (which are ignored via `.gitignore`).
- The application automatically strips sensitive credentials from exported apps and logs.

## 2. Reporting a Vulnerability
If you discover a potential security vulnerability in this project, please report it privately:
- **Email**: security@example.com
- Do not create public GitHub issues for security vulnerabilities.
