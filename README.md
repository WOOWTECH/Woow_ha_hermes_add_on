<p align="center">
  <img src="hermes/logo.png" alt="Hermes Agent" width="160"/>
</p>

<h1 align="center">Woow Hermes Agent — Home Assistant Add-on</h1>

<p align="center">
  <b><a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> (NousResearch) packaged as a Home Assistant add-on.</b><br/>
  Dashboard and chat terminal in the HA sidebar, identical to the LAN port;
  OpenAI-compatible API and webhooks ready for a Cloudflare Tunnel.<br/>
  <b>把 NousResearch 的 Hermes Agent 包成 Home Assistant add-on。</b><br/>
  儀表板與聊天終端機放進 HA 側邊欄，功能與區網 port 完全一致；OpenAI 相容 API 與 Webhook 可經 Cloudflare Tunnel 對外。
</p>

<p align="center">
  <a href="https://github.com/WOOWTECH/Woow_ha_hermes_add_on/releases"><img src="https://img.shields.io/github/v/release/WOOWTECH/Woow_ha_hermes_add_on?label=release&color=blue" alt="Release"/></a>
  <a href="https://github.com/WOOWTECH/Woow_ha_hermes_add_on/actions/workflows/publish-hermes-addon-images.yml"><img src="https://img.shields.io/github/actions/workflow/status/WOOWTECH/Woow_ha_hermes_add_on/publish-hermes-addon-images.yml?label=build" alt="Build"/></a>
  <img src="https://img.shields.io/badge/HA%20add--on-Supervisor-41BDF5?logo=home-assistant&logoColor=white" alt="Home Assistant Add-on"/>
  <img src="https://img.shields.io/badge/arch-amd64-lightgrey" alt="amd64"/>
  <img src="https://img.shields.io/badge/Hermes%20Agent-v2026.8.31-8A2BE2" alt="Hermes Agent v2026.8.31"/>
</p>

<p align="center">
  <a href="#繁體中文">繁體中文</a> ·
  <a href="#english">English</a> ·
  <a href="hermes/README.md">完整說明 / Full guide</a> ·
  <a href="hermes/DOCS.md">DOCS</a> ·
  <a href="hermes/CHANGELOG.md">CHANGELOG</a> ·
  <a href="docs/testing/">測試報告 / Test reports</a>
</p>

---

## 繁體中文

### 這是什麼

[Hermes Agent](https://github.com/NousResearch/hermes-agent) 是 NousResearch 的自架 AI agent：網頁儀表板、瀏覽器裡的聊天終端機、排程、MCP、Skills、Kanban、OpenAI 相容 API 與 Webhook。
本 add-on 以 [Woow_podman_hermes](https://github.com/WOOWTECH/Woow_podman_hermes) 的 `slim` 映像為基礎，做成 Home Assistant add-on：

- **HA 側邊欄**：透過 HA Ingress 操作儀表板與聊天終端機，功能與區網 `http://<HA IP>:9119` 完全相同（登入、WebSocket、檔案上傳下載、Swagger、F5 停在原頁都一致）。
- **對外入口**：OpenAI 相容 API（`8642`）與 Webhook 接收器（`8644`）開在區網 port，由同一台 HA 上的 Cloudflared add-on 建立 HTTPS 公開網址。
- **預建映像**：從 GHCR 直接下載，不在 HA 主機上建置。
- **安全**：排程、API、Webhook 觸發的危險指令一律拒絕；Supervisor token 不會交給 agent。

### 安裝

1. HA → **設定 → 附加元件 → 附加元件商店 → 右上角 ⋮ → 儲存庫**，加入：
   ```
   https://github.com/WOOWTECH/Woow_HA_App_Store
   ```
2. 在商店找到 **Woow Hermes Agent**，按 **安裝**（下載約 1 GB 映像）。
3. 在「資訊」頁打開 **開機時啟動**、**Watchdog**、**在側邊欄顯示**，按 **啟動**。
4. 到「設定」頁看自動產生的 **儀表板密碼**（點眼睛圖示），從側邊欄的 **Hermes** 用 `admin` 登入。
5. 在儀表板設定模型供應商與金鑰。

詳細設定、Cloudflare Tunnel、安全與常見問題請看 **[hermes/README.md](hermes/README.md)**。

### 入口與 port

| 入口 | 網址 | 驗證 |
|---|---|---|
| 儀表板 + 聊天終端機 | HA 側邊欄 **Hermes** | HA 登入，再登入 Hermes |
| 儀表板 + 聊天終端機 | `http://<HA IP>:9119` | Hermes 登入 |
| OpenAI 相容 API | `http://<HA IP>:8642/v1` | `Authorization: Bearer <Gateway API 金鑰>` |
| Webhook 接收器 | `http://<HA IP>:8644/webhooks/<route>` | HMAC（Webhook 密鑰） |

### 系統需求

- Home Assistant OS 或 Supervised，**amd64（x86-64）** 主機。
- RAM 至少 4 GB，建議 8 GB 以上（add-on 平常約 0.4–1.3 GB，使用瀏覽器工具時約 2 GB）。
- 磁碟可用空間至少 5 GB（映像解壓後約 3.3 GB）。

### 驗證狀況

0.1.6 在真實 HAOS 上以實際的 ChatGPT 模型做過兩輪全面實測：對話、工具、排程、MCP、Skills、Kanban、WebSocket、API、Webhook 與各頁面，**側邊欄與區網直連之間沒有任何功能差異**。報告在 [`docs/testing/`](docs/testing/)。

---

## English

### What it is

[Hermes Agent](https://github.com/NousResearch/hermes-agent) is NousResearch's self-hosted AI agent: web dashboard, in-browser chat terminal, scheduled jobs, MCP, skills, kanban, an OpenAI-compatible API and webhooks.
This add-on packages the `slim` image of [Woow_podman_hermes](https://github.com/WOOWTECH/Woow_podman_hermes) for Home Assistant:

- **HA sidebar**: the dashboard and chat terminal through HA Ingress, working exactly like the LAN port `http://<HA IP>:9119`.
- **Machine entrances**: the OpenAI-compatible API (`8642`) and the webhook receiver (`8644`) on LAN ports, ready for a Cloudflare Tunnel from the Cloudflared add-on on the same Home Assistant.
- **Prebuilt image** on GHCR; nothing is built on the Home Assistant host.
- **Safety**: dangerous commands from scheduled jobs, the API and webhooks are refused; the agent never sees the Supervisor token.

### Install

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, add
   `https://github.com/WOOWTECH/Woow_HA_App_Store`.
2. Install **Woow Hermes Agent** (about 1 GB to download).
3. On the Info tab turn on **Start on boot**, **Watchdog** and **Show in sidebar**, then **Start**.
4. Reveal the generated **Dashboard password** on the Configuration tab and sign in as `admin` from the **Hermes** sidebar entry.
5. Set up a model provider in the dashboard.

Requirements: Home Assistant OS or Supervised on **amd64**, 4 GB RAM minimum (8 GB recommended), 5 GB free disk.
Full guide: [hermes/README.md](hermes/README.md) (Traditional Chinese) and [hermes/DOCS.md](hermes/DOCS.md) (English).

---

## Repository layout | 倉庫結構

```
.
├── hermes/                     # the add-on (synced to Woow_HA_App_Store/woow-hermes)
│   ├── config.yaml             # add-on manifest: ports, ingress, options schema
│   ├── Dockerfile              # FROM nousresearch/hermes-agent (pinned by digest)
│   ├── README.md · DOCS.md · CHANGELOG.md · icon.png · logo.png
│   ├── translations/           # en, zh-Hant option labels
│   ├── patches/                # WOOWTECH patches to upstream Hermes (build fails if an anchor moves)
│   ├── vendor/podman/          # files vendored from Woow_podman_hermes (see PROVENANCE)
│   ├── rootfs/                 # s6 services, cont-init scripts, nginx ingress adapter, ws relay
│   └── test/                   # unit tests, local HA-ingress emulator, parity and browser tests
├── docs/testing/               # test reports
└── .github/workflows/          # build → test → GHCR → GitHub Release
```

## Release flow | 發佈流程

1. Bump `version` in `hermes/config.yaml` and add a `## x.y.z` section to `hermes/CHANGELOG.md`, then push to `main`.
2. [`publish-hermes-addon-images.yml`](.github/workflows/publish-hermes-addon-images.yml) runs the unit tests, builds and pushes `ghcr.io/woowtech/woow-ha-hermes-amd64:<version>`, runs the approval-gate test inside that image, checks the image can be pulled anonymously, and only then creates GitHub Release `v<version>`.
3. [Woow_HA_App_Store](https://github.com/WOOWTECH/Woow_HA_App_Store) syncs `hermes/` from the latest Release into `woow-hermes/` (nightly, or run its `sync-upstreams.yml`). A failed test means no Release, so the store never offers a broken version.

版本號改在 `hermes/config.yaml` 並補 CHANGELOG，推上 `main` 後 CI 自動測試、建置、推 GHCR、建 Release；商店每晚從最新 Release 同步。測試沒過就不會建 Release，商店也不會拿到壞掉的版本。

## Related | 相關專案

| Platform | Repository |
|---|---|
| Home Assistant add-on store | [Woow_HA_App_Store](https://github.com/WOOWTECH/Woow_HA_App_Store) |
| Podman / Quadlet | [Woow_podman_hermes](https://github.com/WOOWTECH/Woow_podman_hermes) |
| K3s / Kubernetes | [Woow_k3s_hermes](https://github.com/WOOWTECH/Woow_k3s_hermes) |
| Upstream | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) |

## Credits | 致謝

Hermes Agent is developed by [Nous Research](https://nousresearch.com) and released under the MIT License; the icon and logo are its official app icon.
This repository contains the Home Assistant packaging, maintained by [WOOWTECH](https://github.com/WOOWTECH). Bundled third-party tools keep their own licenses.
