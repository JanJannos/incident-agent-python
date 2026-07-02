const PRESETS = {
  'all-tables': `SELECT name AS table_name, sql AS schema
FROM sqlite_master
WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
ORDER BY name;`,
  entities: 'SELECT * FROM entities ORDER BY entity_id;',
  'events-order': `SELECT id, event_type, offset, produced_at, payload
FROM event_log
WHERE event_key = 'order_1000'
ORDER BY offset;`,
  replay: `SELECT
  e.id,
  e.event_type,
  e.offset,
  e.produced_at,
  CASE WHEN i.event_id IS NOT NULL THEN 1 ELSE 0 END AS was_processed
FROM event_log e
LEFT JOIN processed_events i ON e.id = i.event_id
WHERE e.event_key = 'order_1000'
ORDER BY e.offset;`,
  idempotency: 'SELECT * FROM processed_events ORDER BY processed_at DESC LIMIT 50;',
  expected: 'SELECT * FROM answer_key ORDER BY entity_id;',
};

let activeTable = null;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || `Request failed (${res.status})`);
  }
  return data;
}

function renderTable(rows, container) {
  container.innerHTML = '';
  if (!rows?.length) {
    container.innerHTML = '<div class="empty">No rows returned</div>';
    return;
  }

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const tbody = document.createElement('tbody');
  const columns = Object.keys(rows[0]);

  const headerRow = document.createElement('tr');
  for (const col of columns) {
    const th = document.createElement('th');
    th.textContent = col;
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);

  for (const row of rows) {
    const tr = document.createElement('tr');
    for (const col of columns) {
      const td = document.createElement('td');
      const value = row[col];
      td.textContent =
        value === null || value === undefined
          ? ''
          : typeof value === 'object'
            ? JSON.stringify(value)
            : String(value);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }

  table.appendChild(thead);
  table.appendChild(tbody);
  container.appendChild(table);
}

function setStatus(el, message, type = '') {
  el.textContent = message;
  el.className = `status ${type}`.trim();
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((tab) => {
    tab.classList.toggle('active', tab.dataset.tab === name);
  });
  document.querySelectorAll('.panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `panel-${name}`);
  });
}

async function loadMeta() {
  const meta = await api('/api/meta');
  const el = document.getElementById('db-meta');
  const totalRows = meta.tables.reduce((sum, t) => sum + t.rowCount, 0);
  el.innerHTML = `${meta.tables.length} tables · ${totalRows} total rows<br><code>${meta.dbPath}</code>`;

  const list = document.getElementById('table-list');
  list.innerHTML = '';
  for (const table of meta.tables) {
    const btn = document.createElement('button');
    btn.className = 'table-item';
    btn.innerHTML = `${table.name}<small>${table.rowCount} rows</small>`;
    btn.addEventListener('click', () => {
      activeTable = table.name;
      document.querySelectorAll('.table-item').forEach((item) => {
        item.classList.toggle('active', item === btn);
      });
      loadTable(table.name);
    });
    list.appendChild(btn);
  }

  if (meta.tables[0] && !activeTable) {
    list.firstChild?.click();
  }
}

async function loadTable(name) {
  const title = document.getElementById('table-title');
  const results = document.getElementById('table-results');
  title.textContent = name;
  setStatus(results, 'Loading…');

  try {
    const data = await api(`/api/tables/${name}?limit=200`);
    renderTable(data.rows, results);
    setStatus(
      document.getElementById('query-status'),
      `Showing ${data.rows.length} of ${data.total} rows`,
      'success'
    );
  } catch (error) {
    results.innerHTML = `<div class="empty">${error.message}</div>`;
  }
}

async function runQuery() {
  const sql = document.getElementById('sql-editor').value;
  const status = document.getElementById('query-status');
  const results = document.getElementById('query-results');
  const btn = document.getElementById('run-query');

  btn.disabled = true;
  setStatus(status, 'Running query…');

  try {
    const data = await api('/api/query', {
      method: 'POST',
      body: JSON.stringify({ sql }),
    });
    renderTable(data.rows, results);
    setStatus(
      status,
      `${data.rowCount} row(s) in ${data.durationMs}ms`,
      'success'
    );
  } catch (error) {
    results.innerHTML = '';
    setStatus(status, error.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function runTool(tool) {
  const status = document.getElementById('tools-status');
  const output = document.getElementById('tools-results');
  let params = {};

  switch (tool) {
    case 'get_entity_state':
      params = { entity_id: document.getElementById('tool-entity-id').value };
      break;
    case 'get_events':
      params = { event_key: document.getElementById('tool-event-key').value };
      break;
    case 'replay_events':
      params = { event_key: document.getElementById('tool-replay-key').value };
      break;
    case 'check_idempotency':
      params = { event_id: document.getElementById('tool-event-id').value };
      break;
  }

  setStatus(status, `Running ${tool}…`);
  try {
    const data = await api('/api/tools', {
      method: 'POST',
      body: JSON.stringify({ tool, params }),
    });
    output.textContent = JSON.stringify(data.result, null, 2);
    setStatus(status, `${tool} completed`, 'success');
  } catch (error) {
    output.textContent = '';
    setStatus(status, error.message, 'error');
  }
}

async function runInvestigation() {
  const entityId = document.getElementById('investigate-entity').value.trim();
  const cheap = document.getElementById('investigate-cheap').checked;
  const status = document.getElementById('investigate-status');
  const output = document.getElementById('investigate-results');
  const btn = document.getElementById('run-investigate');

  if (!entityId) {
    setStatus(status, 'entity_id is required', 'error');
    return;
  }

  btn.disabled = true;
  setStatus(status, 'Investigation running — this may take a few seconds…', 'warning');
  output.textContent = '';

  try {
    const data = await api('/api/investigate', {
      method: 'POST',
      body: JSON.stringify({ entityId, cheap }),
    });
    output.textContent = data.output;
    setStatus(status, 'Investigation complete', 'success');
  } catch (error) {
    setStatus(status, error.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => switchTab(tab.dataset.tab));
});

document.getElementById('run-query').addEventListener('click', runQuery);
document.getElementById('refresh-table').addEventListener('click', () => {
  if (activeTable) loadTable(activeTable);
});

document.getElementById('preset-select').addEventListener('change', (e) => {
  const preset = PRESETS[e.target.value];
  if (preset) {
    document.getElementById('sql-editor').value = preset;
    switchTab('query');
  }
});

document.getElementById('sql-editor').addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
    e.preventDefault();
    runQuery();
  }
});

document.querySelectorAll('[data-tool]').forEach((btn) => {
  btn.addEventListener('click', () => runTool(btn.dataset.tool));
});

document.getElementById('run-investigate').addEventListener('click', runInvestigation);

loadMeta().catch((error) => {
  document.getElementById('db-meta').textContent = error.message;
});
