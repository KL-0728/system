# 竹南冷凍倉儲庫存管理系統

目前完成 A0 基礎骨架與 A1 登入、角色權限、基本資料 seed 及唯讀清單。
入庫、出庫、移位、盤點、損耗與報表仍未實作。

## 環境與安裝

Python 3.12（含 pip、venv），Node.js 22.12 以上的 22.x 或 Node.js 24（含 npm）。
SQLite 使用 Python 內建 sqlite3，不需另裝伺服器。
以下 PowerShell 指令皆從專案根目錄執行；npm.cmd 可避免 npm.ps1 執行原則問題。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm.cmd --prefix frontend ci
```

macOS／Linux：Python 路徑改為 .venv/bin/python，npm.cmd 改為 npm；
建立環境時可用 python3 -m venv .venv。不必啟用虛擬環境。

## SQLite 初始化（首次執行一次）

```powershell
.\.venv\Scripts\python.exe -m backend.database
```

產生 data/inventory.db，含 8 張空表。backend/schema.sql 原樣取自 spec.md 第 4.2 節，
所有欄位、外鍵、CHECK 和索引均保留。每次透過 connect_database 建立連線都啟用外鍵，
不共用全域連線，離開 context 時關閉。健康檢查不依賴資料庫，也不會自動建表。

重複初始化會回報 Database already exists 並以非零狀態結束，保留原資料。
不要刪除既有資料庫來套用結構更新；後續需由團隊協調遷移。
初始化後執行 `.\.venv\Scripts\python.exe -m backend.seed`。Seed 只補缺少的示範資料，不重複新增或覆寫既有內容：

- 管理者：`admin`／`admin1234`
- 倉管人員：`worker`／`worker1234`
- A、B 冷凍庫及 A-01、A-02、B-02、B-03、B-04
- 紅蘿蔔、青花菜；刻意不含展示時才建立的甘藍菜

密碼以 PBKDF2-SHA256 加鹽雜湊保存。備份時先停止服務，再複製 data/inventory.db；
還原時同樣先停止服務，保留目前檔案備份後再放回。

## 開發啟動（兩個終端機）

終端機一：

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

終端機二：

```powershell
npm.cmd --prefix frontend run dev
```

開啟 http://localhost:5173，應先看到登入頁，登入後顯示目前角色、品項與儲位。
Vite 將 /api 轉送至本機 8000 埠，手機也使用相同相對路徑，不需設定 CORS。
連線失敗時首頁最多約 5 秒後顯示錯誤；恢復服務後重新整理即可。

健康檢查：http://127.0.0.1:8000/api/health
API 文件：http://127.0.0.1:8000/docs

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

預期 HTTP 200，JSON 為 {"status":"ok"}；只表示後端可回應，不代表資料庫或業務功能已驗收。
停止後端後刷新開發首頁，可確認錯誤訊息；未定義 API 路徑應回傳 404。

## A1 API

| 方法與路徑 | 權限 | 說明 |
| --- | --- | --- |
| `POST /api/auth/login` | 公開 | 輸入 `{"username":"worker","password":"worker1234"}`，設定 HttpOnly Cookie 並回傳使用者 |
| `POST /api/auth/logout` | 公開 | 使目前 session 失效並清除 Cookie |
| `GET /api/auth/me` | 已登入 | 回傳目前使用者與 `ADMIN`／`WORKER` 角色 |
| `GET /api/master-data/products` | 兩角色 | 回傳品項、單位、門檻、目標量與啟用狀態 |
| `GET /api/master-data/locations` | 兩角色 | 回傳儲位、所屬冷凍庫與啟用狀態 |

未登入回 `401`，帳密錯誤回 `401`，角色不符回 `403`。共用後端依賴位於 `backend/auth.py`：`get_current_user`、`require_admin`、`require_worker`、`require_roles(...)`。共用前端呼叫與型別位於 `frontend/src/api`、`frontend/src/types`。Session 保存在執行中的後端記憶體，後端重啟後需重新登入。

## 同一網址展示（建置後只啟動後端）

先停止開發後端，再執行：

```powershell
npm.cmd --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

電腦開啟 http://localhost:8000；手機與電腦連同一網路，
以 http://電腦的區域網路IPv4:8000 開啟（用 ipconfig 查 IPv4）。
FastAPI 啟動時檢查 frontend/dist，存在時提供首頁與資源；
首次建置或重新建置後重新啟動後端。未建置時 / 回 404，/api/health 仍可用。
兩種啟動模式擇一使用，避免 8000 埠衝突。Vite 固定使用 5173，佔用時會報錯。
用 Ctrl+C 停止服務。

需手動確認手機／電腦首頁、窄螢幕排版、正常及失敗狀態。
手機無法連線時，檢查私人網路防火牆的 8000 埠及 Wi-Fi 裝置隔離設定。
本階段沒有庫存資料同步操作可驗收。

## 檔案分工與交接

- frontend/src/pages：頁面；components：共用元件預留。
- frontend/src/api、types：API 呼叫與共用型別。
- backend/main.py：入口、健康檢查、建置後的静態頁面。
- backend/database.py、schema.sql：連線、一次性初始化、固定 SQL。
- backend/models、schemas、routes、services：後續模組預留。
- tests：後續業務測試預留；data：本機資料庫，不提交 Git。

AI 參與：骨架與文件由 AI 協助建立；組員 A 需理解啟動及資料庫初始化，
由 B 對照 spec.md 第 4 節審查。完整業務流程尚未驗收。

## 本次實際檢查結果

檢查環境：Windows、Python 3.12.6、Node.js 24.16.0、npm 11.13.0。

- 套件安裝成功；npm 安裝時 audit 顯示 0 vulnerabilities，pip check 通過。
- npm.cmd --prefix frontend run build：TypeScript 檢查及 Vite 7.3.6 建置成功。
- 實際啟動 Uvicorn：GET /api/health 回 200，內容為 {"status":"ok"}。
- 建置後首頁、JS/CSS 與 /docs 回 200；不存在的 API 回 404。
- 實際啟動 Vite：首頁與 TSX 模組回 200，/api/health 代理回預期 JSON。
- 停止後端後，Vite API 代理回 HTTP 錯誤，沒有誤報成功。
- schema.sql 與 spec.md 的 SQL 區塊逐字比對一致（換行正規化後）。
- 本機 SQLite 建立 8 張表；完整性、外鍵檢查通過，無效外鍵寫入被拒絕。
- 再次初始化回非零狀態，資料庫 SHA-256 不變。
- 資料庫、虛擬環境、node_modules、dist、.env 均被 Git 忽略。

檢查服務已停止；本機保留 .venv、node_modules、dist 及空資料庫，均不提交 Git。
尚未進行瀏覽器視覺驗收或實體手機連線；請依上方啟動步驟，確認窄螢幕、
連線正常與失敗訊息，以及同一網路的手機可開啟首頁。
