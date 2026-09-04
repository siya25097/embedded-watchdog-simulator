# UI/UX Document
## Embedded Watchdog & Fault Recovery Simulator — Dashboard

**Version:** 0.1 (implemented MVP; official project reference)
**Based on:** PRD v0.1, SRS v0.1, Architecture v0.1

---

## 1. Design Principles

1. **Glanceability first.** An interviewer/reviewer should understand system state within 3 seconds of looking at the screen — color and layout do the explaining, not paragraphs of text.
2. **Show cause and effect.** When a fault is injected, the resulting status change and recovery should be visually traceable — this is the entire point of the demo.
3. **No unnecessary chrome.** This is a monitoring dashboard, not a marketing site — keep it dense, functional, and technical-looking (think Grafana/industrial HMI, not a consumer app).
4. **Simple and implementation-ready.** Since this is built solo with Streamlit, favor Streamlit's native components over custom CSS/JS — polish comes from good layout and color, not custom widgets.

---

## 2. User Journey

There is one primary user journey (the "demo flow"), since this is a single-screen operator tool:

1. **Launch** → user runs the app → dashboard loads showing all configured tasks initializing.
2. **Observe baseline** → within a few seconds, all tasks show `HEALTHY` with live-updating "last heartbeat" times.
3. **Inject a fault** → user selects a task and a fault type, triggers injection.
4. **Watch detection** → the task's status visibly changes (HEALTHY → LATE → STALLED), color shifts accordingly, and an event appears in the log.
5. **Watch recovery** → status changes to `RECOVERING` → then back to `HEALTHY`, with the task's recovery counter incrementing and a new log entry.
6. **Review history** → user scans the event log / recovery counts to see the full story of what happened during the session.

This loop (3→5) is what should be repeated during a live resume/interview demo — the UI should make repeating it easy (no page reload needed, controls always visible).

---

## 3. Screens

Given the small scope, this is a **single-screen application** with logical sections rather than separate pages/routes:

### Screen: Main Dashboard

Sections (top to bottom or left/right split):

1. **Header bar** — project name, overall system status summary (e.g., "4/5 tasks healthy"), and a start/stop/reset control.
2. **Task Status Grid** — one card/row per task showing: name, status badge (color-coded), last heartbeat (relative time, e.g., "0.3s ago"), recovery count.
3. **Fault Injection Panel** — a control section: select task (dropdown), select fault type (radio/select: Hang / Comm Failure), "Inject Fault" button, and a "Clear Fault" button.
4. **Event Log** — a scrolling/reverse-chronological table: timestamp, task, event type, details. Newest at top.
5. **(Stretch) Timeline/Chart** — a simple time-series view (e.g., using Streamlit's line chart or a Gantt-style strip) showing heartbeat gaps/stall periods per task over the session — nice visual proof for a demo, not required for MVP.

---

## 4. Navigation

No multi-page navigation needed for MVP — single screen, single view. If the "Timeline/Chart" stretch feature grows large, it can become a second tab (Streamlit supports `st.tabs`) labeled "Live" and "History," but don't build this unless the single-screen layout genuinely gets cluttered.

---

## 5. Components & Interactions

| Component | Behavior |
|---|---|
| **Status badge** | Colored pill/label: green = HEALTHY, amber = LATE, red = STALLED, blue = RECOVERING, grey = INITIALIZING/FAILED_PERMANENTLY |
| **Task card/row** | Auto-updates every refresh cycle (≤1s); hovering isn't necessary since this isn't a interactive-per-item UI — status is always visible |
| **Fault injection form** | Task dropdown populated from live task list; fault-type select; disable "Inject Fault" button while a fault is already active on the selected task (prevents double-injection edge case E-3 from the SRS) |
| **Event log table** | Read-only, auto-scrolling to newest entry or simply prepending; consider a "clear log" button for demo resets, separate from the actual simulation state |
| **Header system summary** | A single aggregate line, e.g. "3 healthy · 1 recovering · 1 stalled" — gives the 3-second read described in Design Principle 1 |

---

## 6. Forms

Only one form-like interaction exists: **Fault Injection**.

- Fields: `task_id` (select, required), `fault_type` (select, required)
- Validation: button disabled unless both fields are chosen; button disabled if selected task already has an active fault (mirrors SRS BR-2/E-3)
- Submit: immediate action (no confirmation dialog needed — this is a low-stakes internal tool, not a destructive production action)

---

## 7. Loading / Error / Empty States

- **Loading (app just started):** Tasks show `INITIALIZING` status (grey) until their first heartbeat arrives — never show a blank or crashed-looking state on first load.
- **Empty event log:** Show a simple placeholder row/message like "No events yet — inject a fault to see the watchdog in action," which doubles as a usage hint during a demo.
- **Error (e.g., invalid config on startup):** Show a clear Streamlit error banner (`st.error`) explaining what's wrong (e.g., "Task 'sensor_poll' has timeout_ms <= period_ms — check config.yaml") rather than a raw traceback — reflects the SRS validation rules (V-1 through V-4).
- **Recovery failure state (stretch, FR-21):** If a task exceeds max recovery attempts, show it clearly as `FAILED_PERMANENTLY` (distinct grey/black badge) rather than looping it forever — this is a good visual "edge case handled" moment for a demo.

---

## 8. Responsive Behavior

Since this is a local developer/demo tool typically viewed on a laptop, full mobile responsiveness is **not a priority**. Streamlit's default responsive layout (columns collapsing on narrow windows) is sufficient — no custom breakpoints needed. If you do want it to look reasonable on a shared screen/projector during an interview, favor larger font sizes for status badges over dense small text.

---

## 9. Accessibility

Reasonable, low-effort accessibility choices worth doing since they cost little in Streamlit:
- Don't rely on color alone for status — pair each color badge with a text label (e.g., "🟢 HEALTHY", not just a green dot), so the status is legible even to colorblind viewers or in a black-and-white printed screenshot for a resume/README.
- Ensure sufficient contrast for status colors against Streamlit's default background (test in both light and dark Streamlit themes, since reviewers may have either).
- Keep font sizes at Streamlit's default or larger — don't shrink text to fit more on screen.

---

## 10. Typography, Colors, Spacing

Since Streamlit provides the base styling, keep customization minimal and purposeful:

- **Typography:** Use Streamlit's default font stack; reserve `st.title`/`st.header`/`st.subheader` hierarchy consistently (Title = app name, Header = section names like "Task Status," Subheader/caption = supporting details like timestamps).
- **Color palette (status semantics — keep consistent everywhere status appears):**
  - Healthy → green (`#2ECC71` or Streamlit's default success green)
  - Late → amber/yellow (`#F1C40F`)
  - Stalled → red (`#E74C3C`)
  - Recovering → blue (`#3498DB`)
  - Initializing/Failed permanently → grey (`#95A5A6`)
- **Spacing:** Use Streamlit's `st.columns` for the task grid to keep consistent horizontal spacing; leave generous vertical spacing between the Task Grid, Fault Injection Panel, and Event Log sections (`st.divider()` between major sections) so the single screen doesn't feel cramped.

---

## 11. Implementation Notes for Streamlit

- Use `st.columns` for the task grid (one column per task, or a row-based `st.dataframe`/`st.table` if task count grows).
- Use a background thread (see Architecture §5) + `st.session_state` to persist simulation objects across Streamlit reruns; do **not** restart the simulation on every widget interaction.
- Use `st_autorefresh` (community component) or a manual `time.sleep` + `st.rerun()` loop for the live-updating refresh described in FR-25 — document whichever tradeoff you pick (the community component is simpler; the manual loop avoids an extra dependency).
- Keep all dashboard code strictly read-only against simulation state except through the explicit Fault Injection interface — reinforces the architecture's separation of concerns and is worth mentioning in an interview as a deliberate design choice.
