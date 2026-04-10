"""Claude light-mode theme for Autopilot TUI — uses inline hex colors."""

THEME_CSS = """
Screen {
    background: #FAF7F2;
    color: #2D2B28;
}

#left-panel {
    width: 34%;
    background: #F0EBE3;
    border-right: solid #E5DFD6;
}

#right-top {
    background: #FAF7F2;
}

#right-bottom {
    height: 18;
    background: #F0EBE3;
    border-top: solid #E5DFD6;
}

TabbedContent {
    background: #FAF7F2;
}

TabbedContent ContentSwitcher {
    background: #FAF7F2;
}

Tabs {
    background: #F0EBE3;
    border-bottom: solid #E5DFD6;
}

Tab {
    color: #6B6560;
    background: #F0EBE3;
}

Tab.-active {
    color: #C17A4A;
    background: #FAF7F2;
    border-bottom: solid #C17A4A;
}

Tab:hover {
    color: #2D2B28;
    background: #FAF7F2;
}

#session-list {
    background: #F0EBE3;
    padding: 0;
}

.session-item {
    padding: 1 2;
    border-bottom: solid #E5DFD6;
    color: #2D2B28;
}

.session-item:hover {
    background: #FAF7F2;
}

.session-item.--selected {
    background: #FAF7F2;
    border-left: thick #C17A4A;
}

.status-running {
    color: #7D9B76;
}

.status-blocked {
    color: #D4874A;
}

.status-done {
    color: #A89F95;
}

.status-error {
    color: #B85C5C;
}

.session-name {
    color: #2D2B28;
    text-style: bold;
}

.session-meta {
    color: #6B6560;
}

.panel-title {
    background: #F0EBE3;
    color: #6B6560;
    padding: 0 2;
    border-bottom: solid #E5DFD6;
    text-style: bold;
}

#progress-content {
    padding: 1 2;
    overflow-y: auto;
}

.phase-complete {
    color: #7D9B76;
}

.phase-active {
    color: #C17A4A;
}

.phase-pending {
    color: #A89F95;
}

.section-header {
    color: #6B6560;
    text-style: bold;
    margin-top: 1;
    border-bottom: solid #E5DFD6;
}

.decision-item {
    color: #2D2B28;
    margin-left: 2;
}

.decision-time {
    color: #A89F95;
}

.usage-label {
    color: #6B6560;
}

.usage-value {
    color: #2D2B28;
}

#artifacts-content {
    padding: 1 2;
    overflow-y: auto;
}

.artifact-item {
    color: #2D2B28;
    margin-bottom: 0;
}

.artifact-time {
    color: #A89F95;
}

.empty-state {
    color: #A89F95;
    padding: 2;
}

#question-content {
    padding: 1 2;
    overflow-y: auto;
}

.question-text {
    color: #2D2B28;
    text-style: bold;
    margin-bottom: 1;
}

.question-context {
    color: #6B6560;
    margin-bottom: 1;
}

.option-card {
    background: #F0EBE3;
    border: solid #E5DFD6;
    padding: 0 1;
    margin-bottom: 0;
    color: #2D2B28;
}

.option-card:hover {
    border: solid #C17A4A;
    color: #C17A4A;
}

.option-card.--selected {
    border: solid #C17A4A;
    background: #FAF7F2;
    color: #C17A4A;
}

.option-label {
    color: #C17A4A;
    text-style: bold;
}

#events-log {
    padding: 0 1;
    overflow-y: auto;
    background: #F0EBE3;
}

.event-line {
    color: #6B6560;
}

.event-phase {
    color: #7D9B76;
    text-style: bold;
}

.event-question {
    color: #D4874A;
    text-style: bold;
}

.event-time {
    color: #A89F95;
}

#answer-input {
    background: #F0EBE3;
    border: solid #E5DFD6;
    color: #2D2B28;
    padding: 0 1;
}

#answer-input:focus {
    border: solid #C17A4A;
}

Button {
    background: #F0EBE3;
    border: solid #E5DFD6;
    color: #2D2B28;
}

Button:hover {
    background: #FAF7F2;
    border: solid #C17A4A;
    color: #C17A4A;
}

Button.-primary {
    background: #C17A4A;
    color: #FAF7F2;
    border: solid #C17A4A;
}

Button.-primary:hover {
    background: #D4874A;
    border: solid #D4874A;
}

ScrollBar {
    background: #F0EBE3;
}

ScrollBar > .scrollbar--bar {
    color: #E5DFD6;
}

ScrollBar > .scrollbar--bar:hover {
    color: #A89F95;
}

Footer {
    background: #F0EBE3;
    color: #6B6560;
    border-top: solid #E5DFD6;
}

ModalScreen {
    background: rgba(0, 0, 0, 0.4);
}

#dialog {
    background: #FAF7F2;
    border: solid #E5DFD6;
    padding: 2 4;
    width: 60;
    height: auto;
}

#dialog-title {
    text-style: bold;
    color: #2D2B28;
    margin-bottom: 1;
}

#dialog-message {
    color: #6B6560;
    margin-bottom: 2;
}

#dialog-buttons {
    layout: horizontal;
    align: right middle;
    height: auto;
}
"""
