const TYPES = { text: "Text", number: "Zahl", date: "Datum", boolean: "Ja/Nein" };
let variables = [];
let results = [];

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

// ---------- Status ----------
async function checkHealth() {
  try {
    const h = await (await fetch("api/health")).json();
    $("health").textContent = `Extractor: ${h.extractor} · LLM (${h.llm_model}): ${h.llm}`;
  } catch { $("health").textContent = "Backend nicht erreichbar"; }
}

// ---------- Variablen ----------
function renderVars() {
  $("var-rows").innerHTML = variables.map((v, i) => `
    <tr>
      <td><input data-i="${i}" data-k="name" value="${esc(v.name)}" placeholder="z. B. Rechnungsnummer"></td>
      <td><textarea data-i="${i}" data-k="description" rows="1" placeholder="Was genau soll extrahiert werden?">${esc(v.description)}</textarea></td>
      <td><select data-i="${i}" data-k="type">${Object.entries(TYPES).map(([k, l]) =>
        `<option value="${k}" ${v.type === k ? "selected" : ""}>${l}</option>`).join("")}</select></td>
      <td><button class="icon" data-del="${i}" title="Entfernen">✕</button></td>
    </tr>`).join("");
}

$("var-rows").addEventListener("input", (e) => {
  const { i, k } = e.target.dataset;
  if (i !== undefined) variables[i][k] = e.target.value;
});
$("var-rows").addEventListener("click", (e) => {
  if (e.target.dataset.del !== undefined) { variables.splice(+e.target.dataset.del, 1); renderVars(); }
});
$("add-var").onclick = () => { variables.push({ name: "", description: "", type: "text" }); renderVars(); };

async function saveVars() {
  const clean = variables.filter((v) => v.name.trim());
  const r = await fetch("api/variables", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(clean) });
  const body = await r.json();
  if (!r.ok) { $("var-msg").innerHTML = `<span class="status-err">${esc(body.detail?.[0]?.msg || body.detail)}</span>`; return false; }
  variables = body; renderVars(); renderResults();
  $("var-msg").innerHTML = `<span class="status-ok">Gespeichert (${variables.length} Variablen).</span>`;
  return true;
}
$("save-vars").onclick = saveVars;

// ---------- Upload & Verarbeitung ----------
const drop = $("drop");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
$("file-input").addEventListener("change", (e) => { handleFiles(e.target.files); e.target.value = ""; });

async function handleFiles(fileList) {
  const files = [...fileList].filter((f) => f.name.toLowerCase().endsWith(".pdf"));
  if (!files.length) return;
  if (!(await saveVars())) return; // aktuelle Definition verwenden
  const entries = files.map((f) => { const r = { filename: f.name, values: null, error: null, running: true }; results.push(r); return [f, r]; });
  renderResults();
  for (const [file, entry] of entries) {  // nacheinander, um das LLM nicht zu überlasten
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await fetch("api/process", { method: "POST", body: fd });
      const body = await r.json();
      Object.assign(entry, r.ok ? body : { error: body.detail || `HTTP ${r.status}` });
    } catch (err) { entry.error = String(err); }
    entry.running = false;
    renderResults();
  }
}

// ---------- Ergebnisse ----------
function fmt(v, type) {
  if (v === null || v === undefined) return '<span class="null">–</span>';
  if (type === "boolean") return v ? "Ja" : "Nein";
  if (type === "date" && /^\d{4}-\d{2}-\d{2}$/.test(v)) { const [y, m, d] = v.split("-"); return `${d}.${m}.${y}`; }
  return esc(v);
}

function renderResults() {
  $("res-head").innerHTML = `<tr><th>Datei</th>${variables.map((v) => `<th>${esc(v.name)}</th>`).join("")}<th>Status</th></tr>`;
  $("res-rows").innerHTML = results.map((r) => {
    const status = r.running ? '<span class="status-run">läuft …</span>'
      : r.error ? `<span class="status-err">${esc(r.error)}</span>` : '<span class="status-ok">OK</span>';
    return `<tr><td>${esc(r.filename)}</td>${variables.map((v) => `<td>${r.values ? fmt(r.values[v.name], v.type) : ""}</td>`).join("")}<td>${status}</td></tr>`;
  }).join("");
  $("empty").style.display = results.length ? "none" : "";
  $("export").disabled = !results.some((r) => !r.running);
}

$("clear").onclick = () => { results = results.filter((r) => r.running); renderResults(); };

$("export").onclick = async () => {
  const done = results.filter((r) => !r.running);
  const r = await fetch("api/export", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ variables, results: done }) });
  const blob = await r.blob();
  const name = (r.headers.get("Content-Disposition") || "").match(/filename="(.+)"/)?.[1] || "extraktion.xlsx";
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: name });
  a.click(); URL.revokeObjectURL(a.href);
};

// ---------- Start ----------
(async () => {
  variables = await (await fetch("api/variables")).json();
  renderVars(); renderResults(); checkHealth();
})();
