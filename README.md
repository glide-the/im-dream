# Ink & Memory

<p align="center">
  <img src="assets/banner.png" alt="Ink & Memory Banner" width="700"/>
</p>

<p align="center">
  <a href="README.zh.md">中文</a> · English
</p>

> *Write. Reflect. Listen to the voices within.*

**Ink & Memory** is a journaling studio inspired by the inner monologues of *Disco Elysium*. As you write, a council of distinct personas chimes in—offering perspective, asking questions, or pointing out the absurdity of it all.

This isn't just another notes app. It's a daily writing companion that saves your work, organizes your thoughts, and helps you notice patterns in your own thinking. It speaks both English and Chinese, switching seamlessly as you write.

---

## What Makes It Different

<p align="center">
  <img src="assets/writing-area.png" alt="Writing with inner voices" width="700"/>
</p>

**A clean writing space.** No toolbar clutter. Just a calm surface for your thoughts, with automatic saving so nothing gets lost.

**A council of inner voices.** As you type, different personas highlight phrases and offer their takes—from the pattern-spotting Mirror to the darkly funny Absurdist. They appear as gentle watercolor highlights in the margins, never interrupting your flow.

**Your timeline, visualized.** Every session is saved to a calendar. Each day generates a unique image from your writing—a visual diary that grows with you.

**Fully customizable.** Don't like a voice? Edit it. Want new perspectives? Create your own deck. Share your creations with the community or discover what others have made.

---

## The Voices

The voices are organized into three decks. Enable the ones that resonate; disable the rest.

### Introspection Deck
*For processing emotions and understanding yourself*

| | Voice | What it does |
|---|---|---|
| ❤️ | **Holder** | Offers gentle validation and support |
| 👁️ | **Mirror** | Reflects patterns you might not notice |
| 👊 | **Starter** | Breaks paralysis with tiny first steps |
| 🧭 | **Weaver** | Finds hidden threads connecting your thoughts |
| 🎭 | **Absurdist** | Lightens heaviness with dark humor |

### Scholar Deck
*For intellectual and academic perspectives*

| | Voice | What it does |
|---|---|---|
| 🧭 | **Linguist** | Analyzes structure, semantics, meaning |
| 👁️ | **Painter** | Focuses on imagery, aesthetics, mood |
| 💡 | **Physicist** | Applies principles of energy and systems |
| 🧠 | **Computer Scientist** | Thinks in algorithms and complexity |
| ❤️ | **Doctor** | Offers health and psychological angles |
| 🧭 | **Historian** | Provides context and historical patterns |

### Philosophy Deck
*For examining life through different lenses*

| | Voice | What it does |
|---|---|---|
| 🛡️ | **Stoic** | Emphasizes what you can and can't control |
| 💨 | **Taoist** | Points toward effortless action and flow |
| 🤔 | **Existentialist** | Asks about choice, freedom, meaning |
| 👊 | **Pragmatist** | Focuses on what actually works |

### Making Your Own

Each voice is just a system prompt, an icon, and a color. Fork any deck to customize it. Create voices that channel your favorite thinker, focus on specific aspects of your life, or just make you laugh. Share them in the community store.

---

## Getting Started

### You'll Need
- Python 3.11+ with [uv](https://github.com/astral-sh/uv)
- Node.js 18+

### Backend Setup

```bash
cd backend
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

Configure the Admin Gateway in `backend/.env`. Dream has no direct Provider
endpoint/key fallback: writing, chat, analysis, Claude Agent, workflows and
daily-picture description/generation all use server-side Gateway aliases.

```dotenv
INK_GATEWAY_ENABLED=1
INK_GATEWAY_BASE_URL=http://127.0.0.1:3000
INK_GATEWAY_SERVICE_KEY=
INK_GATEWAY_TEXT_MODEL_ALIAS=dream-balanced
INK_GATEWAY_IMAGE_DESCRIPTION_MODEL_ALIAS=dream-image-description
INK_GATEWAY_IMAGE_GENERATION_MODEL_ALIAS=dream-image-generation
```

The service key is injected at runtime and must never be committed, returned
to the browser or written to application logs.

Dream Settings → AI 模型 does not contain a static model list. The browser
calls Dream `GET /api/gateway/models`; Dream signs the canonical subject and
calls Admin `GET /v1/models` with `models:list`. Saving a model stores only the
platform alias, and every Claude Agent turn revalidates it before the SDK is
forced through Admin Gateway. Provider IDs, upstream model names and Gateway
credentials are never accepted from the browser.

Configure the PostgreSQL-only runtime in `backend/.env`. Set `DATABASE_URL`
directly, or point Dream at an existing env file and it will load only that
file's `DATABASE_URL` value:

```dotenv
DATABASE_URL=postgresql://ink_memory:ink_memory@127.0.0.1:5433/ink-memory
# Or load only DATABASE_URL from an existing environment file:
INK_LOAD_DATABASE_URL_FROM_ENV_FILE=1
INK_DATABASE_ENV_FILE=/absolute/path/to/ink-admin-memory/.env.local
```

Then start the server:

```bash
cd backend
.venv/bin/python server.py  # Runs on http://localhost:8765
```

Use the repository virtual environment shown above. Calling the system
`python` directly is unsupported because it may not contain the locked
PostgreSQL driver (`psycopg`) or the rest of the backend dependencies.

### PostgreSQL migration

Dream does not create tables at application startup and has no SQLite/JSON/
memory fallback. Dream Alembic owns the 48 canonical table definitions and the
Dream importer owns snapshot/staging/validation; Admin Drizzle owns the ordered
data-migration registry and subscription bootstrap. A fresh database must run
Admin `0000–0026`, Dream Alembic head `20260809_06`, Admin `0027–0028`, then
the two `drizzle/data` runners. This order lets Dream exactly adopt the three
canonical tables before the approved Admin Story extensions are applied.

The importer defaults to a source-only dry run; production execution
additionally requires exact database/host/port/owner and an explicit approval
string.

```bash
python backend/script/migrate_legacy_to_postgres.py \
  --main-sqlite /absolute/path/to/ink-and-memory.db \
  --notion-sqlite /absolute/path/to/notion-connectors.db
```

From the Admin repository, `pnpm db:data:legacy -- --main-sqlite <absolute>
--notion-sqlite <absolute> --mode execute --record` runs the same Dream-owned
importer and records only safe table counts/digests. `pnpm
db:data:subscriptions -- --apply` initializes `Free`, `Dream`, and `is
Dreaming` plus the canonical-user subscription projections. Existing
PostgreSQL installations use `--mode verify-existing`; post-cutover changes
are accepted only with the explicit flag and only when every source PK exists
and the target timestamp proves that the PostgreSQL row is newer.

The local Admin-owned `localhost:5433/ink-memory` was re-verified on
2026-08-10 with Admin migration count 29 and Dream head `20260809_06`. All 48
source tables / 4,921 source primary keys are present: 4,919 rows match exactly
and 2 rows are verified newer PostgreSQL writes; no source row is missing and
the adoption transaction wrote no business data. The append-only Drizzle
registry contains two runs and 48 table results; all 30 canonical users have
their internal projection, billing account, and Subscription, and all three
default Plans exist. The 48-table total is the complete 43-table Dream main
source plus the 5-table Notion Connector source; it is not the earlier
three-table Admin importer.
See the Admin architecture runbook and correction worklog before migrating a
different environment.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev  # Listens on 0.0.0.0:5173; open http://<this-machine-ip>:5173 from another device
```

---

## How It Works

The voice system uses a **trace-based energy model**:

1. **Energy builds** as you write
2. **Threshold triggers** analysis of recent text
3. **Voices scan** for phrases that match their personality
4. **Comments appear** as watercolor highlights in the margin

This creates an organic rhythm—voices chime in naturally rather than constantly interrupting.

---

## Technical Stack

**Frontend:** React 19 + TypeScript, Vite, TipTap editor with custom extensions

**Backend:** FastAPI + Python, PolyCLI for LLM orchestration, PostgreSQL 16 with psycopg 3 pooling and Dream-owned Alembic

**AI:** Multi-model support (GPT-4, Claude, DeepSeek, Gemini), structured outputs via Pydantic

**Architecture:** Deck-based voice system with parent-child relationships, community store for sharing

---

## Roadmap

- More voices and community-created decks
- Richer visualizations of your writing patterns
- Mobile app for writing on the go
- Collaborative features

---

## Deployment

The current backend requires PostgreSQL and must not be deployed with the old
Cloud Storage FUSE/SQLite persistence path. The commands below remain legacy
deployment scaffolding until its environment is updated for `DATABASE_URL`,
Alembic and the PostgreSQL cutover gates:

```bash
export GCP_PROJECT_ID=your-project-id
./deploy/google-cloud/deploy.sh setup-storage  # one-time: GCS bucket + service account
./deploy/google-cloud/deploy.sh setup-env      # one-time: secrets + env vars
./deploy/google-cloud/deploy.sh deploy         # every release
```

See [docs/deploy/overview.md](docs/deploy/overview.md) for the full guide.

---

## Contributing

This is open source. We'd love your help.

- **Found a bug?** Open an issue
- **Have an idea?** Let's discuss it
- **Want to code?** PRs welcome
- **Created a cool deck?** Share it with the community

---

<p align="center">
  <i>Your thoughts deserve to be heard—even by yourself.</i>
</p>
