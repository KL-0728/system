# 竹南冷凍倉儲庫存管理系統

已整合 A0–A3、B1–B2、C1–C2、D1–D3；A4 負責完整展示流程與交付彩排。各模組的分段說明保留在下方，完整操作請看「A4 整合展示」。

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

產生 data/inventory.db，含必做版 8 張表及加做的 `shortage_demands` 表。backend/schema.sql 與 spec.md 第 4.2 節一致，
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

未登入回 `401`，帳密錯誤回 `401`，角色不符回 `403`。共用後端依賴位於 `backend/auth.py`：`get_current_user`、`require_admin`、`require_worker`、`require_roles(...)`。共用前端呼叫與型別位於 `frontend/src/api`、`frontend/src/types`。Session 保存在執行中的後端記憶體，有效 8 小時；重新登入會作廢同一瀏覽器舊 token，後端重啟後也需重新登入。前端一般請求 15 秒逾時，收到受保護 API 的 `401` 會返回登入畫面；登出連線失敗時會提示重試，不能當成已登出。

## A2 品項、儲位與導覽

登入後的共用導覽包含首頁、倉管操作，以及僅管理者可見的基本資料、審核申請與決策報表頁。倉管操作入口對倉管包含入庫、庫存查詢、出庫、移位、盤點／損耗申請、缺貨需求及儲位簡圖；管理者在此頁可查庫存與簡圖，不能提交倉管操作。管理者首頁從 D3 報表 API 取得即時統計。

登入頁及登入後導覽都有太陽／月亮外觀按鈕：尚未手動選擇時預設跟隨系統，按圖示即切換明暗。手動選擇存在此瀏覽器的 localStorage，重新整理或再次登入仍保留；此版本沒有「自動」復原按鈕，若需重新跟隨系統，可清除 localStorage 的 `zhunan-theme` 設定。不同裝置各自設定，不影響庫存資料。介面採霧藍／深藍配色；手機導覽按鈕會換行排列，不需水平捲動；輸入欄位在窄螢幕改為單欄，紀錄與報表卡片依寬度換欄，控制項至少 44px 高，鍵盤操作有焦點提示。

介面驗收可用電腦開發工具切換 320／390／768／1280px，分別以兩種角色巡看首頁、倉管操作及管理者的基本資料／審核／報表，確認沒有左右捲動、文字和按鈕完整可見，尤其核對入庫日期沒有超出卡片邊框。新瀏覽器在點擊外觀圖示前應跟隨裝置外觀；按太陽／月亮圖示切換後，重整及重新登入仍應保留手動選擇。自動版面檢查使用暫存資料庫，不改展示資料：先執行前端 build，安裝 `tests/requirements-browser.txt`，在已安裝 Chrome 的電腦上執行 `.\.venv\Scripts\python.exe -m tests.browser_responsive`；實體手機仍需本人操作確認。

iPhone Safari 的原生日期欄位曾出現比其他輸入框更寬的情況；入庫日期現在由外層容器負責邊框與內距，日期輸入本身不再設定內距，以免 iOS WebKit 將 100% 寬度算得過大。Chrome 的手機寬度模擬不能取代實機 Safari 驗收。

| 方法與路徑 | 權限 | 說明 |
| --- | --- | --- |
| `GET /api/master-data/warehouses` | 兩角色 | 讀取 A／B 冷凍庫，供儲位表單選擇 |
| `POST /api/master-data/products` | ADMIN | 新增品項；輸入 `name`、`unit`、`min_qty`、`target_qty`、`is_active` |
| `PUT /api/master-data/products/{id}` | ADMIN | 編輯品項；已有庫存異動或缺貨需求紀錄時不可更改單位 |
| `POST /api/master-data/locations` | ADMIN | 新增儲位；輸入 `warehouse_id`、`code`、`is_active` |
| `PUT /api/master-data/locations/{id}` | ADMIN | 編輯或停用儲位；仍有正餘量或待審申請時不可停用 |

名稱或代碼重複、已有異動或缺貨紀錄卻更改單位、未搬空或仍有待審申請便停用儲位回 `409`；資料不存在回 `404`；欄位格式、負數、超出 SQLite 整數範圍或目標量低於最低量回 `422`；WORKER 寫入回 `403`。儲位代碼須與所選冷凍庫一致，編號 01–99；管理頁選冷凍庫並輸入 1–99，例如選 B、輸入 3，自動送出 `B-03`。本版本不刪除品項或儲位，停用後仍保留清單與歷史關聯。

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
目前可用兩台裝置登入後讀取同一資料庫；倉管可操作入庫、出庫、移位及盤點／損耗送件，管理者可審核申請與查看決策報表，兩角色可用 B2 查詢庫存與異動。

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
7. 在 D1 頁由畫面建立同批次／儲位的待審申請，回出庫頁更新，應顯示待審且不能提交；申請前先確認該批次／儲位的實際餘量。
8. 手機驗收依「同一網址展示」啟動，手機登入操作出庫後，電腦按更新應看到同一餘量及紀錄。時間顯示為臺灣時間。

後端檢查：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。測試使用暫存 SQLite，不改本機展示庫存。

可重跑的 Chrome 畫面檢查（須先完成前端 build，且已安裝 Chrome）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r tests/requirements-browser.txt
.\.venv\Scripts\python.exe -m tests.browser_c1
```

2026-09-25 C1 實測：後端 20 項測試通過（包含既有 A1／A2／A3），pip check 通過，TypeScript／Vite build 通過。Chrome 自動操作通過真實登入、非法數量、同頁連續提交只發一筆 POST、刷新保留餘量、已提交但回應中斷後核對紀錄、待審停用按鈕，以及 320／390／1280px 無橫向溢出，沒有 JavaScript 執行錯誤。實體手機連線仍需本人依上方步驟驗收。

2026-09-26 這台電腦已建立 `.venv`、安裝前端依賴並首次初始化／seed 展示資料庫。Python 為 3.12.10；Node.js 24.21.0 免安裝版放在 Git 忽略的 `data/node-v24.21.0-win-x64`。若新終端機仍找不到 npm，可先在專案根目錄執行以下指令，再使用本文的 npm 指令；其他組員若已有 Node.js 不需這一步。

```powershell
$env:Path = (Resolve-Path 'data/node-v24.21.0-win-x64').Path + ';' + $env:Path
```

C1 主要檔案為 `frontend/src/pages/OutboundPage.tsx`、`frontend/src/api/outbound.ts`、`backend/routes/outbound.py`、`backend/services/outbound_service.py`、`backend/schemas/outbound.py` 及 `tests/test_c1.py`。AI 協助實作與測試；C 應理解「表單 → 登入權限 → 同一交易檢查／扣量／異動 → 回傳資料庫結果」及連線不確定時的核對流程，操作驗收後再 Commit／Push 並回報 A，由 A 建立 PR。

## C2 移位與操作驗收

以 `worker`／`worker1234` 登入，進入「倉管操作」的「移位」區塊。先選來源批次及儲位，再選不同的啟用目標儲位並輸入正整數數量。畫面顯示來源、目標同批餘量和同批各處合計；提交成功後顯示兩處新餘量與異動編號，並更新出庫可用餘量。管理者可讀移位紀錄，但不能提交移位。

`POST /api/outbound/transfers` 僅限 WORKER，輸入 `lot_id, from_location_id, to_location_id, qty`，成功回傳 `from_qty, to_qty, movement_id` 及位置、批次 ID。`GET /api/outbound/transfers` 兩種角色可讀，可用 `lot_id` 篩選，回傳最近 100 筆移位及操作者與 UTC 時間；這是 C2 核對用紀錄，完整異動查詢仍由 B2 負責。未登入回 401，非 WORKER 寫入回 403，數量／ID 格式不符回 422，超量、同位置、停用目標、來源或既有目標同批待審回 409，失敗不更動餘量或紀錄。移位寫入使用同一次 `stock_transaction()`，來源歸零列保留。

驗收時可選種子批次 `LOT-20260924-901` 的 B-03 作來源（初始為 5 籠），B-04 作目標，移 2 籠後應為 B-03 3 籠、B-04 2 籠，合計仍是 5 籠，最近移位紀錄新增一筆。重新整理後再核對。若示範庫存已被操作，請依畫面上的實際原數核對，不要重置資料庫。再試超量、同一儲位、0 或小數，應拒絕且紀錄不增加。等待回應時表單停用；若連線中斷造成結果未確認，先按「查詢移位紀錄／更新餘量」核對時間、批次、兩處位置、數量和操作者，確認後才開始新的操作。可先在 D1 頁建立待審申請，再驗證來源或既有目標同批待審時不能移位。

後端檢查：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。本片段的測試使用暫存 SQLite，不修改本機展示資料庫。實體手機仍須依上方「同一網址展示」方式連線驗收。

## D1 盤點／損耗申請與操作驗收

以 `worker`／`worker1234` 登入，點「倉管操作」並找到「盤點／損耗申請」。選批次與儲位後，盤點填非負整數現場實數（可填 0），損耗填不超過目前餘量的正整數報廢量，兩種申請都要填原因。送件只建立 `PENDING` 申請並保存送件當下的 `original_qty`，不改庫存餘量，也不寫庫存異動；管理者後續使用 D2 審核頁處理。

| 方法與路徑 | 權限 | 輸入與結果 |
| --- | --- | --- |
| `POST /api/adjustments` | WORKER | `lot_id, location_id, kind`（`COUNT`／`SCRAP`）、必填 `reason`；盤點填 `observed_qty`，報廢填 `damaged_qty`。成功 201，回傳申請 ID、批次／位置、原數、填報數、原因、`PENDING` 狀態與 UTC 時間。 |
| `GET /api/adjustments/mine` | WORKER | 只回傳登入者最近 100 筆申請，含當前狀態、審核人／時間與審核備註或駁回原因；刷新後仍可查。 |

未登入回 401，非倉管回 403，欄位格式、缺原因、零／負報廢量或錯填兩種數量回 422；不存在或停用的儲位、不存在的批次／儲位餘量、超量報廢及同批次／儲位已有待審申請回 409。`requested_by` 只取自登入狀態，前端提交不能指定。服務在一次 `stock_transaction()` 中取得原數並寫入申請，沿用資料庫的唯一待審索引；沒有修改 `backend/schema.sql` 或 A3 選單契約。待審凍結只作用於同一批次＋儲位。等待回應時表單停用；若結果未確認，先查「我的申請」並核對後再決定是否重新操作。

畫面驗收：

1. 先在「庫存查詢」確認紅蘿蔔 `LOT-20260924-901`／B-03 的目前餘量；seed 初始為 5 籠，但已操作過時以畫面實際數量為準。選「盤點」、填實數 `0` 與原因後送出。畫面應顯示申請編號與「待審」，原數等於送件前餘量；刷新後「我的最近申請」仍有此筆，庫存餘量不變。
2. 同批次／B-03 再送一筆應被拒絕；出庫與移位頁更新後顯示待審凍結，不能從該批次／位置扣量或移入。同位置的其他批次不受影響。
3. 改選青花菜 `LOT-20260924-902`／B-04，選「損耗」，填報廢量 `1` 和原因送出；「我的最近申請」應顯示原數、報廢量與待審，青花菜餘量不變。再試超過該處餘量、空原因、報廢量 `0` 或小數，應拒絕且不新增申請。
4. 以管理者登入時沒有送件表單；手機使用同一網址登入倉管，確認選單、輸入與申請紀錄在窄螢幕可操作。

D1 測試使用暫存 SQLite，不改本機展示資料庫：`.\.venv\Scripts\python.exe -m pytest -q tests/test_d1.py`；完整回歸：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。

## D2 管理者審核與操作驗收

管理者登入後點上方「審核申請」，或直接開啟 `http://localhost:5173/#reviews`。頁面分列所有待審申請與最近 100 筆已審核申請；已核准／駁回的項目會從待審清單移到已審核清單，重新整理也能找回，不會刪除。點「查看詳情與審核」會在該筆紀錄內展開，可直接核對送件人、品項、批次、儲位、原數、目前餘量、盤點實數或報廢量、預計差額、原因與時間；再點一次可收起，查看下一筆不用往頁面上方找詳情。倉管開啟該網址會看到「權限不足」，且後端管理 API 回 403；倉管可在「我的最近申請」看到自己申請的審核結果及駁回原因。若前端已更新，但審核頁顯示 `request_id` 不能解析為整數，代表仍在執行未註冊 `/api/adjustments/reviewed` 的舊後端；先停止並重新啟動後端，再刷新網頁，不需重建或清除資料庫。

| 方法與路徑 | 權限 | 結果／規則 |
| --- | --- | --- |
| `GET /api/adjustments/pending` | ADMIN | 所有待審申請與詳情，依申請 ID 排序。 |
| `GET /api/adjustments/reviewed` | ADMIN | 最近 100 筆已核准／駁回申請與詳情，最新審核先列。 |
| `GET /api/adjustments/{id}` | ADMIN | 單筆詳情，包含審核後狀態、審核人與異動編號；不存在回 404。 |
| `POST /api/adjustments/{id}/review` | ADMIN | 輸入 `action: "APPROVE"` 或 `"REJECT"` 與 `review_note`；駁回原因必填，核准備註選填。回傳狀態、調整量、新餘量、異動編號、審核人與時間。 |

審核者由登入狀態取得，不可審核自己提交的申請或重複審核。核准時在一次 `stock_transaction()` 內重查 `PENDING` 與目前餘量等於申請原數；盤點差額正／負時分別更新餘量並寫 `COUNT_GAIN`／`COUNT_LOSS`，報廢寫 `SCRAP`，異動連結申請。盤點差額 0 只標記核准，不新增零數量異動。駁回必填原因，餘量不變、沒有異動；結案後解除該批次＋儲位的待審凍結。欄位錯誤回 422，狀態、自己審自己或原數衝突回 409；審核失敗整筆回滾。提交期間兩個審核按鈕停用；網路結果不明時先按「更新申請與詳情」核對，不自動重送。

畫面驗收：

1. 倉管在 D1 對紅蘿蔔 `LOT-20260924-901`／B-03 送盤點實數 `0` 與原因；先確認送件後原餘量不變、出庫與移位受凍結。以管理者登入審核頁，應看到原數（seed 初始 5 籠，若已操作過以送件時實數為準）、實數 0 與負差額。
2. 點「查看詳情與審核」，再按「核准申請」。應顯示新餘量 0、異動編號；該筆不再列於待審清單。到「倉管操作 → 庫存查詢」刷新，確認原入庫紀錄仍在，新增一筆 `COUNT_LOSS`；倉管的「我的最近申請」刷新後顯示已核准。
3. 倉管對青花菜 `LOT-20260924-902`／B-04 送報廢量 `1` 與原因，管理者核准後，餘量比申請原數少 1，歷史有 `SCRAP`。另外可對其他有餘量批次送盤點實數等於原數，核准後沒有新的庫存異動。
4. 另送一筆申請，在管理者頁先試空白駁回原因，應被拒絕；填原因駁回後餘量不變且不新增異動。重新整理後，管理者在「最近已審核申請」仍可查看這筆與駁回原因，倉管在「我的最近申請」也應看到同一原因，並可在同批次／儲位重新送件。手機用同一網址核對卡片、詳情與按鈕可操作。自行審核、倉管呼叫審核 API 及重複核准由 `tests/test_d2.py` 驗證。

D2 測試使用暫存 SQLite，不改本機展示資料庫：`.\.venv\Scripts\python.exe -m pytest -q tests/test_d2.py`；完整回歸：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。

## D3 決策報表與管理者首頁統計

管理者登入後，首頁顯示目前有庫存品項數、低於最低量品項數、待審申請數；按「更新統計」重新查詢資料庫。點上方「決策報表」或開啟 `http://localhost:5173/#reports` 可看完整報表；按「更新報表」取得最新數字。倉管開啟該網址顯示權限不足，直接呼叫報表 API 回 403。

`GET /api/reports` 僅供 ADMIN 讀取，回傳 `as_of_utc`、`summary`、`products`、`aged_lots`、`adjustments`：

- `summary`：啟用品項數、有正餘量品項數、低庫存品項數、待審申請數；不合計不同品項的數量。
- `products`：所有啟用品項各自的單位、目前總量、最低量、目標量、是否低庫存、距離目標還差多少（API 欄位 `replenishment_gap`）、近 30 日出庫、歷來已核准的盤盈／盤虧／報廢量。沒有批次的啟用品項也列 0；低庫存是 `目前總量 < 最低量`，目標差額是 `max(目標量 − 目前總量, 0)`，不是自動採購量。
- `aged_lots`：正餘量批次的入庫日期、各處合計與依臺灣日期計算的庫齡，舊批次先列；已歸零批次保留在庫存歷史，不列入待處理庫齡。
- `adjustments`：已核准的 `COUNT_GAIN`、`COUNT_LOSS`、`SCRAP` 明細，各附申請編號、品項、批次、位置、原因、操作者與臺灣時間。盤盈、盤虧和報廢分列，不把待審或駁回申請計入異動。

後端使用同一個 SQLite 讀取快照和伺服器 UTC 截點計算近 30 日 `OUTBOUND`，不混入移位或盤差；畫面標明最低量與目標量是人工門檻，沒有價格或自動採購預測。報表只讀取現有表，不修改 `backend/schema.sql` 或 A3 選單。

畫面驗收：

1. 管理者登入首頁並點「更新統計」，核對有庫存品項、低庫存品項及待審申請數；再進「決策報表」，確認每個啟用品項分別顯示自身單位。可在「基本資料」新增一個最低量 2、目標量 5、單位「箱」的新啟用品項，報表更新後應列目前 0 箱、低庫存、距離目標還差 5 箱，首頁低庫存品項數增加 1。
2. 倉管對某批次出庫 1 後，管理者按「更新報表」，該品項目前量減 1、近 30 日出庫增加 1；不同單位的數量仍各自列示。庫齡卡片依批次入庫日和正餘量顯示。
3. 若 D1 已送件但未審核，首頁待審數增加，盤差／報廢仍不增加；D2 核准盤點或報廢後再更新，待審數減少，盤虧或報廢欄各自增加。駁回不增加異動。可對照「庫存查詢」的同批次歷史與目前餘量；用手機同網址讀取並核對卡片排版。

D3 測試使用暫存 SQLite，不改本機展示資料庫：`.\.venv\Scripts\python.exe -m pytest -q tests/test_d3.py`；完整回歸：`.\.venv\Scripts\python.exe -m pytest -q`；前端檢查：`npm.cmd --prefix frontend run build`。跨模組展示請依下方 A4 步驟實測。

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

## B2 庫存查詢與異動歷史

以管理者或倉管帳號登入，點「倉管操作」即可在頁面頂端使用「庫存查詢」。可選品項、輸入完整或部分批次碼、選儲位；三個條件可同時使用。查詢結果按入庫日與批次排序，逐批顯示各位置餘量、**全批合計**、入庫日、臺灣時間庫齡及入庫操作者。點「查看異動歷史」可看到該批全部 RECEIPT、OUTBOUND、TRANSFER、COUNT_GAIN、COUNT_LOSS、SCRAP 異動的數量、來源／目標位置、操作者、備註及臺灣時間。已停用品項和儲位仍可查歷史，歸零餘量列也會顯示。

| 方法與路徑 | 查詢參數 | 結果 |
| --- | --- | --- |
| GET /api/inventory/stock | 可選 product_id、lot_code（部分文字）、location_id | 每列 lot_id、lot_code、product_id、product_name、unit、received_date、age_days、received_by、location_id、location_code、warehouse_code、warehouse_name、qty、total_qty |
| GET /api/inventory/movements | 必填 lot_id | 該批全部異動，含 movement_id、kind、來源／目標儲位代碼、qty、actor_name、note、adjustment_request_id、UTC created_at |

兩個 API 都要求登入，未登入回 401；ID 非正整數、批次碼超過 100 字回 422。無符合資料時回空陣列。儲位篩選只限制顯示的位置列，total_qty 始終包含該批所有位置，方便核對移位前後總量。B2 沒有改動 A3 的 /api/stock-options 選單契約，也不改資料庫結構或既有資料。

畫面驗收：

1. 啟動前後端，用 worker 登入，點「倉管操作」；庫存查詢應顯示 seed 的紅蘿蔔 B-03 5 籠、青花菜 B-04 3 籠（若已操作過，以實際餘量為準）。用 admin 登入也能查。
2. 篩選「紅蘿蔔」、批次碼 `901`、儲位 B-03，應只顯示符合的批次與位置；輸入不存在的批次碼應顯示「沒有符合條件的庫存」。按「清除條件」恢復全部。
3. 用移位頁將同一批紅蘿蔔從 B-03 移 2 籠到 A-01，再按「查詢／更新」；應看到 B-03 3、A-01 2、全批合計 5。改篩選 A-01 時只顯示 A-01 的位置列，但全批合計仍為 5；展開歷史可看見 RECEIPT 與 TRANSFER、來源／目標及操作者。測試前先核對實際起始餘量，不要重設資料庫。
4. 在手機用同一 Wi-Fi 開啟前端網址，核對篩選、結果卡片與展開歷史可操作；電腦刷新後應看到同一筆資料。D 的盤點／報廢合併後，再核對 COUNT_GAIN、COUNT_LOSS、SCRAP 也能出現在歷史。

後端測試：`.\.venv\Scripts\python.exe -m pytest -q`；前端編譯：`npm.cmd --prefix frontend run build`。B2 測試使用暫存 SQLite，不修改 data/inventory.db。

## A4 整合展示與交付彩排

先依「環境與安裝」及「SQLite 初始化」準備展示電腦。已有 `data/inventory.db` 時**不要再次初始化或把 seed 當作重置**；seed 只補缺，不還原已操作的餘量。所有下列動作都在同一台後端與同一個資料庫進行。先執行上方「同一網址展示」的建置與啟動指令，電腦開 `http://localhost:8000`，手機開 `http://<電腦區域網路 IPv4>:8000`。兩台裝置各自登入；手機要能連到這台電腦的 8000 埠。管理者審核頁為 `http://<主機>:8000/#reviews`，報表頁為 `http://<主機>:8000/#reports`。倉管操作頁對倉管提供七個快速跳轉（庫存、簡圖、入庫、出庫、移位、盤點、缺貨需求）；管理者在此頁只有庫存與簡圖。管理者的基本資料、審核與報表頁依區塊提供快速跳轉；這些長頁面往下捲動後，右下角都會出現懸浮的「↑ 頂部」按鈕。快速跳轉、儲位明細、回頂部與倉管操作成功提示會以短暫緩動捲動，系統設定「減少動態效果」時不播放動畫。待審中的批次／儲位在操作選單中呈灰色且不可選，仍保留在查詢與歷史中。為避免 iPhone Safari 的原生下拉選單把頁面撐寬，選單使用精簡名稱與 ID；選取後會在表單內顯示完整名稱，操作紀錄也維持完整資訊。

首次完整彩排須使用只有 seed 資料的展示庫存，並照 [spec.md 第 5 節](spec.md) 依序操作：

1. 電腦以 `admin`／`admin1234` 登入，到「基本資料」確認 A、B 兩庫與儲位，新增甘藍菜，單位「籠」、最低量 9、目標量 15。手機以 `worker`／`worker1234` 登入，刷新後可看到甘藍菜。
2. 手機在「倉管操作」入庫甘藍菜 10 籠至 A-01，記下系統產生的批次號；同頁把這批的 4 籠移至 B-02。電腦到「倉管操作 → 庫存查詢」刷新：A-01 為 6、B-02 為 4，全批 10。
3. 手機從 A-01 出庫 2 籠；電腦刷新庫存與「決策報表」：A-01 為 4、B-02 為 4，全批 8，甘藍菜低庫存、距離目標還差 7 籠，近 30 日出庫 2 籠。
4. 手機把 A-01 的 2 籠移至 A-02；電腦刷新確認 A-01 2、A-02 2、B-02 4，全批仍 8。展開異動歷史確認入庫、出庫、兩次移位與操作者。手機同頁操作成功後，庫存查詢卡片會自動更新；另一台裝置仍需刷新或按「查詢／更新」。
5. 手機對 seed 紅蘿蔔 `LOT-20260924-901`／B-03 送盤點實數 0，填原因。送件後餘量仍為 5；該批次／位置不能出庫、移出或同批移入。倉管直接開 `/#reviews` 顯示權限不足；電腦管理者開審核頁看到待審、原數 5、實數 0、差額 −5。
6. 管理者核准紅蘿蔔盤點。倉管對 seed 青花菜 `LOT-20260924-902`／B-04 送「壓損 1 籠」申請，管理者核准。刷新庫存及報表：紅蘿蔔 0、青花菜 2；盤虧 5 與報廢 1 分列，原入庫異動仍在，甘藍菜仍為 8。
7. 倉管嘗試從 A-01 出庫甘藍菜 99 籠：應顯示庫存不足，刷新後三處餘量及異動歷史皆不變。

每次送出時確認按鈕暫時停用；若網路中斷而結果不明，先查對應紀錄與餘量，**不要直接重送**。手機送出待審申請後，畫面應維持原來的寬度、表單不偏左，也不出現橫向捲動。若數字不符合上列起始值，先確認展示資料庫是否已被操作過，勿直接刪庫。實體手機的窄螢幕排版、觸控操作、網路連通性及跨裝置刷新，必須由團隊在實際展示設備上再驗收；自動測試無法替代此項。

### 備份、重演與還原

先以 Ctrl+C 停止後端及前端，確認沒有服務使用 SQLite。以下 PowerShell 從專案根目錄執行；每次產生不同時間戳記，原資料庫只移到 Git 忽略的 `data/backups`，不刪除：

```powershell
New-Item -ItemType Directory -Force -Path data/backups -ErrorAction Stop
$a4Backup = "data/backups/inventory-before-a4-$(Get-Date -Format yyyyMMdd-HHmmss-fff).db"
if (-not (Test-Path -LiteralPath data/inventory.db)) { throw '原資料庫不存在；若是首次建立，直接執行初始化與 seed。' }
if (Test-Path -LiteralPath $a4Backup) { throw '備份名稱已存在，請換一個檔名。' }
Move-Item -LiteralPath data/inventory.db -Destination $a4Backup -ErrorAction Stop
if (-not (Test-Path -LiteralPath $a4Backup)) { throw '備份未成功，請勿建立新資料庫。' }
.\.venv\Scripts\python.exe -m backend.database
.\.venv\Scripts\python.exe -m backend.seed
```

只在**確定要重演且已保存原檔**時做以上動作。確認 `$a4Backup` 指向的檔案存在，再重新啟動服務；新資料庫只含 seed 情境。若原本沒有資料庫，跳過整段搬移指令，只執行初始化與 seed。若 Python 指令報錯，先停止並檢查，不繼續展示。要還原某份備份時，同樣先停服務，先把目前的 `data/inventory.db` 移到另一個新名稱的備份，再用 `Copy-Item -LiteralPath <已確認的備份檔> -Destination data/inventory.db` 放回；不要覆寫唯一備份。`data` 及其備份不提交 Git。

### 自動檢查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run build
```

`tests/test_a4_integration.py` 使用暫存 SQLite 和兩個獨立登入的測試用戶端，重演上列新增品項、入庫、移位、出庫、待審凍結、審核、報表及超量拒絕；不修改本機 `data/inventory.db`。完整後端測試、前端建置的結果以實際執行輸出為準。完成自動檢查後仍須依上列腳本做實體手機／電腦彩排。

## 加做四項：缺貨需求、效期、儲位簡圖、CSV

`spec.md` 第 2.2 節的四項已納入操作頁。首次建立的新資料庫會直接含加做欄位與資料表；**既有** `data/inventory.db` 不可重新初始化，也不能刪除重建。先停止後端，再於專案根目錄執行：

```powershell
.\.venv\Scripts\python.exe -m backend.migrate_extras
```

此命令先用 SQLite 備份機制在 `data/backups` 建立含時間戳的原資料庫備份，之後只補上 `lots.expires_on` 與 `shortage_demands` 表及索引；可重跑，不更改既有庫存餘量、異動或示範資料。若失敗，先停止操作並保留備份，不直接刪庫。遷移後重新啟動後端並重新整理手機／電腦頁面。新資料庫已包含結構，無須執行此命令。

| 功能 | 畫面與 API | 規則 |
| --- | --- | --- |
| 缺貨需求 | 倉管「倉管操作 → 缺貨需求」；`POST/GET /api/shortages` | 倉管輸入啟用品項、正整數詢問量和選填備註，即使庫存為 0 也可記錄；不扣庫存、不新增出庫異動。倉管看自己的最近 100 筆；管理者在決策報表看累計量、筆數與最近 100 筆，與近 30 日實際出庫分列。 |
| 批次效期 | 管理者「倉管操作 → 庫存查詢 → 設定這批的到期日」；`PUT /api/inventory/lots/{id}/expiry` | 填入可信的 `YYYY-MM-DD` 日期；到期前 7 天內顯示「即將到期」，過期顯示「已到期」，未填顯示「未提供」。留空再儲存可清除。倉管可看提示但不能修改；效期不代表系統已判定品質。 |
| 儲位簡圖 | 兩角色「倉管操作 → 儲位簡圖」 | A、B 兩庫依儲位代碼顯示方格，點儲位會自動捲到下方目前庫存明細；按「更新簡圖」重新讀資料庫。只是代碼示意，不是實際建築平面圖，不跨單位合計。 |
| 庫存 CSV | 兩角色「倉管操作 → 庫存查詢 → 匯出目前查詢 CSV」；`GET /api/inventory/stock.csv` | 使用最後一次成功「查詢／更新」所套用的品項、批次、儲位條件；數量以匯出當下資料庫為準。下載 UTF-8 CSV，含儲位數量、全批合計、入庫日、庫齡與效期；空結果只有標題列。文字欄位有試算表公式注入防護。 |

建議依序驗收，所有數字以目前資料庫為準，不要為了重演刪除資料：

1. 管理者新增一個啟用品項「缺貨示範品項」（例如單位箱、最低 1、目標 4），不入庫。倉管到「缺貨需求」選它，填 3 箱並送出；刷新仍在。管理者按「更新報表」，看到缺貨詢問量 3 箱、筆數增加 1，但該品項庫存仍 0 箱、近 30 日實際出庫仍 0 箱。
2. 管理者在庫存查詢選一個已有批次，展開「設定這批的到期日」，輸入臺灣今天起 7 天內的日期並儲存；刷新後應標示「即將到期」。改成昨天，應顯示「已到期」；清空再儲存，應顯示「未提供」。換倉管登入，只能看效期，不能改。
3. 兩角色均可開儲位簡圖。點有庫存的儲位，應看到對應批次與數量；用倉管移位後按「更新簡圖」，來源與目標方格及明細應反映新位置。若所選批次待審或沒有可移數量，改用其他批次，不要重置資料庫。
4. 在庫存查詢選品項或儲位，先按「查詢／更新」，再按「匯出目前查詢 CSV」。開啟下載檔，核對每列品項、批次、儲位與數量和查詢畫面一致；輸入不存在的批次碼並按查詢後再匯出，檔案應只有標題列。只改輸入值但未按查詢時，匯出仍與當前顯示結果相同。手機也要確認四個區塊無橫向捲動，並用電腦、手機連同一後端核對刷新結果。

自動檢查：`tests/test_extras.py` 與 `tests/test_hardening.py` 使用暫存 SQLite 驗證權限、數量、報表分列、效期、CSV、歷史單位、待審停用與遷移保留資料；`tests/browser_extras.py` 以暫存資料庫檢查真實畫面、長名稱、查詢匯出一致性與下載。執行 `npm.cmd --prefix frontend run build`、`.\.venv\Scripts\python.exe -m pytest -q`，以及安裝 Chrome 與 `tests/requirements-browser.txt` 後執行 `.\.venv\Scripts\python.exe -m tests.browser_c1`、`.\.venv\Scripts\python.exe -m tests.browser_extras`、`.\.venv\Scripts\python.exe -m tests.browser_extras --webkit`、`.\.venv\Scripts\python.exe -m tests.browser_responsive`。同一測試腳本使用固定暫存埠，請依序執行。實體 iPhone Safari 仍須本人驗收。
