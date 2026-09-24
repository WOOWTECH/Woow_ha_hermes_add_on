# Woow Hermes Agent add-on for Home Assistant

**English** · 繁體中文見下方

Home Assistant add-on for [Hermes Agent](https://github.com/NousResearch/hermes-agent), built from
the image of [Woow_podman_hermes](https://github.com/WOOWTECH/Woow_podman_hermes).

- The dashboard and chat terminal in the Home Assistant sidebar (Ingress), with the same features
  as the LAN port `9119`.
- The OpenAI-compatible API (`8642`) and the webhook receiver (`8644`) on LAN ports, ready for a
  Cloudflare Tunnel from the Cloudflared add-on on the same Home Assistant.

See [hermes/DOCS.md](hermes/DOCS.md).

---

## 繁體中文

[Hermes Agent](https://github.com/NousResearch/hermes-agent) 的 Home Assistant add-on，映像來自
[Woow_podman_hermes](https://github.com/WOOWTECH/Woow_podman_hermes)。

- 儀表板與聊天終端機可從 HA 側邊欄（Ingress）操作，功能與區網 `9119` port 完全相同。
- OpenAI 相容 API（`8642`）與 Webhook 接收器（`8644`）開在區網 port，可由同一台 HA 上的
  Cloudflared add-on 建立對外網址。
