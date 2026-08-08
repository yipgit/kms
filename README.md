# Personal Content Infrastructure

个人知识基础设施：输入源负责收集，AI 负责处理，`obsidian-helper` 负责把结构化 Markdown 安全写入 Obsidian Vault。

## Components

- `src/obsidian_helper`: FastAPI Markdown service; the only Vault writer.
- `src/pipeline` and `src/adapters/telegram_bot.py`: existing Telegram collector and enrichment pipeline.
- `Dockerfile.helper`: small runtime image for the Markdown service.
- `systemd/obsidian-helper.service`: Linux non-Docker deployment unit.
- `ARCHITECTURE_REVIEW.md`: design review and long-term risks.

## API

Run the service with `OBSIDIAN_HELPER_API_TOKEN` and `VAULT_PATH` configured:

```bash
uvicorn src.obsidian_helper.main:app --host 127.0.0.1 --port 8080
```

```bash
curl -X POST http://127.0.0.1:8080/api/v1/note \
  -H 'Authorization: Bearer YOUR_TOKEN' -H 'Content-Type: application/json' \
  -d '{"title":"GCP IAM权限继承","folder":"Technology/GCP","tags":["GCP","IAM"],"summary":"权限继承规则","source":["ChatGPT"],"content":"正文"}'
```

`GET /healthz` is intentionally unauthenticated for Docker/systemd health checks. Note writes require a Bearer token or `X-API-Token`. Repeated identical writes return the existing file; changed content with the same title gets a short hash suffix.

Folder management is also available to authenticated clients:

```text
GET  /api/v1/folders
POST /api/v1/folders       {"folder":"History/Geopolitics"}
POST /api/v1/note/move     {"file":"Inbox/note.md","folder":"History"}
```

In Telegram, press `Move To...` on a saved note to load folders from `obsidian-helper`. Choose `Create folder`, then send the folder path as the next message. For direct routing, include a line such as `target: Technology/GCP` in the captured message; the helper creates missing parent folders safely.

## Docker

Copy `.env.example` to `.env`, set `HOST_VAULT_PATH` and a random `OBSIDIAN_HELPER_API_TOKEN`, then run:

```bash
docker compose up -d obsidian-helper telegram-collector
docker compose logs -f obsidian-helper
```

The API is bound to `127.0.0.1` only. The `ai-processor` profile is a reserved boundary for a future queue-backed worker: `docker compose --profile future up -d` starts its placeholder process, but it does not yet process data.

## systemd

Create `/etc/personal-content/obsidian-helper.env` with `VAULT_PATH`, `OBSIDIAN_HELPER_API_TOKEN`, and optionally host/port. Install the unit, adjust the `User`, paths and Vault permissions, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now obsidian-helper
sudo journalctl -u obsidian-helper -f
```

For production, put Caddy/Nginx in front for HTTPS and keep Uvicorn on localhost. Do not expose the service directly to the public internet.

## Tests

```bash
pytest -q
```

The tests cover the existing collector pipeline plus API authentication, idempotency and traversal protection.
