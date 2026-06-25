const API_BASE = window.VERBASE_API_BASE || "http://127.0.0.1:8000";

// ---- DB Connect ----
const dbUrlInput   = document.getElementById("dbUrlInput");
const connectDbBtn = document.getElementById("connectDbBtn");
const dbConnectMsg = document.getElementById("dbConnectMsg");

// Click on a hint → fill the input
document.querySelectorAll(".db-url-hints span").forEach((hint) => {
  hint.addEventListener("click", () => {
    dbUrlInput.value = hint.textContent;
    dbUrlInput.focus();
  });
});

connectDbBtn.addEventListener("click", async () => {
  const db_url = dbUrlInput.value.trim();
  if (!db_url) return;

  connectDbBtn.disabled = true;
  connectDbBtn.textContent = "Connecting…";
  dbConnectMsg.style.display = "none";
  dbConnectMsg.className = "db-connect-msg";

  try {
    const res = await fetch(`${API_BASE}/api/connect`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db_url }),
    });
    const data = await res.json();

    if (!res.ok) {
      dbConnectMsg.textContent = data.detail || "Connection failed.";
      dbConnectMsg.classList.add("error");
    } else {
      dbConnectMsg.textContent = `✓ connected · ${data.table_count} tables`;
      dbConnectMsg.classList.add("success");
      // Refresh the schema panel with the new DB
      renderSchemaFromSnapshot(data.schema);
      connStatus.classList.add("live");
      connStatus.innerHTML = `<span class="dot"></span> connected · ${data.table_count} tables detected`;
    }
    dbConnectMsg.style.display = "block";
  } catch (e) {
    dbConnectMsg.textContent = "Couldn't reach the backend.";
    dbConnectMsg.classList.add("error");
    dbConnectMsg.style.display = "block";
  } finally {
    connectDbBtn.disabled = false;
    connectDbBtn.textContent = "Connect";
  }
});


const thread = document.getElementById("thread");
const composer = document.getElementById("composer");
const input = document.getElementById("questionInput");
const sendBtn = document.getElementById("sendBtn");
const schemaList = document.getElementById("schemaList");
const connStatus = document.getElementById("connStatus");

const SQL_KEYWORDS = [
  "SELECT", "FROM", "WHERE", "GROUP BY", "ORDER BY", "LIMIT", "JOIN",
  "LEFT JOIN", "INNER JOIN", "ON", "AS", "AND", "OR", "COUNT", "SUM",
  "AVG", "MAX", "MIN", "DESC", "ASC", "DISTINCT", "WITH", "HAVING", "NOT",
  "IN", "LIKE", "BETWEEN", "IS", "NULL"
];

function highlightSQL(sql) {
  let escaped = sql
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  escaped = escaped.replace(/'([^']*)'/g, '<span class="str">\'$1\'</span>');
  escaped = escaped.replace(/\b(\d+(\.\d+)?)\b/g, '<span class="num">$1</span>');

  const kwPattern = new RegExp(`\\b(${SQL_KEYWORDS.join("|")})\\b`, "gi");
  escaped = escaped.replace(kwPattern, (m) => `<span class="kw">${m.toUpperCase()}</span>`);

  return escaped;
}

function renderSchemaFromSnapshot(data) {
  schemaList.innerHTML = "";
  data.tables.forEach((t) => {
    const div = document.createElement("div");
    div.className = "schema-table";
    const colNames = t.columns.map((c) => c.name).join(", ");
    div.innerHTML = `<div class="schema-table-name">${t.name}</div><div class="schema-cols">${colNames}</div>`;
    schemaList.appendChild(div);
  });
}

async function loadSchema() {
  try {
    const res = await fetch(`${API_BASE}/api/schema`);
    const data = await res.json();
    connStatus.classList.add("live");
    connStatus.innerHTML = `<span class="dot"></span> connected · ${data.tables.length} tables detected`;
    renderSchemaFromSnapshot(data);
  } catch (e) {
    connStatus.innerHTML = `<span class="dot"></span> couldn't reach backend`;
    schemaList.innerHTML = `<div class="schema-empty">Start the backend (uvicorn main:app) to see your schema here.</div>`;
  }
}

function appendUserMessage(text) {
  const el = document.createElement("div");
  el.className = "msg-user";
  el.textContent = text;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
}

function appendThinking() {
  const el = document.createElement("div");
  el.className = "thinking";
  el.id = "thinkingIndicator";
  el.innerHTML = `<span class="dot"></span> writing SQL for that…`;
  thread.appendChild(el);
  thread.scrollTop = thread.scrollHeight;
  return el;
}

function typeOutSQL(targetEl, sql, done) {
  const highlighted = highlightSQL(sql);
  
  let i = 0;
  const speed = Math.max(4, Math.min(18, 600 / sql.length));
  const plain = sql;

  function step() {
    i += Math.ceil(plain.length / 60); 
    if (i >= plain.length) {
      targetEl.innerHTML = highlighted;
      if (done) done();
      return;
    }
    targetEl.textContent = plain.slice(0, i);
    setTimeout(step, speed);
  }
  step();
}

function renderResult(data) {
  const block = document.createElement("div");
  block.className = "msg-block";

  const terminal = document.createElement("div");
  terminal.className = "sql-terminal";
  terminal.innerHTML = `
    <div class="sql-terminal-bar">
      <span class="tdot r"></span><span class="tdot y"></span><span class="tdot g"></span>
      <span class="sql-terminal-label">verbase — generated query</span>
    </div>
    <div class="sql-code" id="sqlCode"></div>
  `;
  block.appendChild(terminal);
  thread.appendChild(block);
  thread.scrollTop = thread.scrollHeight;

  const codeEl = terminal.querySelector("#sqlCode");

  typeOutSQL(codeEl, data.sql, () => {
    const meta = document.createElement("div");
    meta.className = "meta-row";
    meta.innerHTML = `<span>${data.row_count} rows</span><span>${data.elapsed_ms} ms</span>`;
    block.appendChild(meta);

    if (data.row_count === 0) {
      const empty = document.createElement("div");
      empty.className = "error-block";
      empty.textContent = "Query ran fine, but returned no rows.";
      block.appendChild(empty);
    } else {
      const wrap = document.createElement("div");
      wrap.className = "result-table-wrap";
      const table = document.createElement("table");
      table.className = "result-table";

      const thead = document.createElement("thead");
      thead.innerHTML = `<tr>${data.columns.map((c) => `<th>${c}</th>`).join("")}</tr>`;
      table.appendChild(thead);

      const tbody = document.createElement("tbody");
      data.rows.forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = row.map((v) => `<td>${v === null ? "—" : v}</td>`).join("");
        tbody.appendChild(tr);
      });
      table.appendChild(tbody);

      wrap.appendChild(table);
      block.appendChild(wrap);
    }
    thread.scrollTop = thread.scrollHeight;
  });
}

function renderError(message) {
  const block = document.createElement("div");
  block.className = "msg-block";
  block.innerHTML = `<div class="error-block">${message}</div>`;
  thread.appendChild(block);
  thread.scrollTop = thread.scrollHeight;
}

async function askQuestion(question) {
  document.querySelector(".welcome")?.remove();
  appendUserMessage(question);
  const thinkingEl = appendThinking();
  sendBtn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    thinkingEl.remove();

    if (!res.ok) {
      renderError(data.detail || "Something went wrong.");
    } else {
      renderResult(data);
    }
  } catch (e) {
    thinkingEl.remove();
    renderError("Couldn't reach the Verbase backend. Is it running on " + API_BASE + "?");
  } finally {
    sendBtn.disabled = false;
  }
}

composer.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q) return;
  input.value = "";
  askQuestion(q);
});

document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => askQuestion(chip.dataset.q));
});

loadSchema();
