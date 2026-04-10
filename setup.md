# Autopilot — One-Time Setup

This document handles one-time infrastructure setup. It creates a persistent environment and optional vault. Agent creation is NOT done here — agents are created per-job during dispatch.

---

## Loading Existing Config

Check if setup has already been completed:

```bash
cat .superpowers/autopilot-config.json 2>/dev/null
```

If the file exists and contains a valid `environment_id`, setup is complete. Skip to Verification.

---

## Prerequisites Check

```bash
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set."
  echo "Source .env or export it directly."
  exit 1
fi
echo "Prerequisites check passed."
```

---

## Step 1: Create Environment

```bash
ENV_RESPONSE=$(curl -sS https://api.anthropic.com/v1/environments \
  -X POST \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "anthropic-beta: managed-agents-2026-04-01" \
  -H "content-type: application/json" \
  -d '{
    "name": "autopilot-env",
    "config": {
      "type": "cloud",
      "networking": {"type": "unrestricted"}
    }
  }')

# Handle 409 conflict
ENV_STATUS=$(echo "$ENV_RESPONSE" | jq -r '.type // "success"')
if [ "$ENV_STATUS" = "error" ]; then
  ERROR_TYPE=$(echo "$ENV_RESPONSE" | jq -r '.error.type // ""')
  if [ "$ERROR_TYPE" = "conflict_error" ]; then
    ENV_RESPONSE=$(curl -sS "https://api.anthropic.com/v1/environments?name=autopilot-env" \
      -H "x-api-key: $ANTHROPIC_API_KEY" \
      -H "anthropic-version: 2023-06-01" \
      -H "anthropic-beta: managed-agents-2026-04-01")
  else
    echo "ERROR: $(echo "$ENV_RESPONSE" | jq -r '.error.message')"
    exit 1
  fi
fi

ENVIRONMENT_ID=$(echo "$ENV_RESPONSE" | jq -r '.id // .data[0].id')
echo "Environment ID: $ENVIRONMENT_ID"
```

---

## Step 2: Create Vault (Optional)

Only if GITHUB_TOKEN is available. Stores GitHub credential for repo access.

```bash
VAULT_ID=""

if [ -n "$GITHUB_TOKEN" ]; then
  VAULT_RESPONSE=$(curl -sS https://api.anthropic.com/v1/vaults \
    -X POST \
    -H "x-api-key: $ANTHROPIC_API_KEY" \
    -H "anthropic-version: 2023-06-01" \
    -H "anthropic-beta: managed-agents-2026-04-01" \
    -H "content-type: application/json" \
    -d '{"display_name": "autopilot-vault"}')

  VAULT_ID=$(echo "$VAULT_RESPONSE" | jq -r '.id')

  if [ -n "$VAULT_ID" ] && [ "$VAULT_ID" != "null" ]; then
    echo "Vault ID: $VAULT_ID"
  else
    echo "WARNING: Vault creation failed. Continuing without vault."
    VAULT_ID=""
  fi
else
  echo "GITHUB_TOKEN not set — skipping vault creation."
fi
```

---

## Step 3: Save Config

```bash
mkdir -p .superpowers

CONFIG=$(jq -n \
  --arg environment_id "$ENVIRONMENT_ID" \
  --arg vault_id "${VAULT_ID:-}" \
  --arg setup_completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
    environment_id: $environment_id,
    vault_id: (if $vault_id == "" then null else $vault_id end),
    setup_completed_at: $setup_completed_at
  }')

echo "$CONFIG" > .superpowers/autopilot-config.json
echo "Config saved."
```

Ensure gitignored:
```bash
for f in "autopilot-config.json" "autopilot-sessions.json"; do
  grep -q "$f" .gitignore 2>/dev/null || echo ".superpowers/$f" >> .gitignore
done
```

Initialize sessions file:
```bash
[ -f .superpowers/autopilot-sessions.json ] || echo '{"sessions": []}' > .superpowers/autopilot-sessions.json
```

---

## Verification

```bash
echo "Setup complete."
echo "  Environment: $ENVIRONMENT_ID"
if [ -n "$VAULT_ID" ]; then
  echo "  Vault:       $VAULT_ID"
else
  echo "  Vault:       (not configured)"
fi
echo ""
echo "Agents are created per-job during dispatch."
```
