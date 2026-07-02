import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
} from 'https://esm.sh/react@18.3.1';
import { createRoot } from 'https://esm.sh/react-dom@18.3.1/client?deps=react@18.3.1';
import htm from 'https://esm.sh/htm@3.1.1';

const html = htm.bind(React.createElement);

/* ---------- helpers ---------- */
function pretty(value) {
  if (value == null) return '';
  if (typeof value === 'string') {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function fmtMs(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/* ---------- small components ---------- */
function CodeBlock({ children }) {
  return html`<pre class="code">${children}</pre>`;
}

function HopCard({ ev }) {
  const call = ev.toolCalls[0];
  const results = ev.toolResults || [];
  return html`
    <div class="card">
      <div class="card-head">
        <span class="hopnum">HOP ${ev.hop}</span>
        ${call &&
        html`<span class="tool-chip"
          >${call.name}<span class="paren">( )</span></span
        >`}
        <span class="finish">${ev.finishReason}</span>
      </div>
      <div class="card-body">
        <div class="io">
          ${call &&
          html`<div class="io-row">
            <div class="io-label sent">↗ sent · tool call</div>
            <${CodeBlock}>${call.name}(${pretty(call.args)})<//>
          </div>`}
          ${results.map(
            (r, i) => html`<div class="io-row" key=${i}>
              <div class="io-label recv">↙ received · ${r.name}</div>
              <${CodeBlock}>${pretty(r.output)}<//>
            </div>`
          )}
          ${ev.text &&
          ev.text.trim() &&
          html`<div class="io-row">
            <div class="io-label recv">↙ model</div>
            <div class="llm-text">${ev.text}</div>
          </div>`}
        </div>
      </div>
      <div class="usage-foot">
        <span>▲ ${ev.usage.input} in</span>
        <span>▼ ${ev.usage.output} out</span>
      </div>
    </div>
  `;
}

function Banner({ ev }) {
  if (ev.type === 'key') {
    const rotating = ev.action === 'rotating';
    return html`<div class="banner key">
      <span class="ic">${rotating ? '🔁' : '🔑'}</span>
      <span
        >${rotating ? 'Rotated to key' : 'Using key'}
        <code>${ev.key}…</code> · ${ev.available} available</span
      >
    </div>`;
  }
  if (ev.type === 'notice') {
    const cls = ev.level === 'error' ? 'error' : 'warn';
    const ic =
      ev.code === 'rate_limit' ? '⏳' : ev.code === 'revoked' ? '⛔' : '⚠️';
    return html`<div class="banner ${cls}">
      <span class="ic">${ic}</span><span>${ev.message}</span>
    </div>`;
  }
  if (ev.type === 'error') {
    return html`<div class="banner error">
      <span class="ic">✕</span><span>${ev.message}</span>
    </div>`;
  }
  return null;
}

function Diagnosis({ result }) {
  const d = result.diagnosis;
  const bad = d.bug_type && d.bug_type !== 'none';
  return html`
    <div class="diagnosis">
      <h3>Diagnosis</h3>
      <div class="bug-badge ${bad ? 'bug-bad' : 'bug-none'}">
        ${bad ? '🐛 ' : '✓ '}${d.bug_type}
      </div>
      <div class="diag-field">
        <div class="k">Evidence</div>
        <div class="v">${d.evidence}</div>
      </div>
      <div class="diag-field">
        <div class="k">Recommended fix</div>
        <div class="v">${d.fix}</div>
      </div>
    </div>
  `;
}

/* ---------- timeline node wrapper ---------- */
function Node({ ev }) {
  if (ev.type === 'hop')
    return html`<div class="node hop"><${HopCard} ev=${ev} /></div>`;
  if (ev.type === 'result')
    return html`<div class="node result"><${Diagnosis} result=${ev.result} /></div>`;
  if (ev.type === 'key')
    return html`<div class="node keyev"><${Banner} ev=${ev} /></div>`;
  if (ev.type === 'notice')
    return html`<div class="node notice ${ev.level === 'error' ? 'error' : ''}">
      <${Banner} ev=${ev} />
    </div>`;
  if (ev.type === 'error')
    return html`<div class="node notice error"><${Banner} ev=${ev} /></div>`;
  return null;
}

/* ---------- app ---------- */
function App() {
  const [entities, setEntities] = useState([]);
  const [entityId, setEntityId] = useState('');
  const [cheap, setCheap] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | running | done | error
  const [items, setItems] = useState([]);
  const [result, setResult] = useState(null);
  const [elapsed, setElapsed] = useState(0);

  const esRef = useRef(null);
  const startRef = useRef(0);
  const bottomRef = useRef(null);

  useEffect(() => {
    fetch('/api/entities')
      .then((r) => r.json())
      .then((d) => {
        const list = d.entities || [];
        setEntities(list);
        if (list.length) setEntityId(list[0].entity_id);
      })
      .catch(() => {});
  }, []);

  // elapsed timer while running
  useEffect(() => {
    if (status !== 'running') return;
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 100);
    return () => clearInterval(t);
  }, [status]);

  // auto-scroll to newest node
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [items.length]);

  const stop = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const run = useCallback(() => {
    if (!entityId) return;
    stop();
    setItems([]);
    setResult(null);
    setElapsed(0);
    setStatus('running');
    startRef.current = Date.now();

    const url = `/api/investigate/stream?entityId=${encodeURIComponent(
      entityId
    )}${cheap ? '&cheap=1' : ''}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      let ev;
      try {
        ev = JSON.parse(e.data);
      } catch {
        return;
      }
      if (ev.type === 'result') setResult(ev.result);
      if (ev.type === 'done') {
        setStatus((s) => (s === 'error' ? s : 'done'));
        setElapsed(Date.now() - startRef.current);
        stop();
        return;
      }
      if (ev.type === 'error') setStatus('error');
      if (ev.type === 'log' || ev.type === 'start' || ev.type === 'done')
        return;
      setItems((prev) => [...prev, ev]);
    };

    es.onerror = () => {
      // Only surface as an error if we hadn't already finished cleanly.
      setStatus((s) => (s === 'running' ? 'error' : s));
      stop();
    };
  }, [entityId, cheap, stop]);

  useEffect(() => () => stop(), [stop]);

  const hops = items.filter((i) => i.type === 'hop');
  const tokIn = hops.reduce((a, h) => a + (h.usage?.input || 0), 0);
  const tokOut = hops.reduce((a, h) => a + (h.usage?.output || 0), 0);
  const rotations = items.filter(
    (i) => i.type === 'key' && i.action === 'rotating'
  ).length;

  const statusPill = {
    idle: html`<span class="pill idle">● idle</span>`,
    running: html`<span class="pill running"><span class="spin"></span>investigating…</span>`,
    done: html`<span class="pill done">✓ complete</span>`,
    error: html`<span class="pill error">✕ failed</span>`,
  }[status];

  return html`
    <div class="app">
      <div class="hero">
        <div>
          <h1><span class="dot"></span>Incident Agent</h1>
          <p>Live view of the agent ↔ LLM investigation loop, hop by hop.</p>
        </div>
        <div class="hero-actions">
          <a class="nav-link-muted" href="/">DB Explorer →</a>
        </div>
      </div>

      <div class="controls">
        <div class="field">
          <label>Entity</label>
          <select
            value=${entityId}
            disabled=${status === 'running'}
            onChange=${(e) => setEntityId(e.target.value)}
          >
            ${entities.map(
              (e) =>
                html`<option key=${e.entity_id} value=${e.entity_id}>
                  ${e.entity_id}${e.bug_type ? ` · ${e.bug_type}` : ''}
                </option>`
            )}
          </select>
        </div>
        <label class="toggle">
          <input
            type="checkbox"
            checked=${cheap}
            disabled=${status === 'running'}
            onChange=${(e) => setCheap(e.target.checked)}
          />
          cheap model (8b)
        </label>
        <button
          class="run-btn"
          onClick=${run}
          disabled=${status === 'running' || !entityId}
        >
          ${status === 'running' ? 'Running…' : '▶ Investigate'}
        </button>
      </div>

      <div class="statusbar">
        ${statusPill}
        <div class="stat-group">
          <div class="stat"><b>${hops.length}</b><span>hops</span></div>
          <div class="stat"><b>${tokIn}</b><span>tokens in</span></div>
          <div class="stat"><b>${tokOut}</b><span>tokens out</span></div>
          <div class="stat"><b>${rotations}</b><span>key rotations</span></div>
          <div class="stat"><b>${fmtMs(elapsed)}</b><span>elapsed</span></div>
        </div>
      </div>

      ${items.length === 0
        ? html`<div class="empty">
            <div class="big">🕵️</div>
            <div>Pick an entity and hit Investigate to watch the agent work.</div>
          </div>`
        : html`<div class="timeline">
            ${items.map((ev, i) => html`<${Node} key=${i} ev=${ev} />`)}
            <div ref=${bottomRef}></div>
          </div>`}
    </div>
  `;
}

createRoot(document.getElementById('root')).render(html`<${App} />`);
