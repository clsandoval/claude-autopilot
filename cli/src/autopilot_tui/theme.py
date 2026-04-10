"""Claude warm-cream theme for Autopilot TUI."""

from textual.theme import Theme

AUTOPILOT_THEME = Theme(
    name="autopilot",
    primary="#C17A4A",      # orange accent
    secondary="#6B6560",    # muted brown
    warning="#D4874A",
    error="#B85C5C",
    success="#7D9B76",
    accent="#C17A4A",
    foreground="#2D2B28",   # dark brown text
    background="#FAF7F2",   # warm cream
    surface="#F0EBE3",      # slightly darker cream
    panel="#E5DFD6",        # border/divider color
    dark=False,
)

THEME_CSS = """
#left-panel {
    width: 34%;
    border-right: solid $panel;
}

#right-bottom {
    height: 18;
    border-top: solid $panel;
}

.panel-title {
    background: $surface;
    color: $secondary;
    padding: 0 2;
    border-bottom: solid $panel;
    text-style: bold;
}

.session-name {
    text-style: bold;
}

.session-meta {
    color: $secondary;
}

.status-running {
    color: $success;
}

.status-blocked {
    color: $warning;
}

.status-done {
    color: $secondary;
}

.status-error {
    color: $error;
}
"""
