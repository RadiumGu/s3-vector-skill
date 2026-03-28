# Amazon S3 Vectors 知识库 Skill

> **中文** | [English](README_EN.md)

> 基于 Amazon S3 Vectors 的轻量级知识库，为 OpenClaw Agent 提供"存文档 → 搜知识"的完整 RAG 能力。
>
> S3 Vectors（re:Invent 2025 GA）+ Bedrock Titan v2 Embedding，成本比传统向量数据库低 **90%**，比 Bedrock Knowledge Bases 低 **4 个数量级**。

---

## ✨ 功能概览

| 类别 | 能力 | 脚本 |
|------|------|------|
| **文档摄入** | 自动分块 + embedding + 写入 | `ingest.py` |
| **语义搜索** | 自然语言查询，返回相关文档和来源 | `search.py` |
| **知识库状态** | 文档数、chunk 数、tag 分布 | `stats.py` |
| **Tag 管理** | 增删改查分类标签，支持中文 | `manage_tags.py` |
| **向量桶 CRUD** | 16 个核心操作（桶/索引/向量/策略） | 见下方 |
| **精读模式** | LLM 生成上下文前缀，召回率 +35-49% | `ingest.py --contextual` |

---

## 🚀 快速开始

### 前置条件

| 依赖 | 要求 |
|------|------|
| Python | >= 3.10 |
| boto3 | 最新版（需支持 s3vectors） |
| AWS 权限 | `s3vectors:*` + `bedrock:InvokeModel` |

```bash
pip3 install boto3 --upgrade
```

### 初始化知识库

```bash
# 一键初始化（创建向量桶 + 索引）
./install.sh --bucket openclaw-kb --index docs-v1

# 或手动
python3 scripts/create_vector_bucket.py --bucket openclaw-kb
python3 scripts/create_index.py --bucket openclaw-kb --index docs-v1 --dimension 1024
```

### 存文档

```bash
# 单文件
python3 scripts/ingest.py --bucket openclaw-kb --file /path/to/doc.md --tags "work"

# 目录批量
python3 scripts/ingest.py --bucket openclaw-kb --dir /path/to/docs/ --glob "*.md" --sync

# 重要文档精读（LLM 生成上下文前缀）
python3 scripts/ingest.py --bucket openclaw-kb --file important.md --contextual
```

### 搜知识

```bash
# 语义搜索
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod 调度失败" --top-k 5

# Markdown 格式输出（Agent 友好）
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod 调度失败" --output markdown

# 按 tag 过滤
python3 scripts/search.py --bucket openclaw-kb --query "..." --filter '{"tags": {"$eq": "work"}}'
```

### 管理知识库

```bash
# 查看状态
python3 scripts/stats.py --bucket openclaw-kb --output markdown

# 管理 tag（支持中文）
python3 scripts/manage_tags.py --list
python3 scripts/manage_tags.py --add "架构韧性" --label "架构韧性" --keywords "韧性,容灾,高可用"
python3 scripts/manage_tags.py --remove "架构韧性"

# 删除文档
python3 scripts/ingest.py --bucket openclaw-kb --delete --doc-id "old-document"

# 增量同步
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --sync
```

---

## 🤖 OpenClaw Agent 集成

### 安装到 Agent

```bash
# 软链接到 workspace（所有配置了的 Agent 共享同一个知识库）
ln -s /path/to/s3-vector-skill ~/.openclaw/workspace-<NAME>/skills/s3-vector-bucket
```

### 使用方式

不需要记命令，对 Agent 说自然语言：

| 你说的 | Agent 做的 |
|--------|-----------|
| "把这个链接存到知识库" | `web_fetch` → `ingest.py` |
| "这篇很重要，仔细存一下" | `ingest.py --contextual` |
| "存到知识库，工作用的" | `ingest.py --tags "work"` |
| "EKS Pod 调度失败怎么排查？" | 先搜知识库 → 📚 标注来源回答 |
| "知识库里有什么？" | `stats.py` |
| "加一个架构韧性的标签" | `manage_tags.py --add` |

### 来源标注

Agent 回答时自动标注信息来源：

- 📚 — 来自知识库（附 chunk 来源和相似度）
- 🌐 — 来自网络搜索
- 🤖 — 来自模型自身知识

---

## 📊 分块策略

| 策略 | 准确率 | 成本 | 适用 |
|------|--------|------|------|
| **Recursive splitting**（默认） | 69% | 零 | 所有文档 |
| **Heading-aware**（Markdown 自动） | ~75% | 零 | 有 heading 结构的 Markdown |
| **Contextual**（`--contextual`） | +35-49% | ~$0.0015/chunk | 重要文档 |

- 默认 512 tokens/chunk，64 tokens overlap（Vecta 2026 benchmark 最优参数）
- Markdown 文件自动识别 heading 结构，保留层级路径

---

## 🏷️ Tag 分类

预定义 tag 在 `config/tags.json`，支持中文：

| Tag | 说明 |
|-----|------|
| `work` | 工作技术文档 |
| `life` | 生活日常 |
| `ops` | 运维手册、故障排查 |
| `learning` | 学习笔记 |

用户可通过对话添加新 tag（如"架构韧性"）。Agent 根据关键词自动映射，不会自己发明新 tag。

---

## 💰 成本

以 100 篇文档（~3000 chunks）为例：

| 模式 | 费用 |
|------|------|
| 标准模式 | < $0.02/月 |
| Contextual 模式 | ~$4.50 一次性 + $0.005/月 |
| Bedrock Knowledge Bases（对比） | ~$175/月 |

---

## 📁 项目结构

```
s3-vector-skill/
├── SKILL.md                    # OpenClaw Skill 定义
├── PRD.md                      # 产品需求文档
├── README.md                   # 中文文档
├── README_EN.md                # English docs
├── install.sh                  # 一键初始化
├── config/
│   └── tags.json               # Tag 分类配置
├── scripts/
│   ├── common.py               # 公共模块
│   ├── embed.py                # Bedrock Titan v2 Embedding
│   ├── chunker.py              # 文档分块（recursive + heading-aware）
│   ├── ingest.py               # 文档摄入（分块 + embedding + 写入）
│   ├── search.py               # 语义搜索
│   ├── stats.py                # 知识库状态
│   ├── manage_tags.py          # Tag 管理
│   ├── create_vector_bucket.py # 创建向量桶
│   ├── delete_vector_bucket.py # 删除向量桶
│   ├── get_vector_bucket.py    # 查询向量桶
│   ├── list_vector_buckets.py  # 列出向量桶
│   ├── put_vector_bucket_policy.py
│   ├── get_vector_bucket_policy.py
│   ├── delete_vector_bucket_policy.py
│   ├── create_index.py         # 创建索引
│   ├── get_index.py            # 查询索引
│   ├── list_indexes.py         # 列出索引
│   ├── delete_index.py         # 删除索引
│   ├── put_vectors.py          # 插入/更新向量
│   ├── get_vectors.py          # 获取向量
│   ├── list_vectors.py         # 列出向量
│   ├── delete_vectors.py       # 删除向量
│   └── query_vectors.py        # 相似度搜索
└── references/
    ├── api_reference.md        # S3 Vectors API 参考
    └── cli-reference.md        # CLI 命令参考
```

---

## 关键技术细节

| 项目 | 说明 |
|------|------|
| Embedding 模型 | Amazon Titan Text Embedding v2（1024 维） |
| 向量距离 | cosine（推荐 RAG） |
| 单索引上限 | 20 亿向量，查询延迟 < 100ms |
| Metadata 限制 | 2048 bytes（UTF-8）per vector |
| 支持格式 | Markdown、纯文本、HTML |
| 增量同步 | content hash 对比，只更新变更 |
| 已支持 Region | us-east-1, us-west-2, eu-west-1, ap-northeast-1 等 |
