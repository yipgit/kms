import re
import httpx
import logging
import html
import json
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse
from src.pipeline.core import PipelineStep
from src.domain.models import RawMessage, Content, Note
from src.adapters.filesystem import FilesystemWriter
from src.adapters.llm import LLMProvider
from src.adapters.tag_repository import TagRepository

logger = logging.getLogger(__name__)

class RawMessageToContent(PipelineStep):
    """Transforms a RawMessage into a Content object."""
    
    async def process(self, data: RawMessage) -> Content:
        text = data.text or ""
        # Simple URL extraction (first URL found)
        url_match = re.search(r'(https?://\S+)', text)
        source_url = url_match.group(0) if url_match else None
        
        # Extract hashtags
        tags = re.findall(r'#(\w+)', text)
        
        # Use first line as title if available and not a URL, else date
        lines = text.strip().split('\n')
        first_line = lines[0].strip() if lines else ""
        
        # If first line is strictly a URL, don't use it as a title; let FetchURLContent find a better one
        if first_line and re.match(r'^https?://\S+$', first_line):
            title = f"Note {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        else:
            # Strip "Title: " prefix if present
            clean_title = re.sub(r'^Title:\s*', '', first_line, flags=re.IGNORECASE).strip()
            title = clean_title[:100] if clean_title else f"Note {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        content = Content(
            source_url=source_url,
            title=title,
            body=text,
            tags=tags,
            created_at=data.date,
            metadata={
                "original_message_id": data.message_id,
                "forward_from": data.forward_from
            }
        )
        target_match = re.search(r'target:\s*(.+?)(?:\s+#|$)', text, re.IGNORECASE)
        if target_match:
            content.metadata["target_folder"] = target_match.group(1).strip().strip("/\\")
        return content

class FetchURLContent(PipelineStep):
    """Fetches the content of the source URL if present."""
    
    def __init__(self, proxy_url: Optional[str] = None):
        self.proxy_url = proxy_url

    @staticmethod
    def _x_status_id(url: str) -> Optional[str]:
        """Return the status ID for an X/Twitter post URL, if present."""
        hostname = (urlparse(url).hostname or "").lower()
        if hostname not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
            return None

        match = re.search(r"/(?:i/)?status/(\d+)", urlparse(url).path)
        return match.group(1) if match else None

    @staticmethod
    def _is_xiaohongshu_url(url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return hostname in {
            "xhslink.com",
            "www.xhslink.com",
            "xiaohongshu.com",
            "www.xiaohongshu.com",
        }

    @staticmethod
    def _extract_xiaohongshu_article(page: str) -> Optional[dict]:
        """Read the public JSON-LD Article embedded in a Xiaohongshu share page."""
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        for match in re.finditer(pattern, page, flags=re.IGNORECASE | re.DOTALL):
            try:
                article = json.loads(html.unescape(match.group(1)))
            except json.JSONDecodeError:
                continue
            if not isinstance(article, dict) or article.get("@type") != "Article":
                continue
            description = str(article.get("description") or "").strip()
            if description:
                return article
        return None
        
    async def process(self, data: Content) -> Content:
        if not data.source_url:
            return data
        headers = {
            "User-Agent": "Discordbot/2.0; +https://discordapp.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Xiaohongshu publishes note details as JSON-LD in public share pages,
        # while reader services commonly receive only the login shell.
        if self._is_xiaohongshu_url(data.source_url):
            logger.info(f"Attempting Xiaohongshu share-page extraction: {data.source_url}")
            try:
                async with httpx.AsyncClient(proxy=self.proxy_url, follow_redirects=True, timeout=30.0, headers=headers) as client:
                    response = await client.get(data.source_url)
                    response.raise_for_status()
                article = self._extract_xiaohongshu_article(response.text)
                if article:
                    headline = str(article.get("headline") or "").strip()
                    if headline and data.title.startswith("Note "):
                        data.title = re.sub(r"\s*-\s*小红书$", "", headline).strip()
                    author = article.get("author")
                    if isinstance(author, dict) and author.get("name"):
                        data.metadata["author"] = str(author["name"])
                    images = article.get("image")
                    if isinstance(images, list):
                        data.metadata["image_count"] = len(images)
                    data.body = str(article["description"]).strip()
                    return data
                logger.warning(f"Xiaohongshu share page did not contain a usable JSON-LD article: {data.source_url}")
            except Exception as e:
                logger.warning(f"Xiaohongshu share-page extraction failed for {data.source_url}: {e}")

        # X often blocks readers or returns a login page.  Fetch the public JSON
        # representation first, before accepting a nominally successful reader response.
        status_id = self._x_status_id(data.source_url)
        if status_id:
            api_url = f"https://api.vxtwitter.com/i/status/{status_id}"
            logger.info(f"Attempting X.com JSON API extraction: {api_url}")
            try:
                async with httpx.AsyncClient(proxy=self.proxy_url, follow_redirects=True, timeout=20.0, headers=headers) as client:
                    response = await client.get(api_url)
                    response.raise_for_status()
                    tweet_data = response.json()
                    text = (tweet_data.get("text") or "").strip()
                    if not text:
                        raise ValueError("X.com JSON API response did not contain post text")

                    user = tweet_data.get("user_screen_name") or tweet_data.get("user_name") or "Unknown"
                    snippet = text.replace("\n", " ")[:50].strip()
                    if len(text.replace("\n", " ").strip()) > 50:
                        snippet += "..."
                    data.title = f'{user} on X: "{snippet}"'
                    data.metadata["author"] = user
                    data.body = text
                    return data
            except Exception as e:
                logger.warning(f"X.com JSON API failed for {data.source_url}: {e}")

        # 1. Primary: Jina Reader
        target_url = f"https://r.jina.ai/{data.source_url}"
        logger.info(f"Attempting clean extraction via Jina Reader: {target_url}")

        try:
            async with httpx.AsyncClient(proxy=self.proxy_url, follow_redirects=True, timeout=30.0, headers=headers) as client:
                response = await client.get(target_url)
                response.raise_for_status()
                
                content_text = response.text
                
                # Look for "Title: " prefix which is common in Jina / some readers
                title_match = re.search(r'^Title:\s*(.*)$', content_text, re.MULTILINE)
                if title_match:
                    data.title = title_match.group(1).strip()
                    # Remove the Title line from body to avoid duplication
                    content_text = re.sub(r'^Title:\s*.*\n?', '', content_text, flags=re.MULTILINE)
                elif content_text.startswith("# "):
                    first_line = content_text.split("\n", 1)[0]
                    data.title = first_line.lstrip("# ").strip()
                
                data.body = content_text.strip()
                return data

        except Exception as e:
            logger.warning(f"Jina Reader failed for {data.source_url}: {e}")

        # 2. Last Resort: Direct Fetch with Meta-tag Extraction
        logger.info(f"Attempting direct fetch fallback: {data.source_url}")
        try:
            async with httpx.AsyncClient(proxy=self.proxy_url, follow_redirects=True, timeout=15.0, headers=headers) as client:
                response = await client.get(data.source_url)
                response.raise_for_status()
                content_text = response.text
                
                if data.title.startswith("Note "):
                    title_match = re.search(r'<title>(.*?)</title>', content_text, re.IGNORECASE | re.DOTALL)
                    if title_match:
                        data.title = title_match.group(1).strip()
                
                desc_match = re.search(r'<meta (?:property|name)="og:description" content="(.*?)"', content_text, re.IGNORECASE)
                if not desc_match:
                    desc_match = re.search(r'<meta (?:property|name)="twitter:description" content="(.*?)"', content_text, re.IGNORECASE)
                
                if desc_match:
                    data.body = desc_match.group(1).strip()
                    data.metadata["description"] = data.body
                else:
                    data.body = "Failed to extract clean text. Raw HTML returned."
        except Exception as e:
            logger.error(f"All fetch attempts failed for {data.source_url}: {e}")
            data.body = f"Error fetching URL content: {str(e)}"
            
        return data


class EnrichContent(PipelineStep):
    """Optionally generate an abstract, tags, and key points via an LLM provider."""

    def __init__(self, provider: LLMProvider, tag_repo: TagRepository):
        self.provider = provider
        self.tag_repo = tag_repo

    async def process(self, data: Content) -> Content:
        enrichment = await self.provider.enrich(data, self.tag_repo.get_top_tags(50))
        data.enrichment = enrichment
        data.tags = list(dict.fromkeys([*data.tags, *enrichment.tags]))
        if data.title and data.title.startswith("Note ") and enrichment.suggested_title:
            data.title = enrichment.suggested_title[:100]
        return data

class ContentToNote(PipelineStep):
    """Transforms Content into a Note object (Obsidian Clipper Format)."""
    
    async def process(self, data: Content) -> Note:
        # 1. Generate YAML Frontmatter
        frontmatter = []
        frontmatter.append("---")
        frontmatter.append(f"title: \"{data.title.replace('\"', '\\\"')}\"")
        if data.source_url:
            frontmatter.append(f"source: {data.source_url}")
        
        frontmatter.append(f"created: {data.created_at.strftime('%Y-%m-%dT%H:%M:%S')}")
        
        # Add tags as a YAML list
        if data.tags:
            frontmatter.append("tags:")
            for tag in data.tags:
                frontmatter.append(f"  - {tag}")

        if data.enrichment:
            if data.enrichment.categories:
                frontmatter.append("categories:")
                for category in data.enrichment.categories:
                    frontmatter.append(f"  - {category}")
            if data.enrichment.provider:
                frontmatter.append(f"llm_provider: {data.enrichment.provider}")
            if data.enrichment.model:
                frontmatter.append(f"llm_model: {data.enrichment.model}")
            frontmatter.append(f"llm_prompt_version: {data.enrichment.prompt_version}")
        
        # Append other metadata as properties
        for key, value in data.metadata.items():
            if key not in ["original_message_id", "forward_from"]:
                frontmatter.append(f"{key}: \"{str(value).replace('\"', '\\\"')}\"")
        
        # Internal bot metadata kept for reference
        if data.metadata.get("forward_from"):
            frontmatter.append(f"forwarded_from: \"{data.metadata['forward_from']}\"")
            
        frontmatter.append("---")
        frontmatter.append("")
        
        # 2. Build Markdown Body
        lines = frontmatter
        lines.append(f"# {data.title}")
        lines.append("")

        if data.enrichment:
            lines.append("## Abstract")
            lines.append("")
            lines.append(data.enrichment.abstract)
            lines.append("")
            if data.enrichment.key_points:
                lines.append("## Key points")
                lines.append("")
                lines.extend(f"- {point}" for point in data.enrichment.key_points)
                lines.append("")
            lines.append("## Source content")
            lines.append("")
        
        # If the body is from a cleaner (like vxtwitter), it might not have the header or source
        # but the frontmatter already has them.
        lines.append(data.body)
        lines.append("")
        
        content_str = "\n".join(lines)
        
        # Truncate filename for filesystem safety
        filename = data.title[:200] if data.title else "Untitled"
        
        return Note(
            filename=filename,
            content=content_str,
            summary=data.enrichment.abstract if data.enrichment else None,
            tags=data.tags,
            path=str(data.metadata.get("target_folder") or ""),
        )

class SaveNote(PipelineStep):
    """Saves the Note to the filesystem."""
    
    def __init__(self, writer: FilesystemWriter):
        self.writer = writer
        
    async def process(self, data: Note) -> Note:
        path = await self.writer.write_note(data)
        data.absolute_path = path
        return data
