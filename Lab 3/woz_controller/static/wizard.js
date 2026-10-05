const statusEl = document.querySelector("#status");
const transcriptEl = document.querySelector("#transcript");
const errorEl = document.querySelector("#error");
const timerEl = document.querySelector("#timer");
const lastSpokenEl = document.querySelector("#last-spoken");
const eventsEl = document.querySelector("#events");
let transcriptFocused = false;
let requestError = "";
let refreshSequence = 0;

transcriptEl.addEventListener("focus", () => { transcriptFocused = true; });
transcriptEl.addEventListener("blur", () => { transcriptFocused = false; });

async function post(path, body = {}) {
  const response = await fetch(path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed: ${response.status}`);
  return data;
}

async function act(path, body = {}) {
  refreshSequence += 1;
  requestError = "";
  errorEl.textContent = "";
  try {
    await post(path, body);
    await refresh();
  } catch (error) {
    requestError = error.message;
    errorEl.textContent = requestError;
  }
}

function render(state) {
  statusEl.textContent = state.status;
  document.querySelector("#phase").textContent = state.phase;
  document.querySelector("#automatic").checked = state.automatic_reply;
  const schedule = state.schedule;
  document.querySelector("#daily-enabled").checked = schedule.enabled;
  document.querySelector("#daily-next").textContent = !schedule.enabled
    ? "Schedule off. Manual controls still work."
    : schedule.paused ? "Paused. Resume starts a fresh waiting interval."
    : schedule.busy ? "Conversation in progress. The next interval starts when it ends."
    : schedule.next_at ? `Next ${schedule.next_kind === "morning" ? "morning scene" : "self-talk"}: ${new Date(schedule.next_at).toLocaleString("en-US", {timeZone: schedule.timezone, month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", timeZoneName: "short"})}`
    : "Waiting for the next active window.";
  document.querySelector("#backend").textContent = state.backend === "dry-run"
    ? "Silent simulation; no audio devices" : "Pi audio; real microphone and speaker";
  statusEl.dataset.status = state.status;
  if (!transcriptFocused) transcriptEl.value = state.transcript || "";
  errorEl.textContent = requestError || state.last_error || "";
  lastSpokenEl.textContent = state.last_spoken || "Nothing spoken yet";
  const seconds = state.work.remaining_seconds;
  timerEl.textContent = state.work.running
    ? `Work timer: ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} remaining`
    : state.work.paused_remaining !== null ? `Work timer paused: ${seconds}s remaining` : "No work timer running";
  eventsEl.replaceChildren(...state.events.map((event) => {
    const item = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = new Date(event.time).toLocaleTimeString();
    item.append(time, document.createTextNode(event.message));
    return item;
  }));
}

async function refresh() {
  const sequence = ++refreshSequence;
  try {
    const response = await fetch("/api/state", {cache: "no-store"});
    const state = await response.json();
    if (sequence === refreshSequence) render(state);
  } catch (error) {
    if (sequence === refreshSequence) errorEl.textContent = `Controller unavailable: ${error.message}`;
  }
}

document.querySelector("#morning").addEventListener("click", () => act("/api/morning"));
document.querySelector("#self-talk").addEventListener("click", () => act("/api/self-talk"));
document.querySelector("#daily-enabled").addEventListener("change", (event) => act("/api/schedule", {enabled: event.target.checked}));
document.querySelector("#listen").addEventListener("click", () => act("/api/listen"));
document.querySelector("#quiet").addEventListener("click", () => act("/api/quiet"));
document.querySelector("#stop").addEventListener("click", () => act("/api/stop"));
document.querySelector("#save-transcript").addEventListener("click", () => act("/api/transcript", {text: transcriptEl.value}));
document.querySelectorAll(".scripted").forEach((button) => {
  button.addEventListener("click", () => act("/api/speak", {text: button.dataset.text}));
});
document.querySelector("#speak-custom").addEventListener("click", () => {
  act("/api/speak", {text: document.querySelector("#custom-reply").value});
});
document.querySelector("#work-start").addEventListener("click", () => {
  act("/api/work/start", {minutes: Number(document.querySelector("#minutes").value)});
});
document.querySelector("#work-expire").addEventListener("click", () => act("/api/work/expire"));
document.querySelector("#work-accept").addEventListener("click", () => act("/api/work/accept"));
document.querySelector("#work-defer").addEventListener("click", () => act("/api/work/defer"));

document.querySelector("#pause").addEventListener("click", () => act("/api/pause"));
document.querySelector("#resume").addEventListener("click", () => act("/api/resume"));
document.querySelector("#reset").addEventListener("click", () => act("/api/reset"));
document.querySelector("#automatic").addEventListener("change", (event) => act("/api/replies", {automatic: event.target.checked}));
document.querySelector("#simulate").addEventListener("click", () => act("/api/simulate", {text: document.querySelector("#simulated-input").value}));

refresh();
setInterval(refresh, 500);
