# Changelog

## 0.1.3

- The sidebar chat now ends the same way as on the LAN port. HA ingress turns every WebSocket
  close into a clean 1000, so a chat taken over by another tab, or whose agent exited, showed
  "[session ended (code 1000)]", and the chat and live feeds did not reconnect after an add-on
  restart. A small relay in the add-on records how Hermes closed each ingress WebSocket, and the
  sidebar page restores that code.
- The agent keeps Hermes' default approval settings. The podman stack's approval policy (no
  approvals, cron yolo) never actually took effect on this Hermes version; the dead code that
  looked like it applied it is removed, and the docs now describe the real behaviour.

## 0.1.2

- Fix: `platforms.webhook` was never written to config.yaml in 0.1.1, so the Webhooks page still
  showed the receiver as disabled.

## 0.1.1

- Sidebar and LAN port keep separate Hermes sessions: a login on `http://<ha-ip>:9119` no longer
  logs the sidebar in, and logging out of one no longer affects the other.
- Session export and Swagger "Try it out" now work in the sidebar.
- The Webhooks page shows the receiver as enabled (`platforms.webhook` is written to config.yaml
  on first start).
- Login page favicon loads inside the sidebar.

## 0.1.0

- First release: Hermes Agent v2026.8.31 (dashboard 0.21.0) with the Woow_podman_hermes `slim`
  additions, dashboard in the HA sidebar through Ingress, LAN ports 8642/9119/8644.
