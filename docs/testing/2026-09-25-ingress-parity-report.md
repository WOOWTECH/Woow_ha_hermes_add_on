# Woow Hermes Agent add-on：HA 側邊欄與區網直連功能一致性測試報告

- 日期：2026-09-24 至 2026-09-25
- 受測版本：add-on 0.1.0 → **0.1.3**（Hermes Agent v2026.8.31，dashboard 0.21.0）
- 環境：正式 HAOS（amd64，HA Core 2026.7.2，Supervisor 2026.09.2），以本地測試版 add-on `local_woow_hermes_test` 安裝
- 模型：使用者的 ChatGPT 登入（provider `openai-codex`，model `gpt-5.5`）

每一項都在三條路徑上對照：

| 代號 | 路徑 |
|---|---|
| **D** | 區網直連 `http://<HA-IP>:9119/` |
| **IL** | 區網的 HA 側邊欄（HA Ingress） |
| **IC** | 經 Cloudflare Tunnel 的 HA 側邊欄（HA Ingress） |

## 1 結論

**0.1.3 已達成需求：在 HA 側邊欄操作 dashboard，功能與區網直連 `:9119` 一致。**

- 測試過程找到 7 項 add-on 造成的差異，全部已修正，並在正式機上驗證（見第 3 節）。
- 還剩 1 項安全性差異（A6），是上游 Hermes 的問題，add-on 可以補強，待決定（見第 5 節）。
- 其餘不同之處屬於 HA Ingress 或 Cloudflare 本身的限制，已寫進 DOCS.md（見第 4 節）。

| 測試 | 數量 |
|---|---|
| 對照檢查項目 | 179 項（功能對照 122 項、實際使用 57 項） |
| 實際對話 | 37 個情境對話，每個都在三條路徑上跑，另有雙分頁、Gateway API 等 |
| 實際排程觸發 | 10 次 |
| WebSocket 長連線觀察 | 三條路徑同時觀察 47 分鐘，驗證時再觀察 45 分鐘 |
| 模型呼叫 | 約 250 次 |
| 正式機上重啟 add-on | 2 次，測試重啟後的復原 |

## 2 三條路徑一致的功能

- **登入與頁面**：登入、登出、錯誤密碼提示、`?next=` 導回；全部 20 個頁面路由與外掛頁（kanban、achievements）；深層連結、上一頁/下一頁。
- **聊天終端機**：`/help` 等指令、改變視窗大小、真實模型回覆、串流逐段出現、Ctrl+C 中斷。
- **工具**：終端機、讀寫檔、網頁搜尋、執行程式、skill、長期記憶。
- **Session**：跨路徑接續同一個 session，訊息 hash 相同。
- **資料寫入**：skills、kanban、cron、設定頁、環境變數、MCP、profiles，在任一路徑寫入，另外兩條路徑都讀得到。
- **檔案**：1、20、95 MB 上傳下載的 SHA-256 相符；上傳 `.html`、`.js` 檔再下載，內容不會被改寫。
- **排程**：一次性和週期排程都準時觸發；暫停、恢復、立即執行、編輯、刪除在三條路徑上同步；對話中請 agent 自己建排程也可以。
- **即時更新與 WebSocket**：5 條 WebSocket 都能連上；閒置 10 分鐘不斷線；斷網 5 秒後自動重連；其他人的新 session 會即時出現。
- **Add-on 重啟**（0.1.3）：三條路徑都約 43 秒自動重連，仍保持登入，聊天不會顯示「session ended」。

## 3 找到並已修正的差異

| # | 問題 | 影響 | 修正版本 | 正式機驗證 |
|---|---|---|---|---|
| 1 | 側邊欄的「匯出 session」請求跑出 ingress 路徑 | 側邊欄無法匯出 | 0.1.1：shim 把漏掉路徑的 `fetch`/XHR 補回 ingress 路徑 | ✅ 三條路徑下載的 byte 相同 |
| 2 | Swagger `/docs` 的「Try it out」打到 HA 根目錄 | 側邊欄無法試打 API | 0.1.1：同上 | ✅ 回 200 |
| 3 | 登入頁 favicon 向 HA 根目錄要圖示 | 分頁沒有圖示、console 有 404 | 0.1.1：注入帶 ingress 路徑的 icon 連結 | ✅ |
| 4 | 在同一台主機上，直連的登入 cookie 會帶進側邊欄 | 側邊欄不用登入就進得去，側邊欄登出也無效 | 0.1.1：用 njs 把側邊欄的 cookie 改名為 `woowing_hermes_*` | ✅ 兩邊各自登入、各自登出 |
| 5 | Webhooks 頁顯示接收器「未啟用」 | 看起來 webhook 沒開 | 0.1.2：開機時把 `platforms.webhook` 寫進 config.yaml | ✅ `/api/webhooks` 回 `enabled: true` |
| 6 | HA Ingress 把所有 WebSocket 關閉碼改成 1000 | 被其他分頁接手的聊天、agent 結束的聊天都顯示「session ended (code 1000)」 | 0.1.3：新增 `woow-wsrelay` 記錄 Hermes 真正的關閉碼，由 shim 還原 | ✅ 4409 和 4410 三條路徑相同 |
| 7 | 從 podman 版沿用的安全政策從來沒有生效，卻寫入了「已套用」的標記 | 設定跟預期不同 | 0.1.3：依使用者決定維持上游預設，移除沒作用的程式碼，並更新文件 | ✅ `approvals.mode=smart`、`cron_mode=deny` |

每一項都先寫出能重現問題的測試（紅燈），修正後轉綠燈，最後在正式機上驗證。

## 4 平台本身的限制（add-on 無法修正，已寫入 DOCS.md）

| 項目 | 說明 |
|---|---|
| 在 HA 頁面按 F5 會回到 Sessions | HA 每次都從面板首頁開 iframe，不記住 iframe 裡的頁面。直連重新整理會停在原頁。可以用 shim 記住最後的頁面來改善（見第 5 節）。 |
| 兩邊要各自登入 | 這是 #4 修正的刻意設計，讓兩邊的 session 分開。 |
| 經 Cloudflare 的限制 | 單一請求 body 最多 100 MB；大約 100 秒沒有輸出會回 524；速度受 WAN 影響，95 MB 上傳約 63 秒，區網約 12–15 秒。 |
| 結尾沒有斜線的 ingress 網址 | HA Core 直接回 404。從側邊欄進入不會遇到。 |
| Cloudflare 注入的 challenge 腳本 | 經 Cloudflare 時會多出 `/cdn-cgi` 請求，不影響功能。 |
| WebSocket 被拒時的表現 | 直連是握手時回 403；Ingress 則先建立連線再關閉。兩邊都收不到資料。 |
| 回應標頭 | HA 會在 ingress 回應加上 X-Frame-Options 等安全標頭，並去掉 `charset`，內容 byte 相同。 |
| 對外 port 綁在所有網卡上 | Supervisor 不能只綁一張網卡。不需要的 port 可在 add-on 的 Network 分頁停用。 |
| Watchdog 和開機自動啟動 | HA 不會自動打開，安裝後要手動打開。 |

## 5 待決定

| 項目 | 說明 | 建議 |
|---|---|---|
| **A6 登入次數限制可繞過**（安全） | Hermes 以 `X-Forwarded-For` 的第一個值判斷來源 IP，所以在直連和經 Cloudflare 時，換一個標頭值就能繼續猜密碼。區網的 HA 會擋掉。 | 修：nginx 改用真實來源 IP，並對 Hermes 的 `_client_ip` 加建置時修補（做法比照現有的 `iss-*.py`）。三條路徑就都擋得住。 |
| F5 回到 Sessions | 見第 4 節。 | 可選：在 shim 用 `sessionStorage` 記住最後的頁面，重新整理後自動回去。 |

## 6 上游 Hermes 本身的問題（三條路徑都一樣）

- 登出只清瀏覽器 cookie，伺服器端的 token 仍有效：access token 12 小時，refresh token 30 天。
- 快速連續按鍵（每鍵間隔小於 25 ms）時，聊天終端機會掉字。一般打字不受影響。
- Webhooks 頁顯示的網址是 `localhost:8644`。
- kanban 刪除卡片後，其他分頁不會即時更新。
- 串流模式的 chat completion 在沒有設定模型時，不會把錯誤訊息回傳給呼叫端。

## 7 Cloudflare 對外設定（尚未建立，需要核准）

正式機的 Cloudflared 是遠端管理模式，公開主機名稱要在 Cloudflare Zero Trust 後台新增，放在 catch-all 規則之前：

| 公開 hostname | Service（origin） | 用途 |
|---|---|---|
| `woowtech-hermes-api.woowtech.io` | `http://homeassistant:8642` | OpenAI 相容 API（Bearer key） |
| `woowtech-hermes-hook.woowtech.io` | `http://homeassistant:8644` | Webhook 接收器（HMAC） |
| API hostname 上只開放 `^/api/mcp/oauth/callback/` | `http://homeassistant:9119` | MCP OAuth 回呼，dashboard 其他部分不公開 |

測試時已從 HA 內部網路確認三個 origin 都連得到。

## 8 測試工具（在 repo 的 `hermes/test/`）

| 檔案 | 用途 |
|---|---|
| `test-config-contract.py` | 檢查 manifest、翻譯、nginx 規則、s6 服務與建置檢查是否一致 |
| `test-ingress-shim.mjs`、`test-ingress-shim-ws.mjs` | shim 的路徑補正與 WebSocket 關閉碼還原 |
| `test-ingress-cookies.mjs` | 側邊欄 cookie 改名 |
| `test-ws-relay.py` | 放在 HA 轉送迴圈後面，檢查 relay 記錄的關閉碼 |
| `run-local-parity.sh` | 在本機以 HA ingress 模擬器 `ha_ingress_emulator.py`（照抄 HA 的轉送邏輯）跑整套測試：21 頁巡檢、cookie 隔離、聊天關閉碼、開機設定 |
| `test-chat-close-codes.js`、`test-restart-recovery.js`、`test-cookie-isolation.js` | 也能直接對真實的 HA 執行 |
