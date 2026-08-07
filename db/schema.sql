-- =============================================================================
-- INVENTRA — SCHEMA DO BANCO DE DADOS
-- Segue o mesmo padrão usado em Assessor_sql.txt (tabelas de apoio +
-- tabela principal com FKs), adaptado para o domínio de estoque/compras.
-- =============================================================================

CREATE TABLE IF NOT EXISTS categories (
  id           SERIAL PRIMARY KEY,
  name         VARCHAR(64) NOT NULL,
  description  TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS movement_types (
  id      SERIAL PRIMARY KEY,
  type    TEXT NOT NULL          -- ENTRADA | SAIDA | AJUSTE
);

CREATE TABLE IF NOT EXISTS requisition_status (
  id      SERIAL PRIMARY KEY,
  status  TEXT NOT NULL          -- PENDENTE | APROVADA | REJEITADA | COMPRADA | CANCELADA
);

CREATE TABLE IF NOT EXISTS suppliers (
  id            SERIAL PRIMARY KEY,
  name          VARCHAR(120) NOT NULL,
  contact_info  TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS items (
  id            SERIAL PRIMARY KEY,
  name          VARCHAR(120) NOT NULL,
  category_id   INT REFERENCES categories(id) ON DELETE SET NULL,
  unit          VARCHAR(16) NOT NULL DEFAULT 'un',   -- kg, l, un, cx...
  min_stock     NUMERIC(14,3) NOT NULL DEFAULT 0,
  current_stock NUMERIC(14,3) NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_movements (
  id             BIGSERIAL PRIMARY KEY,
  item_id        INT REFERENCES items(id) ON DELETE CASCADE NOT NULL,
  quantity       NUMERIC(14,3) NOT NULL,
  type           INT REFERENCES movement_types(id) NOT NULL,
  reason         TEXT,
  registered_by  VARCHAR(64),               -- cargo/usuário que registrou
  occurred_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_text    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS requisitions (
  id                 BIGSERIAL PRIMARY KEY,
  item_id            INT REFERENCES items(id) ON DELETE SET NULL,
  item_name_freeform TEXT,                  -- usado quando o item ainda não existe no cadastro
  quantity_requested NUMERIC(14,3) NOT NULL,
  unit               VARCHAR(16),
  requested_by       VARCHAR(64) NOT NULL,  -- cargo/usuário solicitante
  status             INT REFERENCES requisition_status(id) NOT NULL DEFAULT 1,
  notes              TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  source_text        TEXT NOT NULL
);

-- Índices úteis para consultas comuns
CREATE INDEX IF NOT EXISTS idx_items_name ON items (LOWER(name));
CREATE INDEX IF NOT EXISTS idx_movements_item_time ON stock_movements (item_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_requisitions_status ON requisitions (status, created_at DESC);

-- =============================================================================
-- SEEDS
-- =============================================================================
INSERT INTO movement_types (type) VALUES
  ('ENTRADA'),
  ('SAIDA'),
  ('AJUSTE');

INSERT INTO requisition_status (status) VALUES
  ('PENDENTE'),
  ('APROVADA'),
  ('REJEITADA'),
  ('COMPRADA'),
  ('CANCELADA');

INSERT INTO categories (name) VALUES
  ('graos'),
  ('carnes'),
  ('laticinios'),
  ('hortifruti'),
  ('temperos'),
  ('bebidas'),
  ('limpeza'),
  ('embalagens'),
  ('outros');
