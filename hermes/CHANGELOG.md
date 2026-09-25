# Changelog

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
