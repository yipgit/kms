import unittest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.adapters.llm import CodexCLIProvider, LLMProvider, OpenAIProvider
from src.adapters.tag_repository import TagRepository
from src.domain.models import Content, Enrichment
from src.pipeline.processors import ContentToNote, EnrichContent


class FakeProvider(LLMProvider):
    async def enrich(self, content, known_tags):
        self.content = content
        self.known_tags = known_tags
        return Enrichment(
            abstract="A concise description of the source.",
            key_points=["First fact", "Second fact"],
            tags=["machine-learning", "research"],
            categories=["technology"],
            suggested_title="Generated title",
            provider="fake",
            model="fake-model",
        )


class TestEnrichment(unittest.IsolatedAsyncioTestCase):
    async def test_codex_cli_provider_uses_isolated_read_only_exec(self):
        process = MagicMock()
        process.returncode = 0
        process.communicate = AsyncMock(return_value=(
            b'{"abstract":"Summary","key_points":["Fact"],"tags":["AI"],"categories":[],"suggested_title":null}',
            b"",
        ))
        with patch("src.adapters.llm.asyncio.create_subprocess_exec", new_callable=AsyncMock) as create_process:
            create_process.return_value = process
            result = await CodexCLIProvider(command="codex", timeout=10).enrich(
                Content(title="Original", body="Source text"), ["research"]
            )

        self.assertEqual(result.provider, "codex-cli")
        self.assertEqual(result.tags, ["ai"])
        command = create_process.call_args.args
        self.assertEqual(command[:2], ("codex", "exec"))
        self.assertIn("--ephemeral", command)
        self.assertIn("read-only", command)
        self.assertIn("--ignore-user-config", command)
        self.assertIn("--ignore-rules", command)

    async def test_openai_provider_requests_and_parses_strict_json_schema(self):
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            "choices": [{"message": {"content": '{"abstract":"Summary","key_points":["Fact"],"tags":["AI Research"],"categories":["Technology"],"suggested_title":"Better title"}'}}]
        }
        with patch("src.adapters.llm.httpx.AsyncClient") as client_cls:
            client = client_cls.return_value.__aenter__.return_value
            client.post = AsyncMock(return_value=response)
            provider = OpenAIProvider(api_key="test-key", model="test-model")

            result = await provider.enrich(Content(title="Original", body="Source text"), ["research"])

        self.assertEqual(result.abstract, "Summary")
        self.assertEqual(result.tags, ["ai-research"])
        self.assertEqual(result.suggested_title, "Better title")
        request = client.post.call_args.kwargs["json"]
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertTrue(request["response_format"]["json_schema"]["strict"])

    async def test_enrichment_merges_tags_and_replaces_generated_title(self):
        provider = FakeProvider()
        repository = TagRepository("nonexistent-tags.json")
        repository._tags = {"research": 3}
        content = Content(
            title="Note 2026-07-12 10:00",
            body="Source text",
            tags=["manual"],
            created_at=datetime(2026, 7, 12, 10, 0),
        )

        result = await EnrichContent(provider, repository).process(content)

        self.assertEqual(result.title, "Generated title")
        self.assertEqual(result.tags, ["manual", "machine-learning", "research"])
        self.assertEqual(provider.known_tags, ["research"])

    async def test_note_renders_enrichment_without_replacing_source_text(self):
        content = Content(
            title="My note",
            body="Original source text",
            enrichment=Enrichment(
                abstract="A factual abstract.",
                key_points=["Important detail"],
                categories=["research"],
                provider="fake",
                model="fake-model",
            ),
        )

        note = await ContentToNote().process(content)

        self.assertIn("## Abstract", note.content)
        self.assertIn("A factual abstract.", note.content)
        self.assertIn("## Key points", note.content)
        self.assertIn("- Important detail", note.content)
        self.assertIn("## Source content", note.content)
        self.assertIn("Original source text", note.content)
        self.assertIn("categories:\n  - research", note.content)
        self.assertIn("llm_provider: fake", note.content)
        self.assertIn("llm_model: fake-model", note.content)
