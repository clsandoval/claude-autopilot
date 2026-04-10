"""Claude light-mode theme for Autopilot TUI."""

THEME_CSS = """
/* ── Palette ───────────────────────────────────────────────── */
$bg:           #FAF7F2;
$surface:      #F0EBE3;
$border:       #E5DFD6;
$text:         #2D2B28;
$text-sec:     #6B6560;
$muted:        #A89F95;
$text-dim:     #BDB5AB;
$accent:       #C17A4A;
$warning:      #D4874A;
$success:      #7D9B76;
$error:        #B85C5C;

/* ── App shell ─────────────────────────────────────────────── */
Screen {
    background: $bg;
    color: $text;
}

/* ── Panels ────────────────────────────────────────────────── */
#left-panel {
    width: 34%;
    background: $surface;
    border-right: solid $border;
}

#right-top {
    background: $bg;
}

#right-bottom {
    height: 18;
    background: $surface;
    border-top: solid $border;
}

/* ── Tab bar ───────────────────────────────────────────────── */
TabbedContent {
    background: $bg;
}

TabbedContent ContentSwitcher {
    background: $bg;
}

Tabs {
    background: $surface;
    border-bottom: solid $border;
}

Tab {
    color: $text-sec;
    background: $surface;
}

Tab.-active {
    color: $accent;
    background: $bg;
    border-bottom: solid $accent;
}

Tab:hover {
    color: $text;
    background: $bg;
}

/* ── Session list ──────────────────────────────────────────── */
#session-list {
    background: $surface;
    padding: 0;
}

.session-item {
    padding: 1 2;
    border-bottom: solid $border;
    color: $text;
}

.session-item:hover {
    background: $bg;
}

.session-item.--selected {
    background: $bg;
    border-left: thick $accent;
}

.status-running {
    color: $success;
}

.status-blocked {
    color: $warning;
}

.status-done {
    color: $muted;
}

.status-error {
    color: $error;
}

.session-name {
    color: $text;
    text-style: bold;
}

.session-meta {
    color: $text-sec;
}

/* ── Panel titles ──────────────────────────────────────────── */
.panel-title {
    background: $surface;
    color: $text-sec;
    padding: 0 2;
    border-bottom: solid $border;
    text-style: bold;
}

/* ── Progress tab ──────────────────────────────────────────── */
#progress-content {
    padding: 1 2;
    overflow-y: auto;
}

.phase-complete {
    color: $success;
}

.phase-active {
    color: $accent;
}

.phase-pending {
    color: $muted;
}

.section-header {
    color: $text-sec;
    text-style: bold;
    margin-top: 1;
    border-bottom: solid $border;
}

.decision-item {
    color: $text;
    margin-left: 2;
}

.decision-time {
    color: $muted;
}

.usage-label {
    color: $text-sec;
}

.usage-value {
    color: $text;
}

/* ── Artifacts tab ─────────────────────────────────────────── */
#artifacts-content {
    padding: 1 2;
    overflow-y: auto;
}

.artifact-item {
    color: $text;
    margin-bottom: 0;
}

.artifact-time {
    color: $muted;
}

.empty-state {
    color: $muted;
    padding: 2;
}

/* ── Question tab ──────────────────────────────────────────── */
#question-content {
    padding: 1 2;
    overflow-y: auto;
}

.question-text {
    color: $text;
    text-style: bold;
    margin-bottom: 1;
}

.question-context {
    color: $text-sec;
    margin-bottom: 1;
}

.option-card {
    background: $surface;
    border: solid $border;
    padding: 0 1;
    margin-bottom: 0;
    color: $text;
}

.option-card:hover {
    border: solid $accent;
    color: $accent;
}

.option-card.--selected {
    border: solid $accent;
    background: $bg;
    color: $accent;
}

.option-label {
    color: $accent;
    text-style: bold;
}

/* ── Events stream ─────────────────────────────────────────── */
#events-log {
    padding: 0 1;
    overflow-y: auto;
    background: $surface;
}

.event-line {
    color: $text-sec;
}

.event-phase {
    color: $success;
    text-style: bold;
}

.event-question {
    color: $warning;
    text-style: bold;
}

.event-time {
    color: $muted;
}

/* ── Answer input ──────────────────────────────────────────── */
#answer-input {
    background: $surface;
    border-top: solid $border;
    border: solid $border;
    color: $text;
    padding: 0 1;
}

#answer-input:focus {
    border: solid $accent;
}

/* ── Buttons ───────────────────────────────────────────────── */
Button {
    background: $surface;
    border: solid $border;
    color: $text;
}

Button:hover {
    background: $bg;
    border: solid $accent;
    color: $accent;
}

Button.-primary {
    background: $accent;
    color: $bg;
    border: solid $accent;
}

Button.-primary:hover {
    background: $warning;
    border: solid $warning;
}

/* ── Scrollbar ─────────────────────────────────────────────── */
ScrollBar {
    background: $surface;
}

ScrollBar > .scrollbar--bar {
    color: $border;
    background: $border;
}

ScrollBar > .scrollbar--bar:hover {
    color: $muted;
    background: $muted;
}

/* ── Footer ────────────────────────────────────────────────── */
Footer {
    background: $surface;
    color: $text-sec;
    border-top: solid $border;
}

/* ── Dialog / overlay ──────────────────────────────────────── */
ModalScreen {
    background: rgba(0, 0, 0, 0.4);
}

#dialog {
    background: $bg;
    border: solid $border;
    padding: 2 4;
    width: 60;
    height: auto;
}

#dialog-title {
    text-style: bold;
    color: $text;
    margin-bottom: 1;
}

#dialog-message {
    color: $text-sec;
    margin-bottom: 2;
}

#dialog-buttons {
    layout: horizontal;
    align: right middle;
    height: auto;
}
"""
