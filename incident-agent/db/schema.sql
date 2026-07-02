CREATE TABLE IF NOT EXISTS event_log (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  partition INTEGER NOT NULL,
  offset INTEGER NOT NULL,
  event_key TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload TEXT NOT NULL,
  produced_at TEXT NOT NULL,
  consumer_group TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
  entity_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  version INTEGER NOT NULL,
  last_event_id TEXT,
  last_updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_events (
  event_id TEXT PRIMARY KEY,
  processed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bugs (
  entity_id TEXT PRIMARY KEY,
  correct_status TEXT NOT NULL,
  bug_type TEXT NOT NULL,
  explanation TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_event_log_key ON event_log(event_key);
CREATE INDEX IF NOT EXISTS idx_event_log_topic_partition ON event_log(topic, partition, offset);
CREATE INDEX IF NOT EXISTS idx_orders_id ON orders(entity_id);
