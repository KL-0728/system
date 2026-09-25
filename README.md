# 竹南冷凍倉儲庫存管理系統

目前完成 A0 基礎骨架、A1 登入／基本資料、A3 共用庫存服務，以及 A2 品項／儲位管理與導覽。
本分支另完成 C1 出庫表單、API 與出庫紀錄核對。入庫、移位、盤點、損耗與報表仍未實作。

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

## Git 功能分支防呆

新片段先 Fetch，再從遠端 main 建立「不追蹤 main」的功能分支：

```powershell
git fetch origin
git switch --no-track -c feature/b-b1-inbound origin/main
git branch -vv
```

`git branch -vv` 中目前功能分支不可顯示 `[origin/main]`。首次 Push 要明確指定同名功能分支：

```powershell
git push -u origin feature/b-b1-inbound
```

之後才可使用 VS Code「同步變更」。若功能分支誤顯示 `[origin/main]`，先停止 Push，執行 `git branch --unset-upstream` 並通知 A。GitHub 的 `main` 另應啟用 ruleset 或 branch protection，要求透過 Pull Request 合併，作為文件提醒之外的強制防線。

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
- `LOT-20260924-901` 紅蘿蔔在 B-03 共 5 籠、`LOT-20260924-902` 青花菜在 B-04 共 3 籠，以及各自一筆 `RECEIPT`

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

## A2 品項、儲位與導覽

登入後的共用導覽包含首頁、倉管操作，以及僅管理者可見的基本資料頁。倉管操作入口預留給 B／C／D 的入庫、出庫、移位及盤點頁；管理者首頁保留 D3 統計位置，未合併前明確顯示待串接。

| 方法與路徑 | 權限 | 說明 |
| --- | --- | --- |
| `GET /api/master-data/warehouses` | 兩角色 | 讀取 A／B 冷凍庫，供儲位表單選擇 |
| `POST /api/master-data/products` | ADMIN | 新增品項；輸入 `name`、`unit`、`min_qty`、`target_qty`、`is_active` |
| `PUT /api/master-data/products/{id}` | ADMIN | 編輯品項；已有庫存異動時不可更改單位 |
| `POST /api/master-data/locations` | ADMIN | 新增儲位；輸入 `warehouse_id`、`code`、`is_active` |
| `PUT /api/master-data/locations/{id}` | ADMIN | 編輯或停用儲位；仍有正餘量時不可停用 |

名稱或代碼重複、已有異動卻更改單位、未搬空便停用儲位回 `409`；資料不存在回 `404`；欄位格式、負數或目標量低於最低量回 `422`；WORKER 寫入回 `403`。管理頁建立儲位時選冷凍庫並輸入 1–99 的編號，例如選 B、輸入 3，自動送出 `B-03`。本版本不刪除品項或儲位，停用後仍保留清單與歷史關聯。

## A3 共用庫存介面

兩種角色登入後都可讀取以下最小操作選單；這不是 B2 的完整庫存搜尋或異動歷史 API。

| 方法與路徑 | 查詢參數 | 主要回傳欄位 |
| --- | --- | --- |
| `GET /api/stock-options/lots` | 可選 `product_id` | `lot_id`、批次碼、品項、單位、入庫日、跨位置合計 `total_qty` |
| `GET /api/stock-options/balances` | 可選 `lot_id`；`positive_only` 預設 `true` | 批次、品項、位置、`qty`、`has_pending` |
| `GET /api/stock-options/locations` | 無 | 所有啟用目標儲位及所屬冷凍庫 |

例如登入後讀取所有正餘量：`GET /api/stock-options/balances?positive_only=true`。未登入回 `401`；無效的正整數查詢參數回 `422`；合法但沒有資料回空陣列 `[]`。前端共用契約在 `frontend/src/api/stockOptions.ts` 與 `frontend/src/types/stock.ts`。

`backend/services/stock_service.py` 提供：

- `stock_transaction(path=None)`：唯一負責 `BEGIN IMMEDIATE`、成功 `COMMIT`、例外 `ROLLBACK`。
- `get_balance(...)`／`require_balance(..., at_least=...)`：讀取餘量及驗證足量。
- `ensure_no_pending(...)`：阻止同一批次／位置在待審期間移出或移入。
- `require_active_location(...)`：確認目標儲位存在且啟用。
- `change_balance(..., delta, create_if_missing=False)`：原子更新餘量，拒絕負數並保留歸零列。
- `record_movement(...)`：新增不可修改的庫存異動並回傳 ID。

B／C／D 的 service 必須由最外層使用一次 `with stock_transaction() as connection:`，並把同一個 connection 傳給其他函式；這些輔助函式不自行開交易或 commit，route 也不得直接改餘量。Seed 已自行持有交易，所以只呼叫輔助函式，不可再包 `stock_transaction()`。

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
目前可用兩台裝置登入後讀取相同的批次與餘量，倉管也可操作出庫；入庫、移位及盤點將由後續片段提供。

## C1 出庫與操作驗收

以 `worker`／`worker1234` 登入，點「倉管操作」即可看到出庫表單。使用 A3 的庫存選單；管理者不能提交出庫，後端會驗證 WORKER 權限。

| 方法與路徑 | 權限 | 輸入／結果 |
| --- | --- | --- |
| `POST /api/outbound` | WORKER | `lot_id, location_id, qty, note`；201 回傳 `lot_id, location_id, qty`（新餘量）、`movement_id` |
| `GET /api/outbound` | 兩角色 | 可選 `lot_id, location_id` 篩選；回傳最新 100 筆出庫，包含異動 ID、批次、品項、儲位、出庫量、單位、操作者、備註及 UTC `created_at` |

例如 POST `{"lot_id":1,"location_id":4,"qty":2,"note":"課堂出庫"}`，成功回傳 `{"lot_id":1,"location_id":4,"qty":3,"movement_id":3}`。ID 只是範例，請以 A3 選單實際回傳的 ID 為準。
未登入 401、非 WORKER 寫入 403、超量／待審／不存在的批次儲位組合 409、非正整數／非法 ID／備註超過 500 字／額外欄位 422；被拒時不扣量也不新增異動。操作者來自登入狀態。

`outbound_service.py` 在一次 A3 `stock_transaction()` 中檢查待審、餘量、扣量及寫入 OUTBOUND；失敗整筆回滾，歸零列保留。未改共用選單、交易服務或建表 SQL。C1 查詢僅用於核對出庫結果，B2 仍負責完整庫存搜尋與各類異動歷史。

1. 首次依上方安裝環境、初始化及 seed；已有資料庫只需 seed 補缺，不要重新初始化。seed 不會將已出庫的數量恢復為 5。
2. 啟動後端與前端，開啟 http://localhost:5173，倉管登入並點「倉管操作」。
3. 選紅蘿蔔 `LOT-20260924-901`／B-03，確認原數 5 籠，輸入 2，按「確認出庫」。應顯示餘量 3 籠、異動編號，並新增一筆出庫紀錄；重新整理、再次進入倉管操作仍是 3 籠。
4. 輸入 99、0、負數或小數，應被阻擋且紀錄不增加。若資料已操作過，依實際原數驗收扣量，不刪庫重演。
5. 瀏覽器開發工具將網路調慢後，連點確認出庫；等待時表單停用，一次提交只有一筆 POST／OUTBOUND。這是同頁防連點，沒有伺服器冪等鍵。
6. 模擬送出後斷線／逾時：畫面顯示「結果未確認」，不自動重送。恢復後按「查詢紀錄／更新餘量」，核對時間、位置、操作者、數量及備註；確認後才按「我已核對紀錄，開始新的操作」。查不到紀錄不代表原請求一定沒成功。
7. D1 尚未合併，待審凍結以獨立測試資料驗證。合併 D1 後再由畫面建立同批次／儲位待審申請，回出庫頁更新，應顯示待審且不能提交。
8. 手機驗收依「同一網址展示」啟動，手機登入操作出庫後，電腦按更新應看到同一餘量及紀錄。時間顯示為臺灣時間。

後端檢查：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。測試使用暫存 SQLite，不改本機展示庫存。

可重跑的 Chrome 畫面檢查（須先完成前端 build，且已安裝 Chrome）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests/requirements-browser.txt
.\.venv\Scripts\python.exe -m tests.browser_c1
```

2026-09-25 C1 實測：後端 20 項測試通過（包含既有 A1／A2／A3），pip check 通過，TypeScript／Vite build 通過。Chrome 自動操作通過真實登入、非法數量、同頁連續提交只發一筆 POST、刷新保留餘量、已提交但回應中斷後核對紀錄、待審停用按鈕，以及 320／390／1280px 無橫向溢出，沒有 JavaScript 執行錯誤。實體手機連線仍需本人依上方步驟驗收。

這台電腦已建立 `.venv`、安裝前端依賴並首次初始化／seed 展示資料庫，未使用展示資料庫跑出庫測試。Python 為 3.12.10；Node.js 系統安裝未完成，檢查使用官方 Node.js 24.19.0 免安裝版，放在 Git 忽略的 `data/c1-tools`。若新終端機仍找不到 npm，可先在專案根目錄執行以下指令，再使用本文的 npm 指令；其他組員若已有 Node.js 不需這一步。

```powershell
$env:Path = (Resolve-Path 'data/c1-tools/node-v24.19.0-win-x64').Path + ';' + $env:Path
```

C1 主要檔案為 `frontend/src/pages/OutboundPage.tsx`、`frontend/src/api/outbound.ts`、`backend/routes/outbound.py`、`backend/services/outbound_service.py`、`backend/schemas/outbound.py` 及 `tests/test_c1.py`。AI 協助實作與測試；C 應理解「表單 → 登入權限 → 同一交易檢查／扣量／異動 → 回傳資料庫結果」及連線不確定時的核對流程，操作驗收後再 Commit／Push 並回報 A，由 A 建立 PR。

## C2 移位與操作驗收

以 `worker`／`worker1234` 登入，進入「倉管操作」的「移位」區塊。先選來源批次及儲位，再選不同的啟用目標儲位並輸入正整數數量。畫面顯示來源、目標同批餘量和同批各處合計；提交成功後顯示兩處新餘量與異動編號，並更新出庫可用餘量。管理者可讀移位紀錄，但不能提交移位。

`POST /api/outbound/transfers` 僅限 WORKER，輸入 `lot_id, from_location_id, to_location_id, qty`，成功回傳 `from_qty, to_qty, movement_id` 及位置、批次 ID。`GET /api/outbound/transfers` 兩種角色可讀，可用 `lot_id` 篩選，回傳最近 100 筆移位及操作者與 UTC 時間；這是 C2 核對用紀錄，完整異動查詢仍由 B2 負責。未登入回 401，非 WORKER 寫入回 403，數量／ID 格式不符回 422，超量、同位置、停用目標、來源或既有目標同批待審回 409，失敗不更動餘量或紀錄。移位寫入使用同一次 `stock_transaction()`，來源歸零列保留。

驗收時可選種子批次 `LOT-20260924-901` 的 B-03 作來源（初始為 5 籠），B-04 作目標，移 2 籠後應為 B-03 3 籠、B-04 2 籠，合計仍是 5 籠，最近移位紀錄新增一筆。重新整理後再核對。若示範庫存已被操作，請依畫面上的實際原數核對，不要重置資料庫。再試超量、同一儲位、0 或小數，應拒絕且紀錄不增加。等待回應時表單停用；若連線中斷造成結果未確認，先按「查詢移位紀錄／更新餘量」核對時間、批次、兩處位置、數量和操作者，確認後才開始新的操作。待審來源或既有目標的凍結須在 D1 合併後從畫面建立申請驗收，目前由 `tests/test_c2.py` 驗證。

後端檢查：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。本片段的測試使用暫存 SQLite，不修改本機展示資料庫。實體手機仍須依上方「同一網址展示」方式連線驗收。

## B1 單筆入庫與操作驗收

以 `worker`／`worker1234` 登入，進入「倉管操作」最上方的「入庫」區塊。選啟用品項、一個啟用儲位，輸入正整數數量與入庫日期（預設今天，臺灣時間），備註選填。批次碼由後端產生，前端不組碼；同一批要放多處時，入庫後再用 C2 移位分拆。管理者可讀入庫紀錄，但不能提交入庫。

| 方法與路徑 | 權限 | 輸入／結果 |
| --- | --- | --- |
| `POST /api/inventory/inbound` | WORKER | `product_id, location_id, qty, received_date, note`；201 回傳 `lot_id, lot_code, product_id, location_id, received_date, qty`（該儲位此批新餘量）、`movement_id` |
| `GET /api/inventory/inbound` | 兩角色 | 可選 `lot_id`；回傳最新 100 筆 RECEIPT，含批次、品項、單位、入庫日、儲位、數量、操作者、備註及 UTC `created_at` |

例如 POST `{"product_id":1,"location_id":1,"qty":10,"received_date":"2026-09-25","note":"課堂入庫"}`，成功回傳 `{"lot_id":3,"lot_code":"LOT-20260925-001",...,"qty":10,"movement_id":3}`。ID 只是範例，請以品項／儲位清單實際回傳的 ID 為準。

批次碼為 `LOT-YYYYMMDD-NNN`，日期取入庫日，序號取同日已用最大號加 1（例如 seed 已有 `LOT-20260924-901`、`902`，同日下一批為 `903`）；在 `BEGIN IMMEDIATE` 交易內計算，避免同時入庫撞號。未登入 401、非 WORKER 寫入 403；品項或儲位不存在／已停用 409；數量非正整數、日期格式錯誤、不存在的日期（如 2026-02-30）或晚於今天（臺灣時間）、備註超過 500 字、額外欄位（如 `actor_id`、`lot_code`）422。被拒時不建立批次、餘量或異動。操作者來自登入狀態。

`inbound_service.py` 在一次 A3 `stock_transaction()` 內依序：確認品項啟用 → `require_active_location` → 產生批次碼並新增 `lots` → `change_balance(..., create_if_missing=True)` → `record_movement(kind="RECEIPT")`；任何一步失敗整筆回滾。未改共用選單、交易服務或建表 SQL。入庫紀錄查詢只用來核對入庫結果；完整庫存搜尋與各類異動歷史屬於 B2。

1. 依上方安裝、初始化及 seed（已有資料庫只需 seed 補缺，不要重新初始化）。啟動後端與前端，開啟 http://localhost:5173，倉管登入後點「倉管操作」。
2. 正常操作：選「紅蘿蔔（籠）」、A-01、數量 10、日期保持今天，按「確認入庫」。應顯示批次號（如 `LOT-20260925-001`）、A-01 此批餘量 10 籠與異動編號；最近入庫紀錄新增一筆，下方出庫、移位選單也出現這批 A-01 10 籠。重新整理後再進倉管操作，紀錄與餘量仍在。
3. 錯誤操作：數量輸入 0、負數或小數，瀏覽器或畫面會阻擋、不送出，紀錄不增加。停用儲位不會出現在選單中；後端另有自動測試確認直接呼叫 API 送停用儲位／品項會回 409 且不寫入。
4. 連點「確認入庫」只會送出一筆；等待回應時表單停用。若顯示「結果未確認」，先按「查詢入庫紀錄」核對品項、儲位、數量、時間和操作者，確認後才按「我已核對紀錄，開始新的操作」，避免重複建立批次。

後端檢查：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。`tests/test_b1.py` 使用暫存 SQLite，不修改本機展示資料庫。

B1 主要檔案為 `frontend/src/pages/InboundPage.tsx`、`frontend/src/api/inventory.ts`、`backend/routes/inventory.py`、`backend/services/inbound_service.py`、`backend/schemas/inbound.py` 及 `tests/test_b1.py`；另在 `backend/main.py` 註冊路由、`OperationsPage.tsx` 加入入庫區塊、`styles.css` 加入入庫版面樣式。AI 協助實作與測試；B 應理解「表單 → 登入權限 → 同一交易建批次／餘量／RECEIPT → 回傳資料庫結果」。

2026-09-25 B1 實測（雲端 Linux、Python 3.11、Node 22）：後端 49 項測試全數通過（含既有 A1／A3／C1／C2），TypeScript／Vite build 通過；Chromium 自動操作確認倉管入庫 10 籠成功、連點只送一筆 POST、重新整理後出庫選單可見新批次、0 與小數不送出，320／390／1280px 無橫向溢出、無 JavaScript 錯誤。Windows 本機與實體手機仍需本人依上方步驟驗收。

## 檔案分工與交接

- frontend/src/pages：頁面；components：共用元件預留。
- frontend/src/api、types：API 呼叫與共用型別。
- backend/main.py：入口、健康檢查、建置後的静態頁面。
- backend/database.py、schema.sql：連線、一次性初始化、固定 SQL。
- backend/schemas、routes：登入、基本資料與最小庫存選單契約。
- backend/services/stock_service.py：庫存交易、餘量、待審與異動共用介面。
- tests：登入、seed 及共用庫存規則測試；data：本機資料庫，不提交 Git。

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
