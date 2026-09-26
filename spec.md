# 竹南冷凍倉儲庫存管理系統 — spec.md

版本：4.2（2026-09-26 加做四項；保留既有 SQLite 資料）
依據：老師提供的《竹南-新版.pdf》個案，以及課堂使用手機、電腦現場操作並展示結果的要求。  
定位：做出能完整操作、資料真實保存的小型系統；介面與展示資料使用繁體中文。

文件分工：本檔定義功能、資料與驗收；`AGENTS.md` 定義片段與 Codex 工作方式；`README.md` 記錄實際安裝、啟動與已完成狀態。以 GitHub `KL-0728/system` 中合併到 `main` 的三份文件為共同依據。必做主線已整合，A 於 2026-09-26 決定實作第 2.2 節四項加做；實體手機與課堂設備仍須依 README 彩排，不能把自動測試當作現場驗收。

## 1. 題目、目標與設計邊界

竹南公司有兩座冷凍庫、約 20 種蔬果。到貨任意堆放，出貨難找，甚至有存貨多年後才被發現並已受損。系統要回答：**有什麼、多少、在哪一座庫的哪個位置、何時進來，以及發現不符時怎麼修正**。

這是一個課堂情境，不要求真的接上冷凍庫、磅秤、標籤機或客戶系統。課堂上以畫面操作代表現場人員記錄實物變動；不把模擬數據說成真實公司的庫存。完整展示的標準是：在電腦和手機開啟同一系統、實際填表提交、重新整理後結果仍在，而且每次庫存改變都有紀錄。

### 1.1 回答老師的第一題：誰做什麼決策

| 誰、做什麼決策 | 需要什麼資訊 | 真實世界要蒐集什麼資料 | 系統怎麼呈現 |
| --- | --- | --- | --- |
| 李太太：要不要採購、先買哪種、約買多少 | 目前庫存、近 30 日出庫量、低庫存門檻、當季行情、採購預算與損耗 | 每次入庫、出庫、盤點、人工設定的最低量／目標量；行情與預算由李太太在系統外掌握 | 低庫存清單、出庫統計及「距離目標量差多少」；最後由李太太結合行情與預算決定 |
| 李太太：目前能否賣、先賣哪一批 | 各批餘量、儲位、入庫日期、品質異常 | 入庫批次、移位、出庫、異常與盤點 | 庫存搜尋與依入庫日期排序的批次清單 |
| 李太太：何處需要檢查 | 找不到貨、盤點差異、庫齡過長和報廢原因 | 現場盤點的數字、異常原因、報廢量 | 差異待處理清單、庫齡與損耗統計 |
| 倉庫人員：貨放哪、從哪取 | 指定品項的批次、儲位和現有量 | 入庫時選位置，搬運時登記來源和目標，出庫時確認取貨位置 | 每次操作前顯示位置，提交後即時顯示新數量 |

若缺乏歷史需求與市場價格，系統不能精準預測採購量或最佳售價；只提供有依據的提示，不自動下單。

### 1.2 回答老師的第二題：模型、同步、決策支援

1. **建立數位模型**：把兩座冷凍庫劃成有代碼的儲位；用「品項 → 批次 → 儲位 → 數量」描述貨物，記錄每筆入庫、出庫、移位和調整。
2. **保持與現場同步**：每次實際動作後立即提交表單；遇到找不到貨先建立盤點差異，經管理者確認才改帳；定期用現場實數對帳。示範時用桌面上的卡片或畫面標記代表實物與儲位即可。
3. **提供決策支援**：展示即時位置、低庫存、近 30 日出庫、庫齡和損耗。門檻與目標量由管理者設定，畫面標示它是「人工門檻」而非精準預測。

## 2. 交付範圍

### 2.1 必做：一條完整可展示的主線

1. **兩種登入身分**：管理者、倉庫人員；以兩組示範帳號區分權限和操作者。
2. **基本資料**：品項、計量單位、兩座冷凍庫、儲位代碼。可預載約 20 個品項的範例資料，但展示時要能新增或修改一個品項。
3. **入庫**：選品項、輸入數量、選一個儲位，系統自動產生可在畫面閱讀的批次編號。若同一批要放多處，入庫後再用移位分拆。
4. **庫存查詢**：依品項、批次或儲位搜尋，顯示各位置數量及合計；顯示入庫日期與庫齡。
5. **出庫**：選批次與所在儲位、輸入數量並確認；可分次出庫，不能超過該位置剩餘量。
6. **移位**：選來源、目標和數量；成功後來源減、目標加，總量不變。
7. **盤點與損耗**：倉庫人員輸入現場實數或回報損壞，管理者確認原因後生成庫存調整；原來的交易紀錄不被覆寫。
8. **簡單決策畫面**：庫存總覽、低庫存提示、近 30 日出庫量、庫齡及損耗／盤差列表。

### 2.2 加做：必做主線完成後，挑選能現場演示的功能

必做主線完成後，A 已明確決定實作下列四項加做。這些功能不改變第 5 節的必做流程，不增加專用硬體或外部服務；每項須另行驗收，不可只展示假資料。

| 加做功能 | 何時值得做 | 課堂上如何證明真的完成 |
| --- | --- | --- |
| 缺貨需求紀錄 | 想讓李太太知道「客人想買但沒賣到」的需求 | 輸入品項與詢問數量（即使現有庫存為零）；報表立即增加一筆缺貨需求，與已出庫量分開顯示 |
| 批次效期提醒 | 有可信的人工輸入效期，想提醒優先檢查 | 管理者在示範批次填入到期日，查詢頁對到期前 7 天內標示「即將到期」、已過日期標示「已到期」；未填效期顯示「未提供」，不猜測品質 |
| 儲位簡圖 | 核心查詢完成後，想讓老師更直觀看到位置 | 用 A、B 兩庫的方格清單標示儲位；點 A-01 顯示批次與數量，移位後刷新圖立即更新；不聲稱是實際建築平面圖 |
| 庫存 CSV 匯出 | 老師希望帶走或比較報表 | 點「匯出庫存」下載純文字 CSV，開啟後能核對品項、批次、儲位與數量；無須 Excel 串接 |

若某項無法用展示當天的設備、網址與示範資料**實際操作出結果**，就留在構想中，不列為已完成功能。加做功能需先完成自己的簡短驗收，再納入展示。缺貨詢問量不得混入出庫量或扣減庫存；簡圖只是代碼方格，並非真實建築平面圖；CSV 要能以目前庫存篩選條件下載。

### 2.3 移除原規格中的高成本功能

| 原先提出的功能 | 本版處理 | 原因／簡單替代方式 |
| --- | --- | --- |
| QR／條碼生成、手機掃碼、標籤列印、員工 badge | **全部不做** | 畫面顯示批次編號，使用下拉選單或輸入文字查詢；桌上的紙卡可手寫編號 |
| 磅秤串接、固定全系統為公斤、多單位換算 | **不做** | 每個品項只選一種計量單位，如「籠」；同一品項不得混用不同單位 |
| 採購單、供應商、完整銷售訂單、預訂／保留、交期承諾 | **不做** | 入庫與出庫畫面直接登記庫存變動；備註欄可寫供應商或客戶 |
| FEFO 效期推算、複雜儲位容量驗證、出貨暫存區 | **不做** | 按入庫日顯示先進先出參考；儲位由人選擇；不承諾自動判定品質與物理空間 |
| 自動離線佇列、郵件通知、排程服務、IoT | **不做** | 若提交後未收到回應，顯示「結果未確認，請查詢紀錄」，恢復連線後先核對再決定是否重送；警示顯示在系統畫面 |
| 季節價格曲線、需求預測、毛利、ABC 分類 | **不做** | 最低庫存／目標庫存與歷史出庫量已足夠解釋初步採購建議 |
| 兩人同時出庫壓力展示、可重建事件流、冪等鍵架構 | **不做為展示功能** | 後端仍須用資料庫交易及條件檢查避免負庫存；課堂驗收只需做重複點擊與超量輸入檢查 |
| Docker 多服務部署、SMTP、異地備份和現場還原演示 | **不列入交付** | 一台展示電腦啟動網頁服務和資料庫；保留資料庫檔的簡單備份步驟 |

這些功能不排入本次課堂計畫；第 2.2 節的加做清單才是核心完成後可評估的範圍。

## 3. 畫面與權限

| 頁面 | 電腦／手機都要能做什麼 |
| --- | --- |
| 登入與首頁 | 以示範帳號登入；倉管首頁提供操作入口，管理者首頁顯示有庫存品項數、低庫存品項與待確認盤差；不同單位的數量不相加 |
| 品項及儲位 | 管理者建立／修改品項、單位、門檻、目標量及兩庫的儲位 |
| 入庫 | 倉庫人員選品項、數量、位置，提交後顯示批次號與庫存結果 |
| 庫存查詢 | 依名稱、批次或位置查詢，顯示兩庫位置、數量、入庫日、庫齡；可展開異動歷史 |
| 出庫／移位 | 倉庫人員選清單中的現有批次與儲位，輸入數量，畫面立即更新 |
| 盤點／損耗 | 倉庫人員提交實數及原因；管理者查看原數、實數和差額後確認或駁回 |
| 報表 | 管理者看低庫存、近 30 日出庫量、庫齡、損耗和盤差 |

倉庫人員不得核准或駁回任何申請，也不得直接更改帳面餘量；管理者可審核，但不能審核自己提交的申請。兩種角色均可讀取品項／儲位清單及庫存，管理者才可修改基本資料、審核及讀取決策報表；入庫、出庫、移位與提交申請以倉管身分展示。權限在後端驗證，不能只隱藏按鈕。所有操作顯示結果，提交時停用按鈕直到收到結果，避免連點。選單與按鈕需能在手機寬度使用，不用滑動桌面版大表格才能完成主要操作。

## 4. 固定資料庫設計（四個模組共用）

本次作業統一使用 **SQLite**。以下 SQL 對應 `backend/schema.sql`，由 A 維護。4.2 版為加做增補 `lots.expires_on` 與 `shortage_demands`；既有資料庫需先備份再執行可重跑的 `python -m backend.migrate_extras`，修改建表 SQL 不會自動更新既有資料庫，且不得直接刪庫套用新結構。

### 4.1 統一約定

- 本次所有數量都是**非負整數**。各品項自訂一個顯示單位（如籠、箱、整公斤），不換算、不接收小數。若要稱到 0.5 公斤，須將整個品項改以「公克」記錄，或列入未來擴充；已有交易的品項不得直接改單位。
- 主鍵一律為 `id`；外鍵一律用 `*_id`。儲位代碼（如 `A-01`）在全系統唯一。批次由後端生成 `LOT-YYYYMMDD-001` 形式的文字碼，重號時遞增；前端不自行組碼。
- `received_date` 存 `YYYY-MM-DD`；`created_at` / `reviewed_at` 由資料庫儲存 UTC 時間，畫面以臺灣時間顯示。日期格式、正整數與欄位長度仍須由後端驗證。
- 刪除有紀錄的品項、儲位或使用者不列入功能；停用後保留歷史。停用儲位前要先搬空。資料庫檔 `data/inventory.db` 不提交 Git，使用 `backend/seed.py` 重新產生示範資料。
- 每個後端 SQLite 連線都須執行 `PRAGMA foreign_keys = ON`；所有庫存寫入須在同一個交易內執行。以下建表 SQL 執行一次，後續如需變更資料表應寫遷移步驟，不可讓四人各自覆寫資料庫。

### 4.2 可直接建表的 SQL

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL COLLATE NOCASE UNIQUE,
  password_hash TEXT NOT NULL,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('ADMIN', 'WORKER')),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL COLLATE NOCASE UNIQUE,
  unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
  min_qty INTEGER NOT NULL DEFAULT 0
    CHECK (typeof(min_qty) = 'integer' AND min_qty >= 0),
  target_qty INTEGER NOT NULL DEFAULT 0
    CHECK (typeof(target_qty) = 'integer' AND target_qty >= min_qty),
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE warehouses (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL
);

CREATE TABLE locations (
  id INTEGER PRIMARY KEY,
  warehouse_id INTEGER NOT NULL REFERENCES warehouses(id),
  code TEXT NOT NULL UNIQUE,
  is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
);

CREATE TABLE lots (
  id INTEGER PRIMARY KEY,
  lot_code TEXT NOT NULL UNIQUE,
  product_id INTEGER NOT NULL REFERENCES products(id),
  received_date TEXT NOT NULL,
  expires_on TEXT,
  note TEXT NOT NULL DEFAULT '',
  created_by INTEGER NOT NULL REFERENCES users(id)
);

CREATE TABLE shortage_demands (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id),
  qty INTEGER NOT NULL CHECK (typeof(qty) = 'integer' AND qty > 0),
  note TEXT NOT NULL DEFAULT '',
  actor_id INTEGER NOT NULL REFERENCES users(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE stock_balances (
  lot_id INTEGER NOT NULL REFERENCES lots(id),
  location_id INTEGER NOT NULL REFERENCES locations(id),
  qty INTEGER NOT NULL DEFAULT 0
    CHECK (typeof(qty) = 'integer' AND qty >= 0),
  PRIMARY KEY (lot_id, location_id)
);

CREATE TABLE adjustment_requests (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN ('COUNT', 'SCRAP')),
  lot_id INTEGER NOT NULL,
  location_id INTEGER NOT NULL,
  original_qty INTEGER NOT NULL
    CHECK (typeof(original_qty) = 'integer' AND original_qty >= 0),
  observed_qty INTEGER
    CHECK (observed_qty IS NULL OR
      (typeof(observed_qty) = 'integer' AND observed_qty >= 0)),
  damaged_qty INTEGER
    CHECK (damaged_qty IS NULL OR
      (typeof(damaged_qty) = 'integer' AND damaged_qty > 0)),
  reason TEXT NOT NULL CHECK (length(trim(reason)) > 0),
  status TEXT NOT NULL DEFAULT 'PENDING'
    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')),
  requested_by INTEGER NOT NULL REFERENCES users(id),
  reviewed_by INTEGER REFERENCES users(id),
  review_note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  FOREIGN KEY (lot_id, location_id)
    REFERENCES stock_balances(lot_id, location_id),
  CHECK (
    (kind = 'COUNT' AND observed_qty IS NOT NULL AND damaged_qty IS NULL)
    OR (kind = 'SCRAP' AND observed_qty IS NULL AND damaged_qty IS NOT NULL)
  )
);

CREATE UNIQUE INDEX one_pending_request_per_balance
  ON adjustment_requests(lot_id, location_id)
  WHERE status = 'PENDING';

CREATE TABLE stock_movements (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL CHECK (kind IN
    ('RECEIPT', 'OUTBOUND', 'TRANSFER', 'COUNT_GAIN', 'COUNT_LOSS', 'SCRAP')),
  lot_id INTEGER NOT NULL REFERENCES lots(id),
  from_location_id INTEGER REFERENCES locations(id),
  to_location_id INTEGER REFERENCES locations(id),
  qty INTEGER NOT NULL
    CHECK (typeof(qty) = 'integer' AND qty > 0),
  actor_id INTEGER NOT NULL REFERENCES users(id),
  adjustment_request_id INTEGER UNIQUE REFERENCES adjustment_requests(id),
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (kind IN ('RECEIPT', 'COUNT_GAIN')
      AND from_location_id IS NULL AND to_location_id IS NOT NULL)
    OR (kind IN ('OUTBOUND', 'COUNT_LOSS', 'SCRAP')
      AND from_location_id IS NOT NULL AND to_location_id IS NULL)
    OR (kind = 'TRANSFER' AND from_location_id IS NOT NULL
      AND to_location_id IS NOT NULL AND from_location_id <> to_location_id)
  )
);

CREATE INDEX idx_lots_product ON lots(product_id);
CREATE INDEX idx_balances_location ON stock_balances(location_id);
CREATE INDEX idx_movements_lot_time ON stock_movements(lot_id, created_at);
CREATE INDEX idx_movements_kind_time ON stock_movements(kind, created_at);
CREATE INDEX idx_requests_status ON adjustment_requests(status);
CREATE INDEX idx_shortage_demands_product_time ON shortage_demands(product_id, created_at);
```

### 4.3 資料關係、流程和計算

`products` 1 對多 `lots`；`warehouses` 1 對多 `locations`；`lots` 與 `locations` 透過 `stock_balances` 多對多。每筆庫存變動新增一筆 `stock_movements`。`COUNT_GAIN`、`COUNT_LOSS`、`SCRAP` 一定連結一筆已核准的 `adjustment_requests`；盤點沒有差異時只核准申請，不產生數量為零的異動。後端驗證這些跨表規則。

| 操作 | 同一交易內依序處理 |
| --- | --- |
| 入庫 | 驗證品項及儲位啟用 → 建 `lots` → 在選定儲位建立該批 `stock_balances` → 新增 `RECEIPT`；每筆入庫選一個儲位 |
| 出庫 | 確認此批次／儲位沒有待審申請，且餘量足夠 → 減該處 `qty` → 新增 `OUTBOUND` |
| 移位 | 確認來源及已存在的目標「同批次＋儲位」都沒有待審申請、兩位置不同、目標儲位啟用且來源足夠 → 來源減、目標加（不存在就建）→ 新增一筆 `TRANSFER` |
| 送盤點／報廢 | 同一交易內擷取當下 `qty` 存 `original_qty`；盤點存非負整數 `observed_qty`，報廢存正整數 `damaged_qty <= original_qty`，都須填原因；唯一待審索引阻止同一批次／位置第二筆申請 |
| 核准盤點 | 只有 `ADMIN` 且非提交者能核准；在同一交易重查申請仍是 `PENDING`、餘量等於 `original_qty` → 計算 `observed_qty − original_qty`，依正負調整餘量並寫一筆 `COUNT_GAIN` 或 `COUNT_LOSS` → 標記 `APPROVED` |
| 核准報廢 | 同樣驗證管理者、非提交者、仍為 `PENDING`、餘量等於原數，且 `damaged_qty <= original_qty` → 扣減餘量、新增 `SCRAP` → 標記 `APPROVED` |
| 駁回申請 | 只有 `ADMIN` 且非提交者能駁回；同一交易確認仍為 `PENDING`，填 `review_note`，標記 `REJECTED`，餘量不變 |

每次庫存操作的寫入交易使用 `BEGIN IMMEDIATE` 開始；檢查、更新 `stock_balances`、新增 `stock_movements` 及相關核准狀態都成功才 `COMMIT`，任何一步失敗就 `ROLLBACK`。不要共用一個全域 SQLite 連線給同時到來的請求。前端提交時停用按鈕並顯示結果；在這個課堂版不做離線重送。同一 `lot_id + location_id` 的餘量必須保持非負，移位前後總量不變。入庫、出庫與移位按各自規則直接生效；盤點／報廢則必須經核准才改餘量。歷史異動只能新增，不能透過畫面修改或刪除。

待審凍結只作用於同一個 `lot_id + location_id`，不是封鎖整個儲位的所有品項；凍結期間也不能把同批貨移入該位置，避免盤點原數在審核前改變。餘量歸零仍保留 `stock_balances` 資料列，以保留申請外鍵與歷史。重複核准／駁回必須被拒，不能再次調整。前端停用按鈕只涵蓋同一頁等待回應時的連點；未實作伺服器冪等鍵，不宣稱網路重送也能自動去重。

**報表**：品項總量為該品項所有批次、儲位 `qty` 之和，沒有批次的啟用品項也要以 0 納入；不同品項的籠、箱等數量不能直接合計。低庫存條件為 `總量 < min_qty`；參考補貨缺口為 `max(target_qty − 總量, 0)`；近 30 日出庫量僅按品項／單位加總 `OUTBOUND`；庫齡依批次入庫日；`SCRAP` 與 `COUNT_LOSS` 分開統計。`created_at` 為 UTC，報表計算近 30 日時以同一時間基準查詢，避免跨裝置日期不同。

**加做資料**：`shortage_demands` 每筆保存品項、正整數詢問量、備註、登入操作者與 UTC 建立時間，不連結 `stock_balances`，也不寫入 `stock_movements`。報表的累計缺貨詢問量與近 30 日已出庫量分列。`lots.expires_on` 是可空的人工到期日；管理者可填寫、改寫或清除，查詢頁按臺灣當日判定到期前 7 天內「即將到期」、已過日期「已到期」，未填顯示「未提供」。這些狀態只是提醒，不自動判定品質或阻止出庫。

### 4.4 固定 API 欄位（四人共用）

所有 ID 使用資料庫整數 ID；畫面顯示文字碼。API 傳數量一律用 `qty`（整數），日期用 `YYYY-MM-DD`，角色用 `ADMIN`／`WORKER`。前端不得把中文單位文字傳給後端當成數量。至少固定以下輸入與結果；實際路徑可按 `routes/` 分檔，但合併前四人須維持同一份契約。

| 動作 | 必要輸入 | 成功後必須回傳／可查 |
| --- | --- | --- |
| 建品項／儲位 | 品項 `name, unit, min_qty, target_qty`；儲位 `warehouse_id, code` | 新增的 `id` 和欄位 |
| 入庫 | `product_id, location_id, qty, received_date, note` | `lot_id, lot_code` 與該儲位新餘量 |
| 庫存查詢 | 可選 `product_id, lot_code, location_id` | 每筆 `lot_id, lot_code, location_id, location_code, qty` 及合計 |
| 出庫 | `lot_id, location_id, qty, note` | 新餘量及異動 ID |
| 移位 | `lot_id, from_location_id, to_location_id, qty` | 兩處新餘量及異動 ID |
| 盤點／報廢申請 | `lot_id, location_id, kind, observed_qty` 或 `damaged_qty`，以及 `reason` | 申請 ID、原數、`PENDING` 狀態 |
| 核准／駁回 | 申請 ID、動作、`review_note`（駁回必填，核准可選） | 更新後狀態、調整量與新餘量 |
| 缺貨需求 | `product_id, qty, note`；倉管登入 | 需求 ID、品項、單位、詢問量、操作者與時間；不改庫存 |
| 批次效期 | `lot_id, expires_on`（可空）；管理者登入 | 批次 ID、代碼、人工到期日；庫存查詢附效期狀態 |
| 庫存 CSV | 同庫存查詢的可選篩選條件 | UTF-8 CSV 下載，包含各處餘量與全批合計 |

所有寫入由伺服器從登入狀態取得 `actor_id`／`requested_by`／`reviewed_by`，不能信任前端自行提交的操作者 ID。無權限、超量、停用儲位、待審凍結及欄位錯誤要回明確訊息，不更新資料。

A1 合併時在 README 記錄登入／登出／目前使用者、角色驗證與基本資料清單的實際 API；A3 合併時記錄共用庫存服務函式、交易責任及批次／位置／餘量選單 API。包含 HTTP 方法、路徑、輸入／輸出範例及失敗回應，並提供前端共用呼叫與型別。B、C、D 依這些已合併介面實作，不各自猜路徑、建立第二套登入或選單 API。A3 只提供操作所需最小選單，完整搜尋及異動歷史仍由 B2 完成。

## 5. 課堂當天的操作腳本

用預先準備的**情境資料**與兩個示範帳號。桌面可放寫有「A-01」「B-02」的紙卡代表實體位置；不需要印條碼。老師可以在手機、電腦交替操作同一套資料；每個步驟提交後刷新另一台裝置，確認結果同步。

展示起始資料固定為：A1 的基本資料不預載「甘藍菜」，讓步驟 1 可以新增；A3 在 seed 中準備「紅蘿蔔」於 B-03 的批次 5 籠、「青花菜」於 B-04 的另一批次 3 籠及對應入庫異動。兩者都不是甘藍菜，避免影響步驟 3 的總量與補貨缺口。seed 只補缺少的示範資料，不覆寫已操作的餘量，也不重複新增。重演需要回到起點時，A 先停服務並保存／移出原資料庫，再以相同 schema 建新展示資料庫、執行 seed；README 寫清楚步驟，不把重跑 seed 說成重置。

| 順序 | 現場操作 | 預期看到的結果 |
| --- | --- | --- |
| 1 | 在電腦登入管理者，查看 A／B 兩庫和儲位，建立「甘藍菜」（單位：籠、最低量 9、目標量 15） | 品項和儲位可於手機查到 |
| 2 | 在手機登入倉庫人員，新建一批甘藍菜 10 籠放 A-01；再將同批 4 籠移到 B-02 | 系統顯示文字批次號；電腦查詢看到 A-01 有 6、B-02 有 4，總數 10 |
| 3 | 在手機選 A-01 的批次出庫 2 籠 | A-01 變 4、B-02 仍 4、總數 8；電腦刷新後顯示低庫存及參考缺口 7 籠 |
| 4 | 在手機將 A-01 的 2 籠移至 A-02 | A-01 為 2、A-02 為 2、B-02 為 4；總數仍 8；異動歷史顯示操作者 |
| 5 | 倉管對預載於 B-03 的紅蘿蔔 5 籠盤點填 0 及原因；以倉管帳號直接開啟 README 記錄的管理者審核頁網址，再由管理者登入查看 | 倉管顯示無權限；管理者看到「待確認，原數 5、實數 0、差額 −5」，餘量仍 5；此批次／位置暫停出庫、移出與同批移入 |
| 6 | 管理者核准盤差；倉管對 B-04 的青花菜 3 籠回報「壓損 1 籠」，管理者再核准 | 紅蘿蔔變 0、青花菜變 2；報表分開列盤差 5 與報廢 1，原入庫紀錄保留，甘藍菜總量仍 8 |
| 7 | 倉管對 A-01 的甘藍菜嘗試出庫 99 籠 | 庫存不足被拒；所有餘量不變 |

演示前把首頁與手機連結準備好；「重新整理後還在」是每段展示的重要驗證。不要求即時推播，另一台裝置刷新即可取得最新資料。後端拒絕倉管直接呼叫審核 API、重複核准等案例保留自動測試結果，可另外說明；不要求為展示故意開放本來應隱藏或停用的按鈕。

## 6. 技術與展示環境

- 已選定：React + TypeScript + Vite 前端、FastAPI 後端、Python 內建 sqlite3 與一個 SQLite 檔，沿用已建立的骨架。開發各人使用自己的資料庫，Git Pull 不會同步庫存資料；展示時手機和電腦連同一台後端，才會操作同一份資料。建置完成的前端由後端一併提供。
- 展示電腦當伺服器；手機與電腦使用可互通的同一網路。課前用實際設備測試。若教室網路禁止裝置互通，可改用自己開的熱點或預先準備可連線的展示環境；這是課前部署檢查，不是系統功能。
- 本次只用示範帳號與虛構資料；密碼仍以雜湊保存。若未部署 HTTPS，不輸入真實人名、電話或營運資訊。提交後未收到回應時顯示「結果未確認」，恢復後先查庫存與異動，不能一律宣稱「未送出」或自動重送。
- 備份展示資料的簡單方法：停止服務後複製 SQLite 檔，記錄檔案位置與還原步驟。課堂不要求異地備份、排程或恢復演示。

## 7. 專案結構與檔案職責

以下沿用目前 React + FastAPI + SQLite 結構；預留目錄不是要求另外建立 ORM 或多餘抽象層。依既有程式分開頁面、API、商業規則、資料庫存取及必要測試。

```text
system/
├─ frontend/
│  └─ src/
│     ├─ pages/          # 各功能頁面
│     ├─ components/     # 共用導覽列、表格、表單元件
│     ├─ api/            # 集中呼叫後端 API
│     ├─ types/          # 前端共用資料型別
│     └─ App.tsx         # 路由與整體版面
├─ backend/
│  ├─ main.py            # FastAPI 入口與路由註冊
│  ├─ database.py        # SQLite 連線與交易管理
│  ├─ schema.sql         # 第 4.2 節的固定建表 SQL，由 A 維護
│  ├─ models/            # 資料表模型
│  ├─ schemas/           # API 輸入／輸出格式
│  ├─ routes/            # 各功能 API
│  ├─ services/          # 庫存規則與報表計算
│  └─ seed.py            # 示範帳號、品項、兩庫與情境資料
├─ tests/                # 後端規則及主要流程測試
├─ data/                 # 本機 SQLite；資料庫與備份均不提交
├─ .gitignore            # 忽略 data/inventory.db、環境檔與前端依賴
├─ README.md             # 安裝、啟動、示範帳號與操作順序
├─ AGENTS.md             # 任務片段、分支及 Codex 指示
└─ spec.md               # 本需求與驗收規格
```

主要檔案依功能分配如下；不必在開發前把每個小元件的檔名全部決定，但這些核心位置要先固定。

| 模組 | 前端 | 後端 | 核心規則 |
| --- | --- | --- | --- |
| 登入、品項與儲位 | `pages/LoginPage.tsx`、`pages/SettingsPage.tsx` | `routes/auth.py`、`routes/master_data.py` | `services/auth_service.py` |
| 入庫與庫存查詢 | `pages/InboundPage.tsx`、`pages/InventoryPage.tsx` | `routes/inventory.py` | `services/inbound_service.py`、`services/inventory_service.py` |
| 出庫與移位 | `pages/OutboundPage.tsx`、`pages/TransferPage.tsx` | `routes/outbound.py` | `services/outbound_service.py`、`services/transfer_service.py` |
| 盤點、損耗與報表 | `pages/AdjustmentPage.tsx`、`pages/ReportsPage.tsx` | `routes/adjustments.py`、`routes/reports.py` | `services/adjustment_service.py`、`services/report_service.py` |

`services/stock_service.py` 只放所有庫存操作共用的「驗證餘量、管理交易、更新餘量、寫入異動」函式，由 A 維護介面。B、C、D 各自在自己的 service 呼叫它，不得在 route 或前端直接改餘量。若需要修改共用介面，提出修改的人須通知受影響的組員，取得共識後由 A 檢查並決定合併，避免 AI 各自生成互不相容的庫存算法。

## 8. 四人分工與共同責任

分工採用「垂直模組」：每人負責自己的畫面、API、資料處理、測試及上台展示，不設只負責簡報或只負責把 AI 產生程式貼進專案的人。組員姓名確定後，以姓名取代 A、B、C、D。

| 組員 | 主要負責 | 必須交付與親自驗證 | 合併前交接 |
| --- | --- | --- | --- |
| A：基礎與整合 | A1 登入及基本資料清單／種子、A3 共用庫存與選單／情境資料、A2 品項儲位管理與導覽、A4 整合 | 示範帳號、步驟 1、手機連線；README、共用 API 與完整彩排 | 自己實測；接收功能分支，由 A 開 PR、修正與合併 |
| B：入庫與查詢 | B1 單筆入庫與批次、B2 庫存搜尋與異動歷史 | 步驟 2 的入庫與查詢；C2 移位後能查到分處及正確合計 | Push 功能分支，回報 A 分支名稱與實測結果 |
| C：出庫與移位 | C1 出庫、C2 移位 | 步驟 2 的分處、步驟 3–4、7 的超量拒絕；餘量非負、總量守恆 | Push 功能分支，回報 A 分支名稱與實測結果 |
| D：盤點與報表 | D1 盤點／報廢申請、D2 管理者審核、D3 報表與管理者首頁統計 | 步驟 5–7 的審核及拒絕、步驟 3 低庫存；未授權／重複核准被拒且有歷史 | Push 功能分支，回報 A 分支名稱與實測結果 |

共同責任：四人依第 4 節固定資料表和 API 欄位、確認畫面用詞。組員驗收後 Commit、Push 並回報 A；A 在 GitHub 檢查分支並建立 PR，拉到本機操作，確認後合併。網頁顯示「可以合併」不等於已通過功能測試。A 直接修其他人的分支時先協調暫停同分支修改，並交代原因。各片段完成就整合，不等全部寫完才第一次組裝。

若實際能力差異很大，可在時程上互相協助；A 可修復跨模組或緊急問題，但各組員仍負責自己模組的測試、交接和展示。接受協助的組員須能說明資料如何進入、經過哪些驗證、最後改動哪張表，並能在課堂親自操作與回答問題。

## 9. Vibe coding 協作規則

AI 可以產生大量程式碼，因此貢獻不能用「打了幾行」衡量，而要用可驗收的責任衡量。採用以下規則避免最後由一人包辦：

1. **一人一個可展示模組**：每位組員至少擁有第 8 節的一個完整模組，包含前端、API、測試與展示，不把所有核心程式交給同一人生成。
2. **小批次提交**：每完成一個可操作的小功能就提交版本，提交訊息寫明結果，例如「完成移位並驗證總量不變」，避免一次提交整個系統。
3. **功能分支與組長確認**：新工作從最新 `main` 建立功能分支；續做未合併的工作留在原分支。若下一片依賴尚未合併的上一片，可在同一分支續做、每片各 Commit 並告知 A 範圍，避免新分支缺少前片程式；A 接手修正期間暫停改該分支。前片合併後，新工作改從更新後的 `main` 開新分支。組員不用開 PR，由 A 檢查、建立 PR 並決定合併；A 自己的修改也須實測。
4. **記錄 AI 參與**：在合併說明記錄「使用 AI 完成哪些部分、人工修改哪些規則、跑過哪些測試」。不必保存所有聊天內容，除非課程另有要求。
5. **禁止看不懂就合併**：模組負責人必須能說明主要檔案、資料流、驗證規則和錯誤處理；無法說明的 AI 程式碼視為未完成。
6. **每人準備測試證據**：每人至少負責兩個測試案例，其中一個正常流程、一個錯誤流程，並保留測試結果或操作截圖。
7. **每人上台操作**：四人分別展示自己負責的模組；任一人都要知道完整主線，但不要求每人背誦所有程式碼。
8. **先驗收必做再納入加做**：A 已決定第 2.2 節四項均加做；各項仍要有自己的畫面、API、資料規則和實機驗收，不能只交假畫面或只交 API。

建議每個合併請求使用同一份完成檢查：畫面可操作、後端有驗證、資料重新整理後仍存在、正常與錯誤案例通過、負責人能說明。這些條件比程式碼行數更能證明每位組員的實際貢獻。

**修正問題的方式**：PR 尚未合併時，A 在 PR 寫清楚「哪個操作、預期結果、實際結果」。若 A 想直接處理，先在 PR 留言告知原負責人暫停修改該分支；A 同步遠端、切換到該 PR 的分支，在自己的電腦修正、重測、`Commit`、`Push` 到**同一分支**，既有 PR 會更新，再請原負責人確認並說明改動。也可由原負責人自己修復。若同時修改導致 PR 無法合併，由目前修正該分支的人取得最新 `main`，處理衝突並重測；不要強制推送覆蓋別人的版本。PR 已合併後才發現問題，A 可從最新 `main` 另開 `fix/...` 分支修復、測試、提出 PR 並確認合併，通知原負責人了解改動；影響展示的重大錯誤必要時可先將原 PR 還原。修正前先確認目前分支及尚未提交的檔案，避免把其他工作一起推上去。

## 10. 實作順序與必要測試

| 階段 | 主要負責 | 工作 | 可交付的結果 |
| --- | --- | --- | --- |
| 1 | A0 | 確認已回報的骨架實際可啟動並已合併；更新三份文件 | main 有骨架與最新任務；不重做骨架 |
| 2 | A1 → A3 | 先登入、種子、基本資料讀取，再共用交易、庫存選單、兩筆示範庫存；公布 API 與呼叫方式 | 合併後其他三人能直接用共同資料及介面開發，不必等 B 的入庫或 A2 管理頁 |
| 3（並行） | A2；B1 → B2；C1 → C2；D1 → D2 → D3 | A 做品項儲位管理；B 做入庫查詢；C 用 seed 庫存做出庫移位；D 用 seed 庫存做盤點審核與報表 | 各人自己的片段可操作並逐次交付，互不代做；跨模組數字在合併後再驗證 |
| 4 | A4＋四人共同 | 合併、修跨模組問題、整理 README、手機及電腦完整彩排 | 不靠手動改資料庫即可走完第 5 節；保留最後兩天修正和彩排 |

必測案例：超量拒絕、按鈕等待期間連點不重複提交、移位總量不變、待審批次／位置禁止移出和同批移入、倉庫人員不能核准、重複核准被拒、核准後歷史可查，以及手機操作後電腦刷新讀到同一結果。查詢／報表須用後端實際資料。A1／A3 合併前，B／C／D 可先閱讀規格與準備案例；正式串接依共同介面進行，缺依賴就回報，不各自仿造一份共用功能。

## 11. 不同時間工作的 GitHub／AI 操作方式

以 VS Code 開啟各自 Clone 的 `system`，用能讀寫此資料夾的 Codex 開發。四人各用自己的 GitHub 與 ChatGPT 帳號。ChatGPT 專案為選用的討論整理工具，不要求使用，也不代替 GitHub 同步程式。若仍使用專案討論，更新其中的規格副本；共同最新版以 GitHub `main` 上的 `spec.md`、`AGENTS.md`、`README.md` 為準。

1. **組長／A 管理共同程式庫**：GitHub 程式庫為 `KL-0728/system`；把最新版 `spec.md`、`AGENTS.md`、`README.md`、`.gitignore` 和可啟動的骨架放在 `main`，邀請另外三人存取。A 依第 4.2 節維護 `backend/schema.sql`，用 `seed.py` 產生可重置的示範資料。只提交 seed 程式，不提交 `data/inventory.db`、真實密碼、`.env` 或個人的虛擬環境。
2. **下載並安裝**：安裝 Git、VS Code、README 指定的 Python／Node.js 與官方 Codex 擴充套件，登入各自帳號。以 VS Code 的 Git: Clone 或終端機 `git clone` 下載到本機，再開啟整個 `system`；GitHub Desktop 可選，不必另裝。Clone 不含 `.venv`、`node_modules` 或資料庫，所以首次需安裝依賴、初始化一次，seed 完成後再按 README 執行；之後有依賴清單更新才重裝，已存在的資料庫不重做初始化。
3. **確認分支再寫**：VS Code 左下角是目前分支；新工作先在乾淨工作區切 `main`、Pull 最新版，再建立功能分支，例如 `feature/b-b1-inbound`。續做原分支先 Fetch 並同步其遠端更新；Pull 功能分支不會自動把新的 main 合進來，需要時由 A 協助整合 `origin/main`。Codex 可依明確任務協助建立／切換分支；若切換會覆蓋未提交修改、分支分岔或發生衝突，先回報，不擅自丟棄、重設或強制推送。共用對話帳號不會讓本機程式自動同步。
4. **每次交付一小段**：依根目錄 `AGENTS.md` 的片段名稱實作，功能完成後在自己的分支 `Commit`、`Push`，把片段、分支名稱、正常及錯誤操作結果告訴 A。組員不必自行開 PR，也不必同時在線；A 有空時根據回報確認即可。
5. **由 A 檢查並合併**：A 在 GitHub 查看功能分支，建立指向 `main` 的 PR 並拉到本機測試；有問題可協調後直接修原分支並 Push，或交原作者修。合併前確認分支包含最新 main，整合有關變動後重測，再由 A 合併已測過的版本。組員下一次取得最新 main，已存在的開發分支依第 9 節繼續。這是團隊約定；沒有設定分支保護時，GitHub 不會自動禁止其他人合併，因此組員不要自己合併。

在本機 Codex 可用：「我是 B，現在做 B1。請讀 AGENTS.md 和 spec.md，先準備正確功能分支，再實作、測試並告訴我怎麼驗收。」分支操作的授權不包含自動 Commit、Push 或合併，除非使用者另外要求。共用表或 API 要修改時先告訴 A。下載本次文件仍須由 A 提交到 GitHub，其他人 Pull 後才會拿到；Codex 開新的對話／工作階段讀取更新指示。

## 12. 假設與待確認

**已確認**：作業需可運作；沒有指定技術；當天以手機及電腦操作展示，特殊功能可以另外呈現；團隊共四人，希望以資管系大學生可實現的範圍為準，且主要使用 vibe coding 協助開發。組員不一定能同時工作，因此以 GitHub PR 和文字交接協作。

**用於展示的假設**：資料和倉庫位置為模擬；「甘藍菜」以籠計算；管理者可手動設定最低量和目標量；兩台裝置可連到同一個服務。若教室網路受限，課前改用熱點或可連線環境。老師個案沒有提供真實儲位、磅秤、效期、完整交易與價格資料，故本次不依賴它們。

**需由課程團隊決定**：展示電腦、現場網路與可工作的時段；A 至少每天安排一次交付檢查，避免大家等待整合。此時程是工作安排，完成度仍以實測為準。本次沿用現有技術與 SQLite；若課程另有硬性技術要求，再由團隊統一調整，不能各人自行轉換。
