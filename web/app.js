"use strict";
let evidence = JSON.parse(document.getElementById("evidence").textContent);
let selected = "lost_ack";
let mode = "flawed";
let shown = Infinity;
let timer = null;
let localRunner = false;
const $ = id => document.getElementById(id);
const escapeHTML = value => String(value ?? "—").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
const current = () => evidence.results.find(result => result.id === selected && result.mode === mode);
const words = value => String(value).replace(/_/g, " ");

function stopReplay() { if (timer) clearInterval(timer); timer = null; $("replay").textContent = "Replay trace"; }

function renderSummary() {
  const protectedCases = evidence.results.filter(result => result.mode === "protected");
  const passes = protectedCases.filter(result => result.passed).length;
  $("suite-status").textContent = evidence.verification_passed ? "Verification complete" : "Verification needs attention";
  $("suite-status").classList.toggle("fail", !evidence.verification_passed);
  $("suite-description").textContent = `${passes}/${protectedCases.length} protected scenarios pass. ${evidence.assertion_count} assertions across both implementations.`;
  $("run-date").textContent = `Captured ${new Date(evidence.generated_at).toLocaleString()}`;
  $("environment").textContent = evidence.environment;
  $("hash").textContent = `Source SHA-256: ${evidence.source_sha256}`;
  $("case-count").textContent = evidence.scenario_count;
  $("scenarios").replaceChildren();
  for (const result of evidence.results.filter(result => result.mode === "flawed")) {
    const button = document.createElement("button");
    button.className = "scenario";
    button.setAttribute("aria-pressed", String(result.id === selected));
    button.innerHTML = `<span class="dot ${result.passed ? "green" : "red"}" aria-hidden="true"></span><span>${escapeHTML(result.title)}</span>`;
    button.addEventListener("click", () => { stopReplay(); selected = result.id; shown = Infinity; renderSummary(); renderCase(); });
    $("scenarios").append(button);
  }
}

function renderCase() {
  const result = current();
  $("requirement").textContent = `Requirement ${result.requirement}`;
  $("scenario-title").textContent = result.title;
  $("scenario-description").textContent = result.description;
  for (const implementation of ["flawed", "protected"]) {
    const run = evidence.results.find(item => item.id === selected && item.mode === implementation);
    $(`mode-${implementation}`).setAttribute("aria-pressed", String(mode === implementation));
    $(`${implementation}-result`).textContent = run.passed ? "Pass" : "Fail";
    $(`${implementation}-result`).className = run.passed ? "pass" : "fail";
  }
  $("checks").innerHTML = result.checks.map(check => `<tr class="${check.passed ? "" : "failed"}"><td>${check.event + 1}</td><td>${escapeHTML(words(check.field))}</td><td>${escapeHTML(check.expected)}</td><td>${escapeHTML(check.actual)}</td><td class="${check.passed ? "pass" : "fail"}">${check.passed ? "Pass" : "Fail"}</td></tr>`).join("");
  if (result.error) $("scenario-description").textContent += ` Test error: ${result.error}`;
  renderTrace();
}

function renderTrace() {
  const result = current();
  const events = result.events.slice(0, shown);
  $("step-count").textContent = `${events.length} of ${result.events.length} steps shown · captured evidence`;
  $("step").disabled = events.length >= result.events.length;
  $("trace").innerHTML = events.length ? events.map((event, index) => {
    const checks = result.checks.filter(check => check.event === index);
    const failures = checks.filter(check => !check.passed);
    const dropped = event.delivery !== "delivered";
    const outcome = event.response ? words(event.response.outcome) : "Not delivered";
    return `<li class="trace-event"><div class="exchange"><code class="frame"><span class="step-number">Step ${index + 1}</span>${escapeHTML(event.frame || "[empty frame]")}</code><span class="wire ${dropped ? "broken" : ""}" aria-hidden="true"></span><span class="outcome">${escapeHTML(outcome)}</span></div>${event.note ? `<p>${escapeHTML(event.note)}</p>` : ""}${event.delivery === "reply_dropped" ? '<p class="drop-note">Reply discarded by simulated link. Receiver evidence is retained by the test instrument.</p>' : ""}${checks.length ? `<div class="event-check ${failures.length ? "fail" : ""}">${failures.length ? failures.map(check => `${escapeHTML(words(check.field))}: expected ${escapeHTML(check.expected)}, observed ${escapeHTML(check.actual)}`).join(" · ") : `${checks.length} assertion${checks.length === 1 ? "" : "s"} passed`}</div>` : ""}</li>`;
  }).join("") : '<li class="empty-trace">Press Next step to inspect the first message.</li>';
  const last = [...events].reverse().find(event => event.response)?.response;
  $("device-state").innerHTML = [["Session",last?.session],["Indicator level",last?.device_level],["Command executions",last?.executions],["Telemetry",last?.freshness]].map(([label,value]) => `<div><small>${label}</small><strong>${escapeHTML(value)}</strong></div>`).join("");
}

for (const implementation of ["flawed", "protected"]) {
  $(`mode-${implementation}`).addEventListener("click", () => { stopReplay(); mode = implementation; shown = Infinity; renderCase(); });
}
$("replay").addEventListener("click", () => {
  if (timer) { stopReplay(); return; }
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { shown = Infinity; renderTrace(); return; }
  shown = 1; renderTrace(); $("replay").textContent = "Pause replay";
  timer = setInterval(() => { shown++; renderTrace(); if (shown >= current().events.length) stopReplay(); }, 1100);
});
$("step").addEventListener("click", () => { stopReplay(); shown = Math.min(Number.isFinite(shown) ? shown + 1 : 1, current().events.length); renderTrace(); });
$("show-all").addEventListener("click", () => { stopReplay(); shown = Infinity; renderTrace(); });

function download(name, content, type) {
  const url = URL.createObjectURL(new Blob([content], {type}));
  const link = document.createElement("a"); link.href = url; link.download = name;
  link.hidden = true; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
$("export-json").addEventListener("click", () => download("signal-bench-evidence.json", JSON.stringify(evidence, null, 2), "application/json"));
$("export-csv").addEventListener("click", () => {
  const rows = [["step","frame","delivery","outcome","device_level","executions","note"], ...current().events.map((event,index) => [index+1,event.frame,event.delivery,event.response?.outcome ?? "",event.response?.device_level ?? "",event.response?.executions ?? "",event.note])];
  const csv = rows.map(row => row.map(value => '"' + String(value).replace(/"/g,'""') + '"').join(",")).join("\r\n");
  download(`${selected}-${mode}.csv`, csv, "text/csv");
});
$("run").addEventListener("click", async () => {
  if (!localRunner) { $("local-instructions").showModal(); return; }
  stopReplay(); $("run").disabled = true; $("run").textContent = "Running…";
  $("server-note").textContent = "Compiling C++ and executing the scenarios locally…";
  try {
    const response = await fetch("/api/run", {method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Test runner failed. Check the terminal.");
    evidence = payload; shown = Infinity; renderSummary(); renderCase();
    $("server-note").textContent = evidence.verification_passed ? "New evidence captured from the local C++ test run." : "Run completed with unexpected failures. Inspect the results.";
  } catch (error) { $("server-note").textContent = `Could not complete the run: ${error.message}`; }
  finally { $("run").disabled = false; $("run").textContent = "Run tests"; }
});
renderSummary(); renderCase();
async function checkServer() {
  $("server-note").textContent = "Recorded test evidence. Replay the results below, or choose Run locally to execute the C++ suite yourself.";
  if (!/^https?:$/.test(location.protocol) || !["localhost", "127.0.0.1"].includes(location.hostname)) return;
  try {
    const response = await fetch("/api/status");
    if (response.ok && (await response.json()).runner === "signal-bench") {
      localRunner = true;
      $("run").disabled = false;
      $("run").textContent = "Run tests";
      $("server-note").textContent = "Local runner connected. Run tests to compile the controller and capture fresh evidence.";
    }
  } catch (_) { /* The portable report works without a server. */ }
}
checkServer();
