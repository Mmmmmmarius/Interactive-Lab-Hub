const stateEl = document.querySelector("#participant-state");
const labelEl = document.querySelector("#participant-label");
const hintEl = document.querySelector("#participant-hint");
const hints = {
  quiet: "Resting quietly",
  paused: "Paused",
  listening: "Speak naturally",
  thinking: "Working on your words",
  speaking: "The box is talking",
};
let refreshSequence = 0;

async function refresh() {
  const sequence = ++refreshSequence;
  try {
    const response = await fetch("/api/state", {cache: "no-store"});
    const state = await response.json();
    if (sequence !== refreshSequence) return;
    stateEl.dataset.status = state.status;
    labelEl.textContent = state.status[0].toUpperCase() + state.status.slice(1);
    hintEl.textContent = state.phase === "waiting_for_start"
      ? "Start speaking within 2 seconds"
      : state.phase === "capturing_speech" ? "Keep speaking naturally" : hints[state.status];
  } catch (_error) {
    if (sequence !== refreshSequence) return;
    stateEl.dataset.status = "quiet";
    labelEl.textContent = "Paused";
    hintEl.textContent = "Controller unavailable";
  }
}

refresh();
setInterval(refresh, 400);
