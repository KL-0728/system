# 竹南冷凍倉儲庫存管理系統 — spec.md

版本：4.0（資管系課堂實作版；固定 SQLite 資料庫與非同步協作流程）  
依據：老師提供的《竹南-新版.pdf》個案，以及課堂使用手機、電腦現場操作並展示結果的要求。  
定位：做出能完整操作、資料真實保存的小型系統；介面與展示資料使用繁體中文。

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

先通過第 5 節全部步驟，再由團隊按剩餘時間與實際需求選做；**下面各項互不依賴，沒有任何一項是必做**。只用既有手機、電腦和示範資料即可演示，不增加專用硬體或外部服務。

| 加做功能 | 何時值得做 | 課堂上如何證明真的完成 |
| --- | --- | --- |
| 缺貨需求紀錄 | 想讓李太太知道「客人想買但沒賣到」的需求 | 輸入品項與詢問數量（即使現有庫存為零）；報表立即增加一筆缺貨需求，與已出庫量分開顯示 |
| 批次效期提醒 | 有可信的人工輸入效期，想提醒優先檢查 | 在示範批次填入到期日，查詢頁按日期標示「即將到期」；未填效期的批次顯示「未提供」，不猜測品質 |
| 儲位簡圖 | 核心查詢完成後，想讓老師更直觀看到位置 | 用 A、B 兩庫的方格清單標示儲位；點 A-01 顯示批次與數量，移位後刷新圖立即更新；不聲稱是實際建築平面圖 |
| 庫存 CSV 匯出 | 老師希望帶走或比較報表 | 點「匯出庫存」下載純文字 CSV，開啟後能核對品項、批次、儲位與數量；無須 Excel 串接 |

若某項無法用展示當天的設備、網址與示範資料**實際操作出結果**，就留在構想中，不列為已完成功能。加做功能需先完成自己的簡短驗收，再納入展示。

### 2.3 移除原規格中的高成本功能

| 原先提出的功能 | 本版處理 | 原因／簡單替代方式 |
| --- | --- | --- |
| QR／條碼生成、手機掃碼、標籤列印、員工 badge | **全部不做** | 畫面顯示批次編號，使用下拉選單或輸入文字查詢；桌上的紙卡可手寫編號 |
| 磅秤串接、固定全系統為公斤、多單位換算 | **不做** | 每個品項只選一種計量單位，如「籠」；同一品項不得混用不同單位 |
| 採購單、供應商、完整銷售訂單、預訂／保留、交期承諾 | **不做** | 入庫與出庫畫面直接登記庫存變動；備註欄可寫供應商或客戶 |
| FEFO 效期推算、複雜儲位容量驗證、出貨暫存區 | **不做** | 按入庫日顯示先進先出參考；儲位由人選擇；不承諾自動判定品質與物理空間 |
| 自動離線佇列、郵件通知、排程服務、IoT | **不做** | 斷線時顯示提交失敗，恢復連線後由人確認再重新操作；警示顯示在系統畫面 |
| 季節價格曲線、需求預測、毛利、ABC 分類 | **不做** | 最低庫存／目標庫存與歷史出庫量已足夠解釋初步採購建議 |
| 兩人同時出庫壓力展示、可重建事件流、冪等鍵架構 | **不做為展示功能** | 後端仍須用資料庫交易及條件檢查避免負庫存；課堂驗收只需做重複點擊與超量輸入檢查 |
| Docker 多服務部署、SMTP、異地備份和現場還原演示 | **不列入交付** | 一台展示電腦啟動網頁服務和資料庫；保留資料庫檔的簡單備份步驟 |

這些功能不排入本次課堂計畫；第 2.2 節的加做清單才是核心完成後可評估的範圍。

## 3. 畫面與權限

| 頁面 | 電腦／手機都要能做什麼 |
| --- | --- |
| 登入與首頁 | 以示範帳號登入；首頁顯示庫存總數、低庫存品項與待確認盤差 |
| 品項及儲位 | 管理者建立／修改品項、單位、門檻、目標量及兩庫的儲位 |
| 入庫 | 倉庫人員選品項、數量、位置，提交後顯示批次號與庫存結果 |
| 庫存查詢 | 依名稱、批次或位置查詢，顯示兩庫位置、數量、入庫日、庫齡；可展開異動歷史 |
| 出庫／移位 | 倉庫人員選清單中的現有批次與儲位，輸入數量，畫面立即更新 |
| 盤點／損耗 | 倉庫人員提交實數及原因；管理者查看原數、實數和差額後確認或駁回 |
| 報表 | 管理者看低庫存、近 30 日出庫量、庫齡、損耗和盤差 |

倉庫人員不得確認自己提交的差異，也不得直接更改帳面餘量；管理者可以確認。所有操作顯示成功或失敗，提交時停用按鈕直到收到結果，避免連點重複處理。選單與按鈕需能在手機寬度使用，不用滑動桌面版大表格才能完成主要操作。

## 4. 固定資料庫設計（四個模組共用）

本次作業統一使用 **SQLite**。以下 SQL 是必做版唯一的建表定義；A 在開發時將同樣的 SQL 放入 `backend/schema.sql`，其他組員使用既有資料表，不各自發明名稱。若四人共同決定變更欄位，先修改本節，再由 A 修改 `backend/schema.sql`，在合併請求中說明舊示範資料如何重建。加做功能的欄位或表等決定加做時再增補。

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
  note TEXT NOT NULL DEFAULT '',
  created_by INTEGER NOT NULL REFERENCES users(id)
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
```

### 4.3 資料關係、流程和計算

`products` 1 對多 `lots`；`warehouses` 1 對多 `locations`；`lots` 與 `locations` 透過 `stock_balances` 多對多。每筆庫存變動新增一筆 `stock_movements`。`COUNT_GAIN`、`COUNT_LOSS`、`SCRAP` 一定連結一筆已核准的 `adjustment_requests`；盤點沒有差異時只核准申請，不產生數量為零的異動。後端驗證這些跨表規則。

| 操作 | 同一交易內依序處理 |
| --- | --- |
| 入庫 | 驗證品項及儲位啟用 → 建 `lots` → 在選定儲位建立該批 `stock_balances` → 新增 `RECEIPT`；每筆入庫選一個儲位 |
| 出庫 | 確認此批次／儲位沒有待審申請，且餘量足夠 → 減該處 `qty` → 新增 `OUTBOUND` |
| 移位 | 確認來源沒有待審申請、目標儲位啟用且來源足夠 → 來源減、目標加（不存在就建）→ 新增一筆 `TRANSFER` |
| 送盤點／報廢 | 擷取當下 `qty` 存 `original_qty`；盤點存 `observed_qty`，報廢存 `damaged_qty`；送出後由唯一待審索引阻止同處第二筆申請 |
| 核准盤點 | 只有 `ADMIN` 且非提交者能核准；重查餘量等於 `original_qty` → 計算 `observed_qty − original_qty`，依正負調整餘量並寫一筆 `COUNT_GAIN` 或 `COUNT_LOSS` → 標記 `APPROVED` |
| 核准報廢 | 同樣重查餘量，驗證 `damaged_qty <= original_qty` → 扣減餘量、新增 `SCRAP` → 標記 `APPROVED` |
| 駁回申請 | 只有 `ADMIN` 且非提交者能駁回；填 `review_note`，標記 `REJECTED`，餘量不變 |

SQLite 寫入交易使用 `BEGIN IMMEDIATE` 開始；檢查、更新 `stock_balances`、新增 `stock_movements`、核准狀態都成功才 `COMMIT`，任何一步失敗就 `ROLLBACK`。不要共用一個全域 SQLite 連線給同時到來的請求。前端提交時停用按鈕並顯示成功／失敗；在這個課堂版不做離線重送。同一 `lot_id + location_id` 的餘量必須保持非負，移位前後總量不變；未經核准不得直接修改餘量。歷史異動只能新增，不能透過畫面修改或刪除。

**報表**：品項總量為該品項所有批次、儲位 `qty` 之和；低庫存條件為 `總量 < min_qty`；參考補貨缺口為 `max(target_qty − 總量, 0)`；近 30 日出庫量僅加總 `OUTBOUND`；庫齡依批次入庫日；`SCRAP` 與 `COUNT_LOSS` 分開統計。`created_at` 為 UTC，報表計算近 30 日時以同一時間基準查詢，避免跨裝置日期不同。

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
| 核准／駁回 | 申請 ID、動作、可選 `review_note` | 更新後狀態、調整量與新餘量 |

所有寫入由伺服器從登入狀態取得 `actor_id`／`requested_by`／`reviewed_by`，不能信任前端自行提交的操作者 ID。無權限、超量、停用儲位、待審凍結及欄位錯誤要回明確訊息，不更新資料。

## 5. 課堂當天的操作腳本

用預先準備的**情境資料**與兩個示範帳號。桌面可放寫有「A-01」「B-02」的紙卡代表實體位置；不需要印條碼。老師可以在手機、電腦交替操作同一套資料；每個步驟提交後刷新另一台裝置，確認結果同步。

| 順序 | 現場操作 | 預期看到的結果 |
| --- | --- | --- |
| 1 | 在電腦登入管理者，查看 A／B 兩庫和儲位，建立「甘藍菜」（單位：籠、最低量 9、目標量 15） | 品項和儲位可於手機查到 |
| 2 | 在手機登入倉庫人員，新建一批甘藍菜 10 籠放 A-01；再將同批 4 籠移到 B-02 | 系統顯示文字批次號；電腦查詢看到 A-01 有 6、B-02 有 4，總數 10 |
| 3 | 在手機選 A-01 的批次出庫 2 籠 | A-01 變 4、B-02 仍 4、總數 8；電腦刷新後顯示低庫存及參考缺口 7 籠 |
| 4 | 在手機將 A-01 的 2 籠移至 A-02 | A-01 為 2、A-02 為 2、B-02 為 4；總數仍 8；異動歷史顯示操作者 |
| 5 | 另用情境資料預載 B-03 的一批 5 籠；倉管發現找不到，在手機盤點填 0 籠及原因 | 管理者在電腦看到「待確認，原數 5、實數 0、差額 −5」；此批次／儲位暫停出庫 |
| 6 | 管理者在電腦確認差異；倉管對另一筆預載批次回報「壓損 1 籠」，管理者再確認 | B-03 變 0；損耗量少 1；報表分別顯示盤差和壓損，仍查得到原本的入庫紀錄 |
| 7 | 以倉管帳號嘗試確認盤差，並嘗試對 A-01 出庫 99 籠 | 權限不足與庫存不足均被拒絕；餘量不變 |

演示前把首頁與手機連結準備好；「重新整理後還在」是每段展示的重要驗證。不要求即時推播，另一台裝置刷新即可取得最新資料。

## 6. 技術與展示環境

- 建議：一個響應式網頁前端（React 或團隊熟悉的框架）、一個後端服務（如 FastAPI）與一個 SQLite 資料庫檔。手機和電腦開啟同一個後端網址；可把建置完成的前端由後端一併提供，方便只啟動一個服務。若團隊更熟悉其他技術，維持相同功能即可。
- 展示電腦當伺服器；手機與電腦使用可互通的同一網路。課前用實際設備測試。若教室網路禁止裝置互通，可改用自己開的熱點或預先準備可連線的展示環境；這是課前部署檢查，不是系統功能。
- 本次只用示範帳號與虛構資料；密碼仍以雜湊保存。若未部署 HTTPS，不輸入真實人名、電話或營運資訊。網路中斷時明示「未送出」，恢復後確認目前庫存再操作。
- 備份展示資料的簡單方法：停止服務後複製 SQLite 檔，記錄檔案位置與還原步驟。課堂不要求異地備份、排程或恢復演示。

## 7. 專案結構與檔案職責

以下以 React + FastAPI + SQLite 為建議結構。若團隊最後改用其他框架，可以調整檔名，但仍須維持「頁面、API、商業規則、資料庫模型、測試」分開，避免所有程式集中在少數檔案。

```text
zhunan-inventory/
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
├─ data/                 # SQLite 資料庫；正式提交時不得含真實個資
├─ .gitignore            # 忽略 data/inventory.db、環境檔與前端依賴
├─ README.md             # 安裝、啟動、示範帳號與操作順序
└─ spec.md               # 本需求與驗收規格
```

主要檔案依功能分配如下；不必在開發前把每個小元件的檔名全部決定，但這些核心位置要先固定。

| 模組 | 前端 | 後端 | 核心規則 |
| --- | --- | --- | --- |
| 登入、品項與儲位 | `pages/LoginPage.tsx`、`pages/SettingsPage.tsx` | `routes/auth.py`、`routes/master_data.py` | `services/auth_service.py` |
| 入庫與庫存查詢 | `pages/InboundPage.tsx`、`pages/InventoryPage.tsx` | `routes/inventory.py` | `services/inbound_service.py`、`services/inventory_service.py` |
| 出庫與移位 | `pages/OutboundPage.tsx`、`pages/TransferPage.tsx` | `routes/outbound.py` | `services/outbound_service.py`、`services/transfer_service.py` |
| 盤點、損耗與報表 | `pages/AdjustmentPage.tsx`、`pages/ReportsPage.tsx` | `routes/adjustments.py`、`routes/reports.py` | `services/adjustment_service.py`、`services/report_service.py` |

`services/stock_service.py` 只放所有庫存操作共用的「驗證餘量、管理交易、更新餘量、寫入異動」函式，由 A 維護介面。B、C、D 各自在自己的 service 呼叫它，不得在 route 或前端直接改餘量。若需要修改共用介面，提出修改的人須通知另外三人並由至少一人審查，避免 AI 各自生成互不相容的庫存算法。

## 8. 四人分工與共同責任

分工採用「垂直模組」：每人負責自己的畫面、API、資料處理、測試及上台展示，不設只負責簡報或只負責把 AI 產生程式貼進專案的人。組員姓名確定後，以姓名取代 A、B、C、D。

| 組員 | 主要負責 | 必須交付與親自驗證 | 交叉審查 |
| --- | --- | --- | --- |
| A：基礎與整合 | 專案初始化、資料庫模型、登入權限、品項／儲位、共用版面、展示環境 | 兩種帳號權限正確；手機與電腦能連線；整理 `README.md` 和整合版本 | 審查 D 的盤點權限；由 B 審查資料模型 |
| B：入庫與查詢 | 建立批次、分配儲位、庫存搜尋、異動歷史 | 完成展示步驟 1–2；證明同一批可分兩處且合計正確 | 審查 A 的資料模型；由 C 審查入庫規則 |
| C：出庫與移位 | 出庫、超量拒絕、移位、總量驗證 | 完成展示步驟 3–4、7；證明出庫不為負且移位總量不變 | 審查 B 的入庫規則；由 D 審查負庫存測試 |
| D：盤點與報表 | 盤點／損耗申請、管理者確認、低庫存、庫齡與損耗報表 | 完成展示步驟 5–6；證明未授權核准遭拒且調整留有紀錄 | 審查 C 的負庫存測試；由 A 審查盤點權限 |

共同責任：四人依第 4 節固定資料表和 API 欄位、確認畫面用詞；即使無法同時上線討論，每次開始工作前都先取得最新 `main`，完成可操作的小段後就提出合併請求，至少每週一次從 `main` 走完整流程。A 負責協調合併，不代表 A 必須修完所有人的問題；造成問題的模組由原負責人修正，審查者協助定位。

若實際能力差異很大，可在時程上互相協助，但不得直接接管對方全部模組。接受協助的組員仍須能說明資料如何進入、經過哪些驗證、最後改動哪張表，並能在課堂親自操作與回答問題。

## 9. Vibe coding 協作規則

AI 可以產生大量程式碼，因此貢獻不能用「打了幾行」衡量，而要用可驗收的責任衡量。採用以下規則避免最後由一人包辦：

1. **一人一個可展示模組**：每位組員至少擁有第 8 節的一個完整模組，包含前端、API、測試與展示，不把所有核心程式交給同一人生成。
2. **小批次提交**：每完成一個可操作的小功能就提交版本，提交訊息寫明結果，例如「完成移位並驗證總量不變」，避免一次提交整個系統。
3. **功能分支與交叉審查**：每個模組使用自己的分支；合併前由表中指定組員實際啟動、操作驗收案例並審查。不能只看 AI 的解釋便同意合併。
4. **記錄 AI 參與**：在合併說明記錄「使用 AI 完成哪些部分、人工修改哪些規則、跑過哪些測試」。不必保存所有聊天內容，除非課程另有要求。
5. **禁止看不懂就合併**：模組負責人必須能說明主要檔案、資料流、驗證規則和錯誤處理；無法說明的 AI 程式碼視為未完成。
6. **每人準備測試證據**：每人至少負責兩個測試案例，其中一個正常流程、一個錯誤流程，並保留測試結果或操作截圖。
7. **每人上台操作**：四人分別展示自己負責的模組；任一人都要知道完整主線，但不要求每人背誦所有程式碼。
8. **先完成必做再生成加做**：AI 很容易讓範圍膨脹。第 5 節尚未全數通過前，不開始第 2.2 節的加做功能。

建議每個合併請求使用同一份完成檢查：畫面可操作、後端有驗證、資料重新整理後仍存在、正常與錯誤案例通過、負責人能說明。這些條件比程式碼行數更能證明每位組員的實際貢獻。

## 10. 實作順序與必要測試

| 階段 | 主要負責 | 工作 | 可交付的結果 |
| --- | --- | --- | --- |
| 1 | A，B 協助審查 | 建立頁面、後端、SQLite、兩種登入身分、品項與儲位 | 電腦／手機都能查到相同資料；專案啟動方式寫入 README |
| 2 | B，C 協助審查 | 建批次、入庫、庫存查詢與異動歷史 | 可操作展示步驟 1–2，刷新後不消失 |
| 3 | C，D 協助審查 | 出庫、移位與非負數驗證 | 可操作步驟 3–4、7；庫存總和正確 |
| 4 | D，A 協助審查 | 盤點／損耗提交、管理者確認與報表 | 可操作步驟 5–6，權限與歷史紀錄正確 |
| 5 | 四人共同 | 串接完整流程、手機版調整、錯誤處理及跨裝置彩排 | 不靠手動改資料庫即可從頭走完第 5 節；四人都完成自己的展示段落 |

必測案例：出庫超量拒絕、重複點擊不重複扣量、移位總量不變、盤點待確認時禁止修改該位置、倉庫人員不能確認、核准後歷史可查，以及手機操作後電腦刷新能讀到同一結果。完成上述測試後先彩排，再從第 2.2 節挑選一項加做；若時間不足，直接以完成的必做主線展示。

## 11. 不同時間工作的 GitHub／AI 操作方式

ChatGPT **專案**保存共用 `spec.md`、專案指示與四個人的討論；GitHub **程式庫**保存目前可執行的程式和版本。四個對話不會自動把程式合成一套。開發時的共同最新版以 GitHub `main` 和其中的 `spec.md` 為準；如果規格有更新，同步替換 ChatGPT 專案中的 `spec.md`，避免對話讀到舊版本。

1. **組長／A 建立共同程式庫**：在 GitHub 建 `zhunan-inventory`（可設私人），把 `spec.md`、`README.md`、`.gitignore` 和可啟動的骨架放在 `main`，邀請另外三人存取。A 先依第 4.2 節建立 `backend/schema.sql`，用 `seed.py` 產生可重置的示範資料。只提交 seed 程式，不提交 `data/inventory.db`、密碼、`.env` 或個人的虛擬環境。
2. **每人下載自己的程式副本**：安裝並登入 GitHub Desktop，使用「Clone Repository」把同一程式庫下載到自己的電腦。開工前先取得最新 `main`，再從它建立自己的功能分支，例如 `feature/b-inbound`。各人可在不同時間、不同電腦工作。
3. **選擇 AI 實際寫碼的路徑**：建議每人把下載的程式庫資料夾交給可讀寫本機程式的編碼工具（例如能開啟本機資料夾的 Codex），請 AI 在自己的分支修改檔案並執行測試。若只有網頁上的 ChatGPT 專案對話、只上傳了 `spec.md`，就讓 AI 根據你貼給它的**目前程式檔案**產生修改，組員自己把修改放入本機程式庫並測試。另一個選項是依產品介面把 GitHub 程式庫連到 Codex cloud，選定程式庫／環境後審查它產出的分支和差異，再提出 PR；這是選用方式，不是開始課堂專案的必要步驟。不要把「看得到規格」理解成「AI 已看到最新原始碼」。
4. **每次交付一小段**：功能完成後在自己的分支 `Commit`，再 `Push`；開 Pull Request（PR），寫明修改檔案、API／資料表有無變動、正常及錯誤操作的實測結果。指定另一名組員審查；若審查者沒有同時在線，留下 PR 和測試步驟供他之後處理。
5. **審查後才合併**：審查者拉取分支、實際測試，再合併到 `main`。下一位開工者先同步最新 `main`；已有工作中的分支要先更新它再測試。合併衝突由改動該功能的人處理，A 協助協調。`main` 應保持可啟動，展示前要從新下載的乾淨副本演練。

四人各自在 ChatGPT 專案開一個對話作為自己的工作紀錄，第一則訊息寫：「我負責 A／B／C／D；請先讀最新版 `spec.md`，只處理我的模組；如果看不到程式庫，請我提供目前檔案後再修改。」如共用資料表或 API 契約必須改動，先在 GitHub 開議題或 PR 說明，等受影響的組員確認再合併。專案對話可以協助規劃、寫程式與除錯；能否**直接**編輯程式，取決於該對話是否實際取得程式庫或本機資料夾的存取權。

## 12. 假設與待確認

**已確認**：作業需可運作；沒有指定技術；當天以手機及電腦操作展示，特殊功能可以另外呈現；團隊共四人，希望以資管系大學生可實現的範圍為準，且主要使用 vibe coding 協助開發。組員不一定能同時工作，因此以 GitHub PR 和文字交接協作。

**用於展示的假設**：資料和倉庫位置為模擬；「甘藍菜」以籠計算；管理者可手動設定最低量和目標量；兩台裝置可連到同一個服務。若教室網路受限，課前改用熱點或可連線環境。老師個案沒有提供真實儲位、磅秤、效期、完整交易與價格資料，故本次不依賴它們。

**需由課程團隊決定**：截止日期、展示電腦的作業系統、現場網路條件、哪位組員擔任 A，以及每週審查 PR 的期限。本規格已固定建議技術及 SQLite 資料結構；若課程要求改用 MySQL，必須由四人共同修改第 4 節與建表程式，不能讓各組員各自轉換。
