---
name: s3-vector-bucket
description: "Amazon S3 向量桶全功能管理技能。覆盖向量桶、索引、向量数据的全生命周期（16 个核心 CRUD 能力）+ 知识库摄入与语义搜索。基于 S3 Vectors（re:Invent 2025 GA）+ Bedrock Titan v2（1024d），成本比传统向量 DB 低约 90%。"
triggers:
  - vector bucket
  - vector index
  - vector search
  - 向量桶
  - 向量索引
  - 向量搜索
  - 向量存储
  - 插入向量
  - 相似度搜索
  - S3 vector
  - S3 vectors
  - 知识库
  - knowledge base
  - 存到知识库
  - 搜索知识库
  - ingest
  - 导入文档
---

# Amazon S3 向量桶全功能管理技能

通过 boto3 的 `s3vectors` 客户端管理 Amazon S3 向量桶的完整生命周期。

> **S3 Vectors** 于 2025年12月 re:Invent 正式 GA，单索引支持 20 亿向量，查询延迟 < 100ms，
> 成本比 OpenSearch / pgvector 等方案低 90%。

## 回答问题前，优先检索知识库

当用户提问且问题可能在知识库中有答案时，**先搜索知识库再回答**：

```bash
python3 {baseDir}/scripts/search.py \
  --bucket openclaw-kb --index docs-v1 \
  --query "用户的问题" --top-k 3 --output markdown
```

- 有结果（score ≥ 0.6）→ 基于知识库回答，标注 📚 来源
- 无结果 → 用 web_search 或自身知识回答，标注 🌐 或 🤖

**来源标注规范：**
- 📚 — 来自知识库（附 chunk 来源和相似度）
- 🌐 — 来自网络搜索
- 🤖 — 来自模型自身知识
- 📚+🌐 — 知识库 + 网络补充

## 知识库管理

| 能力 | 脚本 | 说明 |
|------|------|------|
| 文档摄入 | `ingest.py` | 分块 + embedding + 写入 S3 Vectors |
| 语义搜索 | `search.py` | query embedding + 相似度搜索 |
| 知识库状态 | `stats.py` | 文档数、chunk 数、tag 分布 |
| Tag 管理 | `manage_tags.py` | 增删改查分类标签 |

### Tag 分类

文档可以打 tag 分类，预定义 tag 在 `config/tags.json`：
- `work` — 工作技术文档
- `life` — 生活日常
- `ops` — 运维手册、故障排查
- `learning` — 学习笔记

Agent 根据用户描述自动映射：
- 用户说"工作用的" → `--tags "work"`
- 用户说"生活类的" → `--tags "life"`
- 用户不说类别 → 不打 tag

搜索时：
- 用户说"工作知识库里搜 xxx" → `--filter '{"tags": {"$eq": "work"}}'`
- 用户直接问问题 → 全搜（不过滤 tag）

### Tag 管理

```bash
# 查看所有 tag
python3 {baseDir}/scripts/manage_tags.py --list

# 添加 tag（用户说"加一个 xxx 分类"）
python3 {baseDir}/scripts/manage_tags.py --add TAG_NAME --label "显示名" --keywords "关键词1,关键词2"

# 删除 tag（用户说"把 xxx 分类删掉"）
python3 {baseDir}/scripts/manage_tags.py --remove TAG_NAME

# 追加关键词（用户说"work 加上 terraform"）
python3 {baseDir}/scripts/manage_tags.py --update TAG_NAME --add-keywords "新关键词1,新关键词2"

# 重新分类文档（用户说"把那篇文档改成 ops"）
python3 {baseDir}/scripts/manage_tags.py --reclassify --doc-id DOC_ID --new-tag NEW_TAG \
  --bucket openclaw-kb --index docs-v1
```

### 文档摄入

```bash
# 单文件
python3 {baseDir}/scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
  --file /path/to/doc.md [--source "https://..."] [--tags "eks,k8s"] [--author "大乖乖"]

# 目录批量
python3 {baseDir}/scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
  --dir /path/to/docs/ [--glob "*.md"] [--sync]

# stdin（配合 web_fetch）
echo "内容" | python3 {baseDir}/scripts/ingest.py --bucket openclaw-kb \
  --index docs-v1 --doc-id "article-001" --source "https://..."

# 删除
python3 {baseDir}/scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
  --delete --doc-id "old-document"

# 重要文档精读入库（用户说"重要/仔细/精读"时自动启用）
python3 {baseDir}/scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
  --file doc.md --contextual
```

### 知识库状态

```bash
# 用户问"知识库里有什么" / "知识库状态"
python3 {baseDir}/scripts/stats.py --bucket openclaw-kb --index docs-v1 --output markdown
```

### 语义搜索

```bash
python3 {baseDir}/scripts/search.py --bucket openclaw-kb --index docs-v1 \
  --query "搜索内容" --top-k 5 [--output markdown|json]
```

## 向量桶 CRUD 能力（16 个）

| 类别 | 能力 | 脚本 |
|------|------|------|
| **向量桶管理** | 创建向量桶 | `create_vector_bucket.py` |
| | 删除向量桶 | `delete_vector_bucket.py` |
| | 查询向量桶信息 | `get_vector_bucket.py` |
| | 列出所有向量桶 | `list_vector_buckets.py` |
| **桶策略管理** | 设置桶策略 | `put_vector_bucket_policy.py` |
| | 获取桶策略 | `get_vector_bucket_policy.py` |
| | 删除桶策略 | `delete_vector_bucket_policy.py` |
| **索引管理** | 创建索引 | `create_index.py` |
| | 查询索引信息 | `get_index.py` |
| | 列出所有索引 | `list_indexes.py` |
| | 删除索引 | `delete_index.py` |
| **向量数据操作** | 插入/更新向量 | `put_vectors.py` |
| | 获取指定向量 | `get_vectors.py` |
| | 列出向量列表 | `list_vectors.py` |
| | 删除向量 | `delete_vectors.py` |
| | 相似度搜索 | `query_vectors.py` |

## 首次使用

```bash
# 检查 boto3
python3 -c "import boto3; boto3.client('s3vectors', region_name='ap-northeast-1'); print('OK')"

# 创建向量桶和索引
python3 {baseDir}/scripts/create_vector_bucket.py --bucket openclaw-kb
python3 {baseDir}/scripts/create_index.py --bucket openclaw-kb --index docs-v1 --dimension 1024
```

## 公共参数

| 参数 | 必需 | 说明 |
|------|:---:|------|
| `--bucket` | ✅ | 向量桶名称 |
| `--region` | ❌ | AWS Region，默认 `ap-northeast-1` |
| `--profile` | ❌ | AWS CLI Profile |

## 操作限制

| 参数 | 限制 | 说明 |
|------|------|------|
| `--top-k` | 1-100 | S3 Vectors 单次查询最大返回 100 条 |
| 单次批量写入 | ≤ 500 条向量 | 超过时自动分批（ingest.py 已处理） |
| 单文本 embedding | ≤ 8000 字符 | Titan v2 上限 8192 tokens，截断到 8000 |
| metadata 过滤字段 | ≤ 2048 bytes (UTF-8) | S3 Vectors filterable metadata 硬限制 |
| chunk_size | 推荐 512 tokens | 基于 Vecta 2026 benchmark 最优区间 |
| 索引维度 | 1024 | 当前使用 Titan Embed v2，切换模型需重建索引 |
