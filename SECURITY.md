# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly by emailing the maintainer directly rather than opening a public
issue.

## Scope

This project is an MCP server that orchestrates AI workflows defined in
markdown. Security considerations include:

- **Workflow files** — Workflow definitions may contain sensitive project
  context, tool specifications, or internal process details. Review before
  sharing publicly.
- **Variable state** — Workflow variables (`output_variables`) may accumulate
  sensitive data during execution (API keys, tokens, internal URLs). State is
  held in memory only and not persisted to disk.
- **MCP transport** — The server communicates over stdio by default. Ensure
  your MCP client configuration does not expose the transport to untrusted
  processes.

## Best Practices

- Don't commit workflow files containing secrets or internal URLs
- Review workflow variable outputs before logging or sharing
- Keep your MCP client configuration secure
- Don't expose the MCP server to untrusted network access
