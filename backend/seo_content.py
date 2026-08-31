#!/usr/bin/env python3
# [Input] Consume public frontend/backend URL values, curated knowledge links, and public crawler requests.
# [Output] Generate SEO metadata content for robots.txt, sitemap.xml, and llms.txt with public knowledge references.
# [Pos] backend SEO content helper
# [Sync] 2026-06-14: created for Codex SEO optimized crawler and AI-search content.
# [Sync] 2026-06-14: split frontend app URL from backend API origin for llms.txt.
# [Sync] 2026-06-15: remove /ink-and-memory public app prefix from crawler policies.
# [Sync] 2026-08-31: add the latest bilingual connector essay and descriptive blog/knowledge-base links to llms.txt.
# [Sync] 2026-08-31: remove the retired /polycli path from crawler policy.
"""SEO content generators for public crawler and AI-search discovery files."""

from __future__ import annotations

from datetime import date
from urllib.parse import urljoin, urlsplit, urlunsplit
from xml.sax.saxutils import escape as xml_escape

APP_NAME = "Ink & Memory"
APP_TAGLINE = "Write. Reflect. Listen to the voices within."
APP_DESCRIPTION = (
    "Ink & Memory is a bilingual AI journaling studio for reflective writing, "
    "inner voice feedback, visual memory timelines, and personal pattern discovery."
)
APP_KEYWORDS = (
    "AI journaling",
    "reflective writing",
    "bilingual journal",
    "personal knowledge",
    "inner voice feedback",
    "visual diary",
    "memory timeline",
)

BLOG_AND_KNOWLEDGE_BASE_LINKS = (
    ("Blog index", "https://suoxya.com/blog/"),
    (
        "English article — Lecture Notes | When Connectors Enter the Agent Workspace: "
        "Boundaries of State, Trust, and Action",
        "https://medium.com/@glide-the/lecture-notes-when-connectors-enter-the-agent-workspace-boundaries-of-state-trust-and-action-e13fc6839b99",
    ),
    (
        "Chinese article — 讲义｜连接器进入 Agent 工作空间之后：状态、信任与动作的边界",
        "https://mp.weixin.qq.com/s/N8guDNouFjWClKXHmWQo-A",
    ),
    (
        "Article page — Workspace 工作空间状态管理与交互入口设计",
        "https://suoxya.com/blog/workspace-state-management/",
    ),
    (
        "Chinese original — Workspace 工作空间状态管理与交互入口设计",
        "https://mp.weixin.qq.com/s/RIdUu6gs3FlJI6tzRPEphA",
    ),
    (
        "Article page — How Does an AI Know What You Are Writing?",
        "https://suoxya.com/blog/how-does-an-ai-know-what-you-are-writing/",
    ),
    (
        "English original — How Does an AI Know What You Are Writing?",
        "https://medium.com/@glide-the/how-does-an-ai-know-what-you-are-writing-b545edbfe8b2",
    ),
)

PUBLIC_APP_PATHS = (
    (
        "",
        "Ink & Memory app homepage for AI-assisted journaling and self-reflection.",
    ),
)

SEARCH_VISIBILITY_CRAWLERS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "PerplexityBot",
)

TRAINING_CRAWLERS = (
    "CCBot",
    "anthropic-ai",
    "Bytespider",
    "cohere-ai",
)

PRIVATE_PATHS = (
    "/api/",
    "/ws/",
)


def normalize_public_base_url(raw_url: str | None) -> str:
    """Return a trailing-slash public app base URL or path."""

    value = (raw_url or "/").strip() or "/"
    if not value.endswith("/"):
        value += "/"
    return value


def build_public_url(public_base_url: str | None, path: str = "") -> str:
    """Join a public app base URL with a sitemap or llms path."""

    base = normalize_public_base_url(public_base_url)
    normalized_path = path.lstrip("/")
    if base == "/":
        return f"/{normalized_path}" if normalized_path else "/"
    return urljoin(base, normalized_path)


def build_public_origin_url(public_base_url: str | None) -> str:
    """Extract the public origin for root-level machine-readable files."""

    base = normalize_public_base_url(public_base_url)
    parsed = urlsplit(base)
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, "/", "", ""))
    return "/"


def _crawler_policy_group(user_agent: str, *, block_all: bool = False) -> str:
    lines = [f"User-agent: {user_agent}"]
    if block_all:
        lines.append("Disallow: /")
    else:
        lines.append("Allow: /")
        for path in PRIVATE_PATHS:
            lines.append(f"Disallow: {path}")
    return "\n".join(lines)


def build_robots_txt(public_base_url: str | None) -> str:
    """Generate robots.txt with explicit AI-search crawler access."""

    origin = build_public_origin_url(public_base_url)
    sitemap_url = urljoin(origin, "sitemap.xml") if origin != "/" else "/sitemap.xml"

    groups = [
        _crawler_policy_group(crawler)
        for crawler in SEARCH_VISIBILITY_CRAWLERS
    ]
    groups.extend(
        _crawler_policy_group(crawler, block_all=True)
        for crawler in TRAINING_CRAWLERS
    )
    groups.append(_crawler_policy_group("*"))
    groups.append(f"Sitemap: {sitemap_url}")
    return "\n\n".join(groups) + "\n"


def build_sitemap_xml(public_base_url: str | None, last_modified: date | None = None) -> str:
    """Generate a compact XML sitemap for the public SPA surface."""

    lastmod = (last_modified or date.today()).isoformat()
    url_entries = []
    for path, _description in PUBLIC_APP_PATHS:
        loc = xml_escape(build_public_url(public_base_url, path))
        url_entries.append(
            "  <url>\n"
            f"    <loc>{loc}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            "  </url>"
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(url_entries)
        + "\n</urlset>\n"
    )


def build_llms_txt(
    public_base_url: str | None,
    backend_public_base_url: str | None = None,
) -> str:
    """Generate llms.txt guidance for AI-search crawlers."""

    app_url = build_public_url(public_base_url)
    backend_origin = build_public_origin_url(backend_public_base_url or public_base_url)
    health_url = (
        urljoin(backend_origin, "api/health")
        if backend_origin != "/"
        else "/api/health"
    )
    knowledge_base_links = "\n".join(
        f"- {label}: {url}" for label, url in BLOG_AND_KNOWLEDGE_BASE_LINKS
    )

    return f"""# {APP_NAME}
> {APP_DESCRIPTION}

## Main Pages
- [{APP_NAME}]({app_url}): Daily AI journaling studio with bilingual reflective writing, inner voice feedback, customizable voice decks, saved writing sessions, and visual memory timelines.

## Blog and Knowledge Base
{knowledge_base_links}

## Product Facts
- {APP_NAME} helps writers capture personal notes, reflect on recurring thoughts, and talk with configurable AI voice personas.
- The app supports English and Simplified Chinese writing flows.
- Core features include autosaved writing sessions, AI comments, deck-based voice customization, timeline images, and Reflections analysis.
- Private user notes and authenticated API data are not public index targets.

## Technical Access
- Public app URL: {app_url}
- Backend API origin: {backend_origin}
- Backend health endpoint: {health_url}
- Public machine-readable files: /robots.txt, /sitemap.xml, /llms.txt
- Authenticated application APIs under /api/ are excluded from crawler indexing.

## Keywords
{", ".join(APP_KEYWORDS)}

## Attribution
Ink & Memory is an open-source AI journaling and reflective writing application.
"""
