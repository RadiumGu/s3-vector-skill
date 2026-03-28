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

## 🚀 Quick Start

### Prerequisites

| Dependency | Requirement |
|-----------|-------------|
| Python | >= 3.10 |
| boto3 | Latest (must support s3vectors) |
| AWS Permissions | `s3vectors:*` + `bedrock:InvokeModel` |

```bash
pip3 install boto3 --upgrade
```

### Initialize Knowledge Base

```bash
# One-click setup
./install.sh --bucket openclaw-kb --index docs-v1

# Or manually
python3 scripts/create_vector_bucket.py --bucket openclaw-kb
python3 scripts/create_index.py --bucket openclaw-kb --index docs-v1 --dimension 1024
```

### Store Documents

```bash
# Single file
python3 scripts/ingest.py --bucket openclaw-kb --file /path/to/doc.md --tags "work"

# Batch directory
python3 scripts/ingest.py --bucket openclaw-kb --dir /path/to/docs/ --glob "*.md" --sync

# Important docs — deep read mode (LLM context prefix)
python3 scripts/ingest.py --bucket openclaw-kb --file important.md --contextual
```

### Search Knowledge

```bash
# Semantic search
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod scheduling failure" --top-k 5

# Markdown output (Agent-friendly)
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod scheduling failure" --output markdown

# Filter by tag
python3 scripts/search.py --bucket openclaw-kb --query "..." --filter '{"tags": {"$eq": "work"}}'
```

### Manage Knowledge Base

```bash
# Status
python3 scripts/stats.py --bucket openclaw-kb --output markdown

# Tag management (supports CJK)
python3 scripts/manage_tags.py --list
python3 scripts/manage_tags.py --add "architecture" --label "Architecture" --keywords "architecture,design,resilience"
python3 scripts/manage_tags.py --remove "architecture"

# Delete document
python3 scripts/ingest.py --bucket openclaw-kb --delete --doc-id "old-document"

# Incremental sync
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --sync
```

---

## 🤖 OpenClaw Agent Integration

### Install to Agent

```bash
# Symlink to workspace (all configured Agents share the same KB)
ln -s /path/to/s3-vector-skill ~/.openclaw/workspace-<NAME>/skills/s3-vector-bucket
```

### Usage

No commands to remember — just talk to your Agent:

| You Say | Agent Does |
|---------|-----------|
| "Store this link in the KB" | `web_fetch` → `ingest.py` |
| "This is important, store it carefully" | `ingest.py --contextual` |
| "Save to KB, work related" | `ingest.py --tags "work"` |
| "How to troubleshoot EKS Pod scheduling?" | Search KB first → 📚 cite sources |
| "What's in the KB?" | `stats.py` |
| "Add an architecture tag" | `manage_tags.py --add` |

### Source Citations

Agents automatically label information sources:

- 📚 — From knowledge base (with chunk source and similarity score)
- 🌐 — From web search
- 🤖 — From model's own knowledge

---

## 📊 Chunking Strategies

| Strategy | Accuracy | Cost | Use Case |
|----------|----------|------|----------|
| **Recursive splitting** (default) | 69% | Free | All documents |
| **Heading-aware** (auto for Markdown) | ~75% | Free | Markdown with headings |
| **Contextual** (`--contextual`) | +35-49% | ~$0.0015/chunk | Important docs |

- Default: 512 tokens/chunk, 64 tokens overlap (Vecta 2026 benchmark optimal)
- Markdown files auto-detected for heading structure, preserving hierarchy path

---

## 🏷️ Tag System

Predefined tags in `config/tags.json`, supports CJK characters:

| Tag | Description |
|-----|------------|
| `work` | Work & technical docs |
| `life` | Daily life |
| `ops` | Operations, troubleshooting |
| `learning` | Study notes |

Users can add tags via conversation. Agents auto-map keywords but never invent new tags.

---

## 💰 Cost Estimate

For 100 documents (~3000 chunks):

| Mode | Cost |
|------|------|
| Standard | < $0.02/month |
| Contextual | ~$4.50 one-time + $0.005/month |
| Bedrock Knowledge Bases (comparison) | ~$175/month |

---

## 📁 Project Structure

```
s3-vector-skill/
├── SKILL.md                    # OpenClaw Skill definition
├── PRD.md                      # Product requirements
├── README.md                   # Chinese docs
├── README_EN.md                # English docs
├── install.sh                  # One-click setup
├── config/
│   └── tags.json               # Tag configuration
├── scripts/
│   ├── common.py               # Shared utilities
│   ├── embed.py                # Bedrock Titan v2 Embedding
│   ├── chunker.py              # Document chunking (recursive + heading-aware)
│   ├── ingest.py               # Document ingestion
│   ├── search.py               # Semantic search
│   ├── stats.py                # KB status
│   ├── manage_tags.py          # Tag management
│   ├── create_vector_bucket.py # Create vector bucket
│   ├── delete_vector_bucket.py # Delete vector bucket
│   ├── get_vector_bucket.py    # Describe vector bucket
│   ├── list_vector_buckets.py  # List vector buckets
│   ├── put_vector_bucket_policy.py
│   ├── get_vector_bucket_policy.py
│   ├── delete_vector_bucket_policy.py
│   ├── create_index.py         # Create index
│   ├── get_index.py            # Describe index
│   ├── list_indexes.py         # List indexes
│   ├── delete_index.py         # Delete index
│   ├── put_vectors.py          # Put vectors
│   ├── get_vectors.py          # Get vectors
│   ├── list_vectors.py         # List vectors
│   ├── delete_vectors.py       # Delete vectors
│   └── query_vectors.py        # Similarity search
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
| Incremental Sync | Content hash comparison, only updates changes |
| Supported Regions | us-east-1, us-west-2, eu-west-1, ap-northeast-1, etc. |
