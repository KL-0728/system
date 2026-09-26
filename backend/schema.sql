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
