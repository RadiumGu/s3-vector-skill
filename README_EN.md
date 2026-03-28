# Amazon S3 Vectors Knowledge Base Skill

> [中文](README.md) | **English**

> A lightweight knowledge base built on Amazon S3 Vectors, providing OpenClaw Agents with a complete "store docs → search knowledge" RAG pipeline.
>
> S3 Vectors (GA at re:Invent 2025) + Bedrock Titan v2 Embedding — **90% cheaper** than traditional vector databases, **4 orders of magnitude cheaper** than Bedrock Knowledge Bases.

---

## ✨ Features

| Category | Capability | Script |
|----------|-----------|--------|
| **Document Ingestion** | Auto-chunking + embedding + write | `ingest.py` |
| **Semantic Search** | Natural language query with source citations | `search.py` |
| **KB Status** | Doc count, chunk count, tag distribution | `stats.py` |
| **Tag Management** | CRUD tags, supports CJK characters | `manage_tags.py` |
| **Vector CRUD** | 16 core operations (bucket/index/vector/policy) | See below |
| **Deep Read Mode** | LLM context prefix, +35-49% recall | `ingest.py --contextual` |

---

## 🚀 Setup from Scratch

### Step 0: Prerequisites

| Dependency | Requirement |
|-----------|-------------|
| Python | >= 3.10 |
| boto3 | Latest (must support `s3vectors` client) |
| AWS Permissions | `s3vectors:*` + `bedrock:InvokeModel` |
| OpenClaw | >= 2026.3 (when used as Skill) |

```bash
pip3 install boto3 --upgrade

# Verify s3vectors support
python3 -c "import boto3; boto3.client('s3vectors', region_name='ap-northeast-1'); print('✅ OK')"
```

### Step 1: Create Knowledge Base (S3 Vector Bucket + Index)

**Via conversation (recommended):**
> You: "I want to use the knowledge base"
> Agent: Automatically initializes — creates vector bucket and index

**Via command line:**
```bash
./install.sh --bucket openclaw-kb --index docs-v1
```

After setup you'll have:
- An S3 vector bucket: `openclaw-kb`
- A 1024-dimensional cosine index: `docs-v1`

### Step 2: Define Tag Categories

Tags categorize documents for filtered search. Supports CJK characters.

**Via conversation (recommended):**
> You: "Add a work tag, keywords: technical, AWS, architecture"
> Agent: ✅ Added category work
>
> You: "Add an AI tag too"
> Agent: ✅ Added category AI
>
> You: "What tags do we have?"
> Agent: Lists all tags with doc counts

**Via command line:**
```bash
python3 scripts/manage_tags.py --add "work" --label "Work" \
  --keywords "work,technical,AWS,architecture,deployment" --description "Work & technical docs"

python3 scripts/manage_tags.py --add "AI" --label "AI" \
  --keywords "AI,LLM,machine learning,RAG,embedding" --description "AI related"
```

Tag config is saved in `config/tags.json`, shared across all Agents.

### Step 3: Register with OpenClaw Agents

```bash
# Symlink to Agent workspace (once per Agent)
ln -s /path/to/s3-vector-skill ~/.openclaw/workspace-<NAME>/skills/s3-vector-bucket

# Batch setup for all Agents
for ws in ~/.openclaw/workspace-*/; do
  mkdir -p "$ws/skills"
  ln -s /path/to/s3-vector-skill "$ws/skills/s3-vector-bucket" 2>/dev/null
done
```

All configured Agents share the same knowledge base. Restart Agents to take effect.

### Step 4: Start Using

**Via conversation (recommended):**
> You: "Store this link in the KB https://docs.aws.amazon.com/..."
> Agent: 📚 Ingested, 12 chunks
>
> You: "How to troubleshoot EKS Pod scheduling failure?"
> Agent: 📚 Based on knowledge base... [with sources]

**Via command line:**
```bash
python3 scripts/ingest.py --bucket openclaw-kb --file /path/to/any-doc.md --tags "work"
python3 scripts/search.py --bucket openclaw-kb --query "some keyword from the doc" --output markdown
python3 scripts/stats.py --bucket openclaw-kb --output markdown
```

---

## 📖 Daily Usage

### Store Documents

**Via conversation:**
| You Say | Agent Does |
|---------|-----------|
| "Store this link in the KB" | Fetch page → chunk → ingest |
| "Save to KB, work related" | Ingest with tag = work |
| "This is important, store carefully" | Deep read mode (contextual) |
| "Import all files from /docs/" | Batch ingest |
| "Sync the KB" | Incremental sync (changes only) |

**Via command line:**
```bash
# Single file
python3 scripts/ingest.py --bucket openclaw-kb --file doc.md --tags "work"

# Batch directory
python3 scripts/ingest.py --bucket openclaw-kb --dir /path/to/docs/ --glob "*.md"

# From stdin (pipe with web_fetch, etc.)
echo "text content" | python3 scripts/ingest.py --bucket openclaw-kb --doc-id "article-001"

# Important docs — deep read mode (LLM context prefix, +35-49% recall, higher cost)
python3 scripts/ingest.py --bucket openclaw-kb --file important.md --contextual

# Incremental sync (only update changed files, delete removed)
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --sync

# Dry run (no actual writes)
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --dry-run
```

### Search Knowledge

**Via conversation:**
| You Say | Agent Does |
|---------|-----------|
| "How to troubleshoot EKS Pod scheduling?" | Auto-search KB → 📚 answer with sources |
| "Search work KB for xxx" | Filter by tag=work |
| "Anything about disaster recovery?" | Search → list matches |

**Via command line:**
```bash
# Semantic search
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod scheduling failure" --top-k 5

# Markdown output (Agent-friendly)
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod scheduling failure" --output markdown

# Filter by tag
python3 scripts/search.py --bucket openclaw-kb --query "..." --filter '{"tags": {"$eq": "work"}}'

# Adjust similarity threshold (default 0.6)
python3 scripts/search.py --bucket openclaw-kb --query "..." --threshold 0.7
```

### Manage Knowledge Base

**Via conversation:**
| You Say | Agent Does |
|---------|-----------|
| "What's in the KB?" | Show doc count, chunks, tag distribution |
| "Delete the Terraform doc" | Delete by doc_id |
| "Move that doc to ops category" | Reclassify |

**Via command line:**
```bash
# Status
python3 scripts/stats.py --bucket openclaw-kb --output markdown

# Tag distribution only
python3 scripts/stats.py --bucket openclaw-kb --tags

# Delete document
python3 scripts/ingest.py --bucket openclaw-kb --delete --doc-id "old-document"

# Reclassify document
python3 scripts/manage_tags.py --reclassify --doc-id "doc-001" --new-tag "ops" \
  --bucket openclaw-kb
```

### Manage Tags

**Via conversation:**
| You Say | Agent Does |
|---------|-----------|
| "What tags do we have?" | List all tags |
| "Add an architecture tag" | Add new tag |
| "Remove the learning tag" | Delete tag |
| "Add terraform to work tag" | Append keyword |

**Via command line:**
```bash
python3 scripts/manage_tags.py --list
python3 scripts/manage_tags.py --add "new-tag" --label "New Tag" --keywords "keyword1,keyword2"
python3 scripts/manage_tags.py --remove "old-tag"
python3 scripts/manage_tags.py --update "work" --add-keywords "terraform,docker"
```

---

## 🤖 OpenClaw Agent Integration

No commands to remember — just talk to your Agent:

| You Say | Agent Does |
|---------|-----------|
| "Store this link in the KB" | `web_fetch` → `ingest.py` |
| "This is important, store it carefully" | `ingest.py --contextual` |
| "Save to KB, work related" | `ingest.py --tags "work"` |
| "Import all files from /docs/" | `ingest.py --dir` |
| "Sync the KB" | `ingest.py --sync` |
| "How to troubleshoot EKS Pod scheduling?" | Search KB first → 📚 cite sources |
| "Search work KB for xxx" | `search.py --filter tag=work` |
| "What's in the KB?" | `stats.py` |
| "Add an architecture tag" | `manage_tags.py --add` |
| "Delete that old doc" | `ingest.py --delete` |

### Source Citations

| Icon | Meaning |
|------|---------|
| 📚 | From knowledge base (with chunk source and similarity) |
| 🌐 | From web search |
| 🤖 | From model's own knowledge |
| 📚+🌐 | KB + web supplemented |

---

## 📊 Chunking Strategies

| Strategy | Accuracy | Cost | Use Case |
|----------|----------|------|----------|
| **Recursive splitting** (default) | 69% | Free | All documents |
| **Heading-aware** (auto for Markdown) | ~75% | Free | Markdown with headings |
| **Contextual** (`--contextual`) | +35-49% | ~$0.0015/chunk | Important docs |

- Default: 512 tokens/chunk, 64 tokens overlap (Vecta 2026 benchmark optimal)
- Markdown files auto-detected for heading structure, preserving hierarchy path
- Semantic Chunking deliberately not used (benchmark only 54%, severe fragmentation)

---

## 💰 Cost Estimate

For 100 documents (~3000 chunks):

| Mode | Cost |
|------|------|
| Standard | < **$0.02/month** |
| Contextual | ~$4.50 one-time + $0.005/month |
| Bedrock Knowledge Bases (comparison) | ~$175/month |

---

## 🏗️ Multi-Agent Shared Architecture

```
Agent A ─┐
Agent B ──┤── symlink → s3-vector-skill/ ── config/tags.json
Agent C ──┘                               └─ scripts/*.py
                                                    │
                                                    ▼
                                          S3 Vectors: openclaw-kb
                                          Index: docs-v1
```

- **One codebase, one tag config, one knowledge base** — shared by all Agents
- Documents stored by any Agent are searchable by all others
- Tags provide logical isolation ("search only work knowledge")

---

## 📁 Project Structure

```
s3-vector-skill/
├── SKILL.md                    # OpenClaw Skill definition
├── PRD.md                      # Product requirements (not pushed to GitHub)
├── README.md                   # Chinese docs
├── README_EN.md                # English docs (this file)
├── install.sh                  # One-click setup (create bucket + index)
├── config/
│   └── tags.json               # Tag configuration (supports CJK)
├── scripts/
│   ├── common.py               # Shared utilities
│   ├── embed.py                # Bedrock Titan v2 Embedding (1024d, cached)
│   ├── chunker.py              # Document chunking (recursive + heading-aware + auto)
│   ├── ingest.py               # Document ingestion (chunk + embed + write + sync + delete)
│   ├── search.py               # Semantic search (markdown/json output, source citations)
│   ├── stats.py                # KB status (doc count, chunks, tag distribution)
│   ├── manage_tags.py          # Tag management (CRUD + reclassify)
│   ├── create_vector_bucket.py # Create vector bucket
│   ├── delete_vector_bucket.py # Delete vector bucket
│   ├── get_vector_bucket.py    # Describe vector bucket
│   ├── list_vector_buckets.py  # List vector buckets
│   ├── put_vector_bucket_policy.py  # Put bucket policy
│   ├── get_vector_bucket_policy.py  # Get bucket policy
│   ├── delete_vector_bucket_policy.py # Delete bucket policy
│   ├── create_index.py         # Create index
│   ├── get_index.py            # Describe index
│   ├── list_indexes.py         # List indexes
│   ├── delete_index.py         # Delete index
│   ├── put_vectors.py          # Put vectors
│   ├── get_vectors.py          # Get vectors
│   ├── list_vectors.py         # List vectors
│   ├── delete_vectors.py       # Delete vectors
│   └── query_vectors.py        # Similarity search (low-level API)
└── references/
    ├── api_reference.md        # S3 Vectors API reference
    └── cli-reference.md        # CLI command reference
```

---

## Technical Details

| Item | Details |
|------|---------|
| Embedding Model | Amazon Titan Text Embedding v2 (1024d) |
| Distance Metric | cosine (recommended for RAG) |
| Index Limit | 2B vectors per index, query latency < 100ms |
| Metadata Limit | 2048 bytes (UTF-8) per vector |
| Supported Formats | Markdown, plain text, HTML |
| Incremental Sync | Content hash (MD5) comparison, only updates changes |
| Tag Naming | Supports CJK, English, digits, hyphens |
| boto3 Client | `boto3.client('s3vectors', region_name=...)` |
| Auth Priority | Instance IAM Role > Env vars > AWS Profile |
| Supported Regions | us-east-1, us-west-2, eu-west-1, ap-northeast-1, etc. |
