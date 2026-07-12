# Windows Codex bridge

Use this bridge when `kms-bot` runs in Docker but Codex CLI is installed and
authenticated on Windows. The bot sends only enrichment requests to the host;
the bridge runs a fixed, read-only `codex exec` command in a temporary folder.

## 1. Start the bridge in Windows PowerShell

```powershell
cd D:\code\kms
$env:CODEX_BRIDGE_TOKEN = "generate-a-long-random-secret"
python host_bridge\codex_bridge.py
```

The bridge automatically prefers `%APPDATA%\npm\codex.cmd`, where the Windows
npm installation places Codex. Set `CODEX_COMMAND` only if you installed the
CLI elsewhere.

The bridge listens on port `8765`. Keep it on the Windows host, and do not
publish that port through a router or public firewall rule.

## 2. Configure the Docker bot `.env`

```env
LLM_ENABLED=true
LLM_PROVIDER=codex-bridge
CODEX_BRIDGE_URL=http://host.docker.internal:8765
CODEX_BRIDGE_TOKEN=the-same-long-random-secret
CODEX_TIMEOUT_SECONDS=120
```

`docker-compose.yml` already maps `host.docker.internal` to the host gateway.
Restart the bot after editing the `.env` file:

```powershell
docker compose up -d --build --force-recreate
```
