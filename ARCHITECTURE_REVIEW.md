# Architecture review

The original design has the right core invariant—Markdown is the durable boundary—but needs a few safeguards before it becomes long-running infrastructure:

- **Do not let collectors write the Vault.** `obsidian-helper` is the only component with Vault write access. Collectors should send authenticated HTTP requests.
- **Avoid accidental duplicates.** The service treats identical title/folder/content as idempotent and adds a content-hash suffix when the same title contains different content. A future queue can use `idempotency_key` for stronger delivery guarantees.
- **Never trust folder names.** Folder paths are normalized and checked after resolution, so `../` cannot escape the Vault. Filenames are sanitized for common Windows/Linux invalid characters.
- **Prevent partial files.** Notes are written to a same-directory temporary file, flushed and fsynced, then atomically replaced. This is safer for iCloud/Syncthing watchers.
- **Keep classification bounded.** AI may suggest a folder and tags, but the processor should validate folders against an allow-list and normalize tags before sending the note. Do not let an LLM create arbitrary top-level directories.
- **Treat sync as replication, not backup.** iCloud/Syncthing can propagate deletions and conflicts. Add a versioned backup/snapshot policy outside the Vault before relying on sync.
- **Keep the API private.** Compose binds it to localhost. Put HTTPS/authenticated reverse proxy access in front only if remote clients are actually needed.

The implementation in `src/obsidian_helper` is intentionally stateless. Telegram, RSS, browser and PDF adapters can all target the same API. A durable queue and an attachment store should be added before high-volume ingestion; do not use the Vault itself as a work queue.
