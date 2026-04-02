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

## 🚀 从零开始配置

### Step 0：环境准备

| 依赖 | 要求 |
|------|------|
| Python | >= 3.10 |
| boto3 | 最新版（需支持 `s3vectors` 客户端） |
| AWS 权限 | `s3vectors:*` + `bedrock:InvokeModel` |
| OpenClaw | >= 2026.3（作为 Skill 使用时） |

```bash
pip3 install boto3 --upgrade

# 验证 boto3 支持 s3vectors
python3 -c "import boto3; boto3.client('s3vectors', region_name='ap-northeast-1'); print('✅ OK')"
```

### Step 1：创建知识库（S3 向量桶 + 索引）

**对话方式（推荐）：**
> 你："我想用知识库"
> Agent：自动执行初始化，创建向量桶和索引

**命令行方式：**
```bash
./install.sh --bucket openclaw-kb --index docs-v1
```

初始化完成后你会得到：
- 一个 S3 向量桶：`openclaw-kb`
- 一个 1024 维的 cosine 索引：`docs-v1`

### Step 2：设定 Tag 分类

Tag 用于给文档分类，方便按类别搜索。支持中文。

**对话方式（推荐）：**
> 你："加一个工作标签，关键词是技术、AWS、架构"
> Agent：✅ 已添加分类 work（工作）
>
> 你："再加一个 AI 标签"
> Agent：✅ 已添加分类 AI
>
> 你："现在有哪些标签？"
> Agent：列出所有 tag 和文档数

**命令行方式：**
```bash
python3 scripts/manage_tags.py --add "work" --label "工作" \
  --keywords "工作,技术,AWS,架构,部署" --description "工作技术文档"

python3 scripts/manage_tags.py --add "AI" --label "AI" \
  --keywords "AI,大模型,LLM,机器学习,RAG" --description "AI 相关"

# 中文 tag 名也可以
python3 scripts/manage_tags.py --add "财经" --label "财经" \
  --keywords "股票,基金,投资,理财" --description "财经相关"
```

Tag 配置保存在 `config/tags.json`，所有 Agent 共享。

### Step 3：注册到 OpenClaw Agent

```bash
# 为 Agent 创建软链接（每个需要知识库的 Agent 执行一次）
ln -s /path/to/s3-vector-skill ~/.openclaw/workspace-<NAME>/skills/s3-vector-bucket

# 示例：为所有 Agent 批量配置
for ws in ~/.openclaw/workspace-*/; do
  mkdir -p "$ws/skills"
  ln -s /path/to/s3-vector-skill "$ws/skills/s3-vector-bucket" 2>/dev/null
done
```

配置后 Agent 重启生效。所有配置了的 Agent 共享同一个知识库。

### Step 4：开始使用

**对话方式（推荐）：**
> 你："把这个链接存到知识库 https://docs.aws.amazon.com/..."
> Agent：📚 已入库，共 12 个 chunk
>
> 你："EKS Pod 调度失败怎么排查？"
> Agent：📚 以下回答基于知识库... [附来源]

**命令行方式：**
```bash
python3 scripts/ingest.py --bucket openclaw-kb --file /path/to/any-doc.md --tags "work"
python3 scripts/search.py --bucket openclaw-kb --query "文档中的某个关键内容" --output markdown
python3 scripts/stats.py --bucket openclaw-kb --output markdown
```

---

## 📖 日常使用

### 存文档

**对话方式：**
| 你说的 | Agent 做的 |
|--------|-----------|
| "把这个链接存到知识库" | 抓取网页 → 分块 → 入库 |
| "存到知识库，工作用的" | 入库，tag = work |
| "把 /docs/ 下面的文件都导入" | 批量入库 |
| "同步一下知识库" | 增量同步（只更新变更） |

**命令行方式：**
```bash
# 单文件
python3 scripts/ingest.py --bucket openclaw-kb --file doc.md --tags "work" --author "大乖乖"

# 目录批量导入
python3 scripts/ingest.py --bucket openclaw-kb --dir /path/to/docs/ --glob "*.md"

# 从 stdin 导入（配合 web_fetch 等管道）
echo "文本内容" | python3 scripts/ingest.py --bucket openclaw-kb --doc-id "article-001"

# 增量同步（只更新变更文件，删除已移除文件）
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --sync

# 试运行（不实际写入）
python3 scripts/ingest.py --bucket openclaw-kb --dir /docs/ --dry-run
```

### ⭐ 精读模式（Contextual Chunking）

普通入库只做分块 + embedding。**精读模式**额外用 LLM 给每个 chunk 生成上下文摘要，搜索时召回率提升 **35-49%**（Anthropic 研究数据）。

**什么时候用精读模式？**
- 重要的参考文档（架构方案、RCA 报告、技术标准）
- 内容结构不清晰的长文档（会议记录、纯文本笔记）
- 希望搜索更准的文档

**怎么唤醒精读模式？**

说这些关键词，Agent 自动启用：

| 你说的 | 触发 |
|--------|------|
| "这篇**很重要**，存一下" | ✅ 精读模式 |
| "**仔细**存到知识库" | ✅ 精读模式 |
| "**精读**一下再存" | ✅ 精读模式 |
| "用**高质量**模式入库" | ✅ 精读模式 |
| "存到知识库"（不强调） | ❌ 普通模式 |

**效果对比：**

```
普通模式（默认）：
  chunk: "Pod 处于 Pending 状态时检查 Events..."
  → 搜索 "调度失败" 可能命中，也可能漏掉

精读模式：
  chunk: "[本段来自 EKS 故障排查指南第 3 章，讨论 Pod 调度失败的诊断步骤]
          Pod 处于 Pending 状态时检查 Events..."
  → 搜索 "调度失败" 几乎必定命中 ✅
```

**成本差异：**
- 普通模式：100 篇文档 ~$0.015（一次性）
- 精读模式：100 篇文档 ~$4.50（一次性，Haiku 生成上下文前缀）

**命令行方式：**
```bash
# 精读模式
python3 scripts/ingest.py --bucket openclaw-kb --file important.md --contextual

# 指定 LLM 模型（默认 Haiku，最便宜）
python3 scripts/ingest.py --bucket openclaw-kb --file doc.md --contextual \
  --contextual-model anthropic.claude-3-haiku-20240307-v1:0
```

### 搜知识

**对话方式：**
| 你说的 | Agent 做的 |
|--------|-----------|
| "EKS Pod 调度失败怎么排查？" | 自动搜知识库 → 📚 标注来源回答 |
| "工作知识库里搜一下 xxx" | 只搜 tag=work |
| "知识库里有关于容灾的内容吗？" | 搜索 → 列出匹配结果 |

**命令行方式：**
```bash
# 语义搜索
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod 调度失败" --top-k 5

# Markdown 输出（适合 Agent 回复）
python3 scripts/search.py --bucket openclaw-kb --query "EKS Pod 调度失败" --output markdown

# 按 tag 过滤
python3 scripts/search.py --bucket openclaw-kb --query "..." --filter '{"tags": {"$eq": "work"}}'

# 调整相似度阈值（默认 0.6）
python3 scripts/search.py --bucket openclaw-kb --query "..." --threshold 0.7
```

### 管理知识库

**对话方式：**
| 你说的 | Agent 做的 |
|--------|-----------|
| "知识库里有什么？" | 显示文档数、chunk 数、tag 分布 |
| "删掉关于 Terraform 的文档" | 按 doc_id 删除 |
| "把那篇文档改成运维分类" | 重新分类 |

**命令行方式：**
```bash
# 查看状态
python3 scripts/stats.py --bucket openclaw-kb --output markdown

# 只看 tag 分布
python3 scripts/stats.py --bucket openclaw-kb --tags

# 删除文档
python3 scripts/ingest.py --bucket openclaw-kb --delete --doc-id "old-document"

# 重新分类文档
python3 scripts/manage_tags.py --reclassify --doc-id "doc-001" --new-tag "ops" \
  --bucket openclaw-kb
```

### 管理 Tag

**对话方式：**
| 你说的 | Agent 做的 |
|--------|-----------|
| "现在有哪些标签？" | 列出所有 tag |
| "加一个架构韧性的标签" | 添加新 tag |
| "把 learning 标签删掉" | 删除 tag |
| "work 标签加上 terraform" | 追加关键词 |

**命令行方式：**
```bash
python3 scripts/manage_tags.py --list
python3 scripts/manage_tags.py --add "新分类" --label "新分类" --keywords "关键词1,关键词2"
python3 scripts/manage_tags.py --remove "旧分类"
python3 scripts/manage_tags.py --update "work" --add-keywords "terraform,docker"
```

---

## 🤖 OpenClaw Agent 使用方式

配置好后不需要记任何命令，对 Agent 说自然语言：

| 你说的 | Agent 做的 |
|--------|-----------|
| "把这个链接存到知识库" | `web_fetch` → `ingest.py` |
| "这篇很重要，仔细存一下" | `ingest.py --contextual` |
| "存到知识库，工作用的" | `ingest.py --tags "work"` |
| "把 /docs/ 下面的文件都导入" | `ingest.py --dir` |
| "同步一下知识库" | `ingest.py --sync` |
| "EKS Pod 调度失败怎么排查？" | 先搜知识库 → 📚 标注来源回答 |
| "工作知识库里搜一下 xxx" | `search.py --filter tag=work` |
| "知识库里有什么？" | `stats.py` |
| "加一个架构韧性的标签" | `manage_tags.py --add` |
| "把那篇文档删掉" | `ingest.py --delete` |

### 来源标注

Agent 回答时自动标注信息来源：

| 图标 | 含义 |
|------|------|
| 📚 | 来自知识库（附 chunk 来源和相似度） |
| 🌐 | 来自网络搜索 |
| 🤖 | 来自模型自身知识 |
| 📚+🌐 | 知识库 + 网络补充 |

---

## 📊 分块策略

| 策略 | 准确率 | 成本 | 适用 |
|------|--------|------|------|
| **Recursive splitting**（默认） | 69% | 零 | 所有文档 |
| **Heading-aware**（Markdown 自动） | ~75% | 零 | 有 heading 结构的 Markdown |
| **Contextual**（`--contextual`） | +35-49% | ~$0.0015/chunk | 重要文档 |

- 默认 512 tokens/chunk，64 tokens overlap（Vecta 2026 benchmark 最优参数）
- Markdown 文件自动识别 heading 结构，保留层级路径
- 不采用 Semantic Chunking（benchmark 仅 54%，碎片化严重）

---

## 💰 成本

以 100 篇文档（~3000 chunks）为例：

| 模式 | 费用 |
|------|------|
| 标准模式 | < **$0.02/月** |
| Contextual 模式 | ~$4.50 一次性 + $0.005/月 |
| Bedrock Knowledge Bases（对比） | ~$175/月 |

---

## 🏗️ 多 Agent 共享架构

```
Agent A ─┐
Agent B ──┤── symlink → s3-vector-skill/ ── config/tags.json
Agent C ──┘                               └─ scripts/*.py
                                                    │
                                                    ▼
                                          S3 Vectors: openclaw-kb
                                          索引: docs-v1
```

- **一份代码、一份 tag 配置、一个知识库**，所有 Agent 共享
- 任一 Agent 存的文档，其他 Agent 都能搜到
- Tag 分类提供逻辑隔离（"只搜工作知识"）

---

## 📁 项目结构

```
s3-vector-skill/
├── SKILL.md                    # OpenClaw Skill 定义（Agent 读取）
├── README.md                   # 中文文档（本文件）
├── README_EN.md                # English docs
├── install.sh                  # 一键初始化（创建桶 + 索引）
├── config/
│   └── tags.json               # Tag 分类配置（支持中文）
├── scripts/
│   ├── common.py               # 公共模块（参数解析、客户端、错误处理）
│   ├── embed.py                # Bedrock Titan v2 Embedding（1024d，带缓存）
│   ├── chunker.py              # 文档分块（recursive + heading-aware + auto）
│   ├── ingest.py               # 文档摄入（分块 + embed + 写入 + sync + delete）
│   ├── search.py               # 语义搜索（markdown/json 输出，来源标注）
│   ├── stats.py                # 知识库状态（文档数、chunks、tag 分布）
│   ├── manage_tags.py          # Tag 管理（增删改查 + 重新分类）
│   ├── create_vector_bucket.py # 创建向量桶
│   ├── delete_vector_bucket.py # 删除向量桶
│   ├── get_vector_bucket.py    # 查询向量桶
│   ├── list_vector_buckets.py  # 列出向量桶
│   ├── put_vector_bucket_policy.py  # 设置桶策略
│   ├── get_vector_bucket_policy.py  # 获取桶策略
│   ├── delete_vector_bucket_policy.py # 删除桶策略
│   ├── create_index.py         # 创建索引
│   ├── get_index.py            # 查询索引
│   ├── list_indexes.py         # 列出索引
│   ├── delete_index.py         # 删除索引
│   ├── put_vectors.py          # 插入/更新向量
│   ├── get_vectors.py          # 获取向量
│   ├── list_vectors.py         # 列出向量
│   ├── delete_vectors.py       # 删除向量
│   └── query_vectors.py        # 相似度搜索（底层 API）
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
| 操作限制 | TopK 1-100，批量 ≤500，embedding ≤8000 字符 |
| 索引维度校验 | ingest 启动时自动校验，维度不匹配直接报错 |
| 支持文档格式 | Markdown、纯文本、HTML |
| 增量同步 | content hash（MD5）对比，只更新变更 |
| Tag 命名 | 支持中文、英文、数字、连字符 |
| boto3 客户端 | `boto3.client('s3vectors', region_name=...)` |
| 认证优先级 | 实例 IAM Role > 环境变量 > AWS Profile |
| 已支持 Region | us-east-1, us-west-2, eu-west-1, ap-northeast-1 等 |
