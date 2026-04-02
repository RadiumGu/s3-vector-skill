# PRD: S3 Vectors 知识库 Skill — 轻量级 RAG 管道

> 版本：v1.3 | 作者：架构审阅猫 | 日期：2026-03-28
>
> v1.3 更新：新增多 Agent 共享架构（§4.6）、部署拓扑（§5.2）
> v1.2 更新：新增新用户引导流程、Tag 分类体系、stats.py 知识库状态查询
> v1.1 更新：重构分块策略（基于 Vecta 2026 / NVIDIA 2024 / Anthropic Contextual Retrieval benchmark 数据）

---

## 1. 概述

为 `s3-vector-skill` 增加轻量级文档摄入（ingest）能力，使其成为 OpenClaw Agent 可直接使用的知识库工具。用户通过自然语言指令即可完成"存文档 → 搜知识"的完整 RAG 流程，无需手动切块或调用 embedding API。

### 1.1 目标用户

- OpenClaw Agent（通过 SKILL.md 自动调用脚本）
- 大乖乖及团队成员（通过 Slack/Telegram 对话触发）

### 1.2 不做什么

- ❌ 不做 PDF、Word、PPT 解析（复杂格式交给 Bedrock Knowledge Bases）
- ❌ 不做 Web Crawler（已有 `web_fetch`）
- ❌ 不做实时流式摄入（不是 Kinesis）
- ❌ 不做 Skill 路由（已删除）
- ❌ 不做 Semantic Chunking（benchmark 显示碎片化严重，准确率仅 54%，不如 recursive splitting）

---

## 2. 新用户引导流程

### 2.1 首次使用（对话式初始化）

新用户不需要任何技术背景，Agent 引导完成初始化：

```
用户："我想用知识库"

Agent："好的，我来帮你初始化知识库。
        给知识库起个名字？默认叫 openclaw-kb。"

用户："就默认的吧"

Agent：（自动执行 install.sh → 创建向量桶 + 索引）
      "✅ 知识库已创建。

       要不要给知识分个类？比如：
       • work — 工作技术文档
       • life — 生活日常
       • 不分类也行，所有文档放一起，搜索时全部搜"

用户："就 work 和 life 两个"

Agent："✅ 分类设好了。以后存文档时提一句是工作还是生活的就行，
        不说的话默认不分类。

        现在你可以：
        1. 发一个链接，我帮你存进去
        2. 指定一个文件夹，我批量导入
        3. 直接问问题，我会先搜知识库再回答"
```

### 2.2 完整用户旅程

```
新用户
  │
  ├─ Step 1："我想用知识库"
  │   └─ Agent 自动初始化（install.sh → 向量桶 + 索引）
  │   └─ Agent 询问分类需求 → 设定预定义 tags
  │
  ├─ Step 2：存文档（三种方式，自然语言触发）
  │   ├─ 发链接 → "把这个存到知识库 https://..."
  │   ├─ 指文件 → "把 /docs/ 下面的 md 文件都导入"
  │   └─ 强调重要 → "这篇很重要，仔细存一下" (自动 contextual 模式)
  │
  ├─ Step 3：日常使用（无感知）
  │   └─ 正常提问 → Agent 自动搜知识库 → 📚/🌐/🤖 标注来源
  │
  └─ Step 4：管理
      ├─ "知识库里有什么？" → stats.py（文档数、chunk 数、tag 分布）
      ├─ "删掉那篇旧文档"  → ingest.py --delete
      └─ "同步一下文档"    → ingest.py --sync
```

### 2.3 日常使用速查

**用户只需要记住这些自然语言指令：**

| 你想做的 | 怎么说 |
|---------|--------|
| 存一篇文档 | "把这个存到知识库" / "存一下这个链接" |
| 存工作文档 | "存到知识库，工作用的" |
| 存生活文档 | "这个是生活类的，存一下" |
| 重要文档精读 | "这篇很重要，仔细存" / "精读一下再存" |
| 批量导入 | "把 /docs/ 下面的文件都导入" |
| 搜索 | 直接问问题就行（Agent 自动搜） |
| 只搜工作知识 | "工作知识库里有没有关于 xxx 的" |
| 查看状态 | "知识库里有什么？" / "知识库状态" |
| 删除文档 | "删掉关于 xxx 的文档" |
| 同步更新 | "同步一下知识库" / "重新同步" |

---

## 3. 用户故事

## 3. 用户故事

### Story 1：存一篇技术文档

> 大乖乖："把这篇 AWS EKS Best Practices 存到知识库里"
>
> Agent 执行：`web_fetch` 抓取 → `ingest.py` 分块 + embedding → 写入 S3 Vectors
>
> Agent 回复："已入库，共 12 个 chunk，来源：docs.aws.amazon.com/eks/..."

### Story 2：批量导入本地文档

> 大乖乖："把 /home/ubuntu/tech/docs/ 下面所有 md 文件导入知识库"
>
> Agent 执行：`ingest.py --dir /home/ubuntu/tech/docs/ --glob "*.md"` → 扫描 → 分块 → 增量写入
>
> Agent 回复："扫描到 23 个文件，新增 156 个 chunk，跳过 3 个未变更文件"

### Story 3：语义搜索（带来源标注）

> 大乖乖："EKS Pod 调度失败一般怎么排查？"
>
> Agent 先搜知识库 → 有结果则基于知识库回答 → 回复中明确标注来源
>
> Agent 回复：
> ```
> 📚 以下回答基于知识库检索：
>
> Pod 调度失败常见原因：
> 1. Insufficient CPU/Memory — 节点资源不足
> 2. nodeSelector/affinity 不匹配
> 3. taint/toleration 配置错误
>
> 来源：
> [1] /docs/eks-troubleshooting.md (chunk 3/8, 相似度 0.89)
> [2] https://docs.aws.amazon.com/eks/scheduling.html (chunk 5/12, 相似度 0.82)
> ```
>
> 如果知识库没有相关内容，Agent 会标注不同来源：
> ```
> 🌐 知识库中未找到相关内容，以下来自网络搜索：
> ...
>
> 🤖 知识库和网络均未找到，以下是我的理解：
> ...
> ```

### Story 4：增量更新

> 大乖乖："重新同步一下知识库"
>
> Agent 执行：`ingest.py --dir ... --sync` → 对比 content hash → 只更新变更的 chunk，删除已移除文件的 chunk
>
> Agent 回复："更新 5 个 chunk，删除 8 个过期 chunk，跳过 143 个未变更"

### Story 5：重要文档精读入库

> 大乖乖："这篇文档很重要，仔细存一下"
>
> Agent 判断：用户强调"重要" / "仔细" → 自动启用 contextual 模式
>
> Agent 执行：`ingest.py --file doc.md --contextual` → 分块 → LLM 生成上下文前缀 → embedding → 写入
>
> Agent 回复："已精读入库，共 8 个 chunk，每个都加了上下文摘要，搜索更准"

### Story 6：删除知识

> 大乖乖："把关于 Terraform 的文档从知识库里删掉"
>
> Agent 执行：`ingest.py --delete --doc-id "terraform-guide"`
>
> Agent 回复："已删除 18 个 chunk"

### Story 7：查看知识库状态

> 大乖乖："知识库里有什么？"
>
> Agent 执行：`stats.py --bucket openclaw-kb --index docs-v1`
>
> Agent 回复：
> ```
> 📊 知识库状态：
>
> 文档数：5
> Chunk 总数：47
> 总 tokens：~18,200
>
> 按分类：
>   work: 3 篇 (32 chunks)
>   life: 1 篇 (8 chunks)
>   未分类: 1 篇 (7 chunks)
>
> 最近入库：
>   [work] eks-troubleshooting.md — 12 chunks (2026-03-28)
>   [life] travel-okinawa.md — 8 chunks (2026-03-28)
> ```

---

## 4. Tag 分类体系

### 4.1 设计原则

- **预定义 tag 列表**：避免泛滥，Agent 将用户的自然语言描述映射到标准 tag
- **可扩展**：用户可以随时添加新 tag（通过对话或配置文件）
- **不强制**：不指定 tag 的文档正常入库，搜索时默认全搜
- **单 tag**：每个文档一个主分类 tag（简单清晰，不搞多标签）

### 4.2 Tag 配置

Tag 定义存储在 `config/tags.json`：

```json
{
  "tags": {
    "work": {
      "label": "工作",
      "keywords": ["工作", "技术", "AWS", "EKS", "文档", "方案", "架构", "代码", "部署"],
      "description": "工作技术文档、架构方案、运维手册"
    },
    "life": {
      "label": "生活",
      "keywords": ["生活", "旅游", "美食", "购物", "健康", "日常"],
      "description": "生活日常、旅游攻略、个人笔记"
    },
    "ops": {
      "label": "运维",
      "keywords": ["运维", "故障", "排查", "RCA", "报警", "监控", "incident"],
      "description": "运维手册、故障排查、RCA 报告"
    },
    "learning": {
      "label": "学习",
      "keywords": ["学习", "课程", "读书", "笔记", "教程", "tutorial"],
      "description": "学习笔记、课程资料、读书摘要"
    }
  },
  "default_tag": null,
  "allow_custom": false
}
```

### 4.3 Agent Tag 映射逻辑

Agent 根据用户的自然语言描述自动选择 tag：

```
用户说的               → Agent 选的 tag
─────────────────────────────────────
"工作用的"             → work
"这是技术文档"          → work
"生活类的"             → life
"旅游攻略"             → life
"运维手册"             → ops
"故障排查"             → ops
"学习笔记"             → learning
"存到知识库"（不说类别）  → 无 tag
```

### 4.4 Tag 管理

用户通过自然语言管理 tag，Agent 操作 `config/tags.json`：

**添加 tag：**
```
用户："加一个 finance 分类，用于理财投资相关的"

Agent：修改 config/tags.json，新增：
  "finance": {
    "label": "理财",
    "keywords": ["理财", "投资", "基金", "股票", "账单"],
    "description": "理财投资、账单管理"
  }

Agent 回复："✅ 已添加分类 finance（理财），关键词：理财、投资、基金、股票、账单"
```

**删除 tag：**
```
用户："把 learning 分类删掉，用不上"

Agent：从 config/tags.json 删除 "learning" 条目
       ⚠️ 但已入库文档的 tag 不受影响（metadata 中的 tags 字段不变）

Agent 回复："✅ 已删除分类 learning。
            注意：已入库的 2 篇 learning 文档不受影响，搜索时仍可通过 tag 过滤。
            需要把它们改到其他分类吗？"
```

**修改 tag 关键词：**
```
用户："work 分类加上 terraform 和 docker 这两个关键词"

Agent：在 config/tags.json 的 work.keywords 中追加 "terraform", "docker"

Agent 回复："✅ work 分类关键词已更新，现在包含：工作、技术、AWS、EKS、...、terraform、docker"
```

**查看所有 tag：**
```
用户："现在有哪些分类？"

Agent 执行：stats.py --tags
Agent 回复：
  "当前分类：
   • work（工作）— 3 篇 32 chunks
   • life（生活）— 1 篇 8 chunks
   • ops（运维）— 0 篇
   • 未分类 — 1 篇 7 chunks"
```

**重新分类已有文档：**
```
用户："把 REVIEW-2026-03-28 改成 ops 分类"

Agent：
  1. 读取该文档所有 chunk 的 metadata
  2. 更新 tags 字段为 "ops"
  3. 重新写入（delete + put）

Agent 回复："✅ REVIEW-2026-03-28（8 chunks）已从 petsite 改为 ops"
```

### 4.5 Tag 管理规则

| 规则 | 说明 |
|------|------|
| **支持中文 tag 名** | 用户说什么就存什么（"架构韧性"→ tag 名就是"架构韧性"） |
| tag 名称允许中文、英文、数字、连字符 | 不强制英文，UTF-8 存储 |
| 不能删除有文档的 tag | Agent 会提醒先迁移文档或确认保留孤立 tag |
| 新增 tag 时必须提供至少 2 个关键词 | 保证 Agent 能正确映射 |
| Agent 不会自动发明新 tag | 遇到无法映射的描述时，询问用户归类或不打 tag |

### 4.6 多 Agent 共享架构

知识库采用**单实例共享**模型：所有 Agent 共享同一个 S3 向量桶、同一个索引、同一份 tag 配置。

#### 架构图

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ 日常小乖乖   │  │ 通用技术猫   │  │ 架构审阅猫   │  ... 其他 Agent
│ workspace-  │  │ workspace-  │  │ workspace-  │
│ daily       │  │ general-tech│  │ doc-reviewer│
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       │  symlink       │  symlink       │  symlink
       ▼                ▼                ▼
┌──────────────────────────────────────────────────┐
│        /home/ubuntu/tech/s3-vector-skill/         │
│                                                   │
│  SKILL.md          ← 所有 Agent 读同一份指引       │
│  config/tags.json  ← 所有 Agent 共享 tag 定义      │
│  scripts/*.py      ← 所有 Agent 调用同一套脚本      │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│         S3 Vectors: openclaw-kb / docs-v1         │
│                                                   │
│  所有 Agent 存入的文档都在同一个索引里               │
│  通过 tag 区分类别，不做 Agent 级隔离               │
└──────────────────────────────────────────────────┘
```

#### 共享范围

| 资源 | 共享方式 | 说明 |
|------|---------|------|
| S3 向量桶 `openclaw-kb` | 全局唯一 | 所有 Agent 读写同一个桶 |
| 索引 `docs-v1` | 全局唯一 | 所有文档在同一个索引 |
| `config/tags.json` | 文件共享（symlink） | 任一 Agent 修改，所有 Agent 立即生效 |
| `SKILL.md` | 文件共享（symlink） | 搜索指引、来源标注规范统一 |
| 脚本 `scripts/*.py` | 文件共享（symlink） | 代码更新一次，所有 Agent 同步 |

#### 部署方式

每个需要知识库的 Agent workspace 创建一个软链接：

```bash
# 格式
ln -s /home/ubuntu/tech/s3-vector-skill \
  ~/.openclaw/workspace-<NAME>/skills/s3-vector-bucket

# 示例：为 3 个 Agent 配置
ln -s /home/ubuntu/tech/s3-vector-skill ~/.openclaw/workspace-daily/skills/s3-vector-bucket
ln -s /home/ubuntu/tech/s3-vector-skill ~/.openclaw/workspace-general-tech/skills/s3-vector-bucket
ln -s /home/ubuntu/tech/s3-vector-skill ~/.openclaw/workspace-doc-reviewer/skills/s3-vector-bucket
```

#### 隔离策略

当前版本**不做 Agent 级数据隔离**，理由：

1. **单用户场景**：只有大乖乖一个人用，Agent 之间不存在权限边界
2. **跨 Agent 搜索是特性不是 bug**：日常小乖乖存的生活文档，通用技术猫也能搜到（如果需要的话）
3. **Tag 已提供逻辑隔离**：通过 tag 过滤可以实现"只搜工作知识"的效果

如果将来需要 Agent 级隔离（多用户场景），可以：
- **轻量方案**：给每个 Agent 分配独立 tag 前缀（如 `daily:life`、`reviewer:ops`）
- **完全隔离**：每个 Agent 使用独立索引（`daily-v1`、`reviewer-v1`）

#### 不适合配置此 Skill 的 Agent

| Agent | 理由 |
|-------|------|
| 编程猫 | 写代码不需要搜知识库，额外的 SKILL.md 注入增加 prompt 长度 |
| 招财猫 | 投资场景与知识库无关 |
| main | 空 workspace |

---

## 5. 架构设计

```
┌──────────────────────────────────────────────────────┐
│                    OpenClaw Agent                      │
│  用户消息 → SKILL.md 匹配 → 调用对应脚本               │
└──────────┬────────────────────────┬───────────────────┘
           │ 写入                    │ 查询
           ▼                        ▼
┌─────────────────────┐  ┌─────────────────────────────┐
│     ingest.py       │  │        search.py            │
│                     │  │                             │
│ 1. 读取文件/文本     │  │ 1. 用户 query → embedding   │
│ 2. 分块 (chunking)  │  │ 2. S3 Vectors 相似度搜索    │
│ 3. [可选] 上下文前缀 │  │ 3. 返回 Top-K + 原文摘要    │
│ 4. 提取元数据        │  │                             │
│ 5. 生成 embedding   │  └──────────────┬──────────────┘
│ 6. 写入 S3 Vectors  │               │
└──────────┬──────────┘               │
           │                          │
           ▼                          ▼
┌──────────────────────────────────────────────────────┐
│              Amazon S3 Vectors (ap-northeast-1)       │
│                                                       │
│  向量桶: openclaw-kb                                   │
│  索引:   docs-v1 (1024d, cosine)                      │
│                                                       │
│  每个 vector:                                         │
│    key:      "{doc_id}.chunk-{seq}"                   │
│    data:     float32[1024] (Titan v2)                 │
│    metadata: {                                        │
│      doc_id, title, source, chunk_index, total_chunks,│
│      content (原文, ≤2000 chars), content_hash,       │
│      context_prefix (可选, ≤500 chars),               │
│      heading_path (Markdown 层级链),                   │
│      file_type, tags, ingested_at                     │
│    }                                                  │
└──────────────────────────────────────────────────────┘
```

### 5.1 数据流

**标准摄入流程：**
```
输入（文件/URL/文本）
  → 格式检测（md/txt/html）
  → 文本提取（HTML: BeautifulSoup → 纯文本）
  → 分块（策略自动选择，见 4.3）
  → 元数据填充（title, source, hash, heading_path, timestamp）
  → Bedrock Titan v2 embedding（复用 embed.py, 带缓存）
  → S3 Vectors PutVectors（批量写入）
```

**Contextual 摄入流程（`--contextual`）：**
```
输入 → 格式检测 → 文本提取 → 分块
  → 对每个 chunk 调用 Bedrock Claude：
    "给定完整文档和以下片段，用 2-3 句话描述这个片段在文档中的位置和上下文"
  → context_prefix + content 拼接后生成 embedding
  → 写入 S3 Vectors（metadata 同时存 context_prefix 和 content）
```

**搜索流程：**
```
用户 query
  → Bedrock Titan v2 embedding
  → S3 Vectors QueryVectors (top-k, return metadata)
  → 格式化输出（原文摘要 + 来源 + 分数 + 上下文前缀）
```

---

## 6. 核心功能规格

### 6.1 ingest.py — 文档摄入

```bash
# 单文件摄入
python3 scripts/ingest.py \
  --bucket openclaw-kb \
  --index docs-v1 \
  --file /path/to/document.md \
  [--doc-id "custom-id"] \
  [--source "https://original-url"] \
  [--tags "eks,kubernetes"] \
  [--contextual]

# 目录批量摄入
python3 scripts/ingest.py \
  --bucket openclaw-kb \
  --index docs-v1 \
  --dir /path/to/docs/ \
  [--glob "*.md"] \
  [--sync] \
  [--dry-run]

# stdin 摄入（配合 web_fetch 或其他管道）
echo "文本内容..." | python3 scripts/ingest.py \
  --bucket openclaw-kb \
  --index docs-v1 \
  --doc-id "web-article-001" \
  --source "https://example.com/article"

# 删除文档的所有 chunk
python3 scripts/ingest.py \
  --bucket openclaw-kb \
  --index docs-v1 \
  --delete --doc-id "old-document"
```

**参数：**

| 参数 | 必需 | 默认值 | 说明 |
|------|:---:|--------|------|
| `--bucket` | ✅ | — | S3 向量桶名称 |
| `--index` | ❌ | `docs-v1` | 索引名称 |
| `--file` | ✅* | — | 单文件路径（与 `--dir` / stdin 三选一） |
| `--dir` | ✅* | — | 目录路径（批量摄入） |
| `--glob` | ❌ | `*.md,*.txt,*.html` | 文件匹配模式 |
| `--doc-id` | ❌ | 自动生成（文件名 hash） | 文档标识符 |
| `--source` | ❌ | 文件路径 | 来源标识（URL 或描述） |
| `--tags` | ❌ | — | 逗号分隔标签，写入 metadata |
| `--chunk-size` | ❌ | `512` | 目标 chunk 大小（tokens） |
| `--chunk-overlap` | ❌ | `64` | chunk 重叠 tokens（~12% overlap） |
| `--chunking` | ❌ | `auto` | 分块策略：`auto` / `recursive` / `heading` |
| `--contextual` | ❌ | false | 启用 Contextual Chunking（LLM 生成上下文前缀，提升召回率 35-49%，成本增加） |
| `--contextual-model` | ❌ | `anthropic.claude-3-haiku-20240307-v1:0` | Contextual prefix 使用的 LLM 模型 |
| `--sync` | ❌ | false | 增量同步：对比 hash，跳过未变更，删除已移除 |
| `--delete` | ❌ | false | 删除指定 doc-id 的所有 chunk |
| `--dry-run` | ❌ | false | 只输出计划，不执行写入 |

### 6.2 search.py — 语义搜索

```bash
python3 scripts/search.py \
  --bucket openclaw-kb \
  --index docs-v1 \
  --query "EKS Pod 调度失败排查" \
  --top-k 5 \
  [--output markdown|json] \
  [--filter '{"file_type": {"$eq": "md"}}'] \
  [--threshold 0.6]
```

**输出示例（markdown）：**
```markdown
### 搜索结果：Top 5 for "EKS Pod 调度失败排查"

**1. [0.89] EKS Troubleshooting Guide — Pod Scheduling**
来源：/docs/eks-troubleshooting.md (chunk 3/8)
上下文：本段来自 EKS 故障排查指南第 3 章，讨论 Pod 调度失败的常见原因和诊断步骤。
> 当 Pod 处于 Pending 状态时，首先检查 kubectl describe pod 的 Events 部分。
> 常见原因：Insufficient CPU/Memory、nodeSelector 不匹配、taint/toleration...

**2. [0.82] Kubernetes 调度器原理**
来源：https://docs.aws.amazon.com/eks/scheduling.html (chunk 5/12)
> kube-scheduler 按以下顺序评估节点：filtering → scoring → binding...
```

### 6.3 stats.py — 知识库状态查询

```bash
# 完整状态
python3 scripts/stats.py --bucket openclaw-kb --index docs-v1

# 只看 tag 分布
python3 scripts/stats.py --bucket openclaw-kb --index docs-v1 --tags
```

**输出示例（JSON）：**
```json
{
  "success": true,
  "action": "stats",
  "bucket": "openclaw-kb",
  "index": "docs-v1",
  "total_docs": 5,
  "total_chunks": 47,
  "tags": {
    "work": { "docs": 3, "chunks": 32 },
    "life": { "docs": 1, "chunks": 8 },
    "untagged": { "docs": 1, "chunks": 7 }
  },
  "recent": [
    { "doc_id": "eks-troubleshooting", "tag": "work", "chunks": 12, "ingested_at": "2026-03-28" },
    { "doc_id": "travel-okinawa", "tag": "life", "chunks": 8, "ingested_at": "2026-03-28" }
  ]
}
```

**参数：**

| 参数 | 必需 | 默认值 | 说明 |
|------|:---:|--------|------|
| `--bucket` | ✅ | — | S3 向量桶名称 |
| `--index` | ❌ | `docs-v1` | 索引名称 |
| `--tags` | ❌ | false | 只输出 tag 分布 |
| `--output` | ❌ | `json` | 输出格式：`json` / `markdown` |

### 6.4 分块策略体系

#### 策略选择逻辑（`--chunking auto`）

```
auto 模式决策树：

输入文件
├── 是 Markdown 且包含 ≥3 个 heading？
│   └── YES → heading-aware recursive splitting
│   └── NO  → 纯 recursive character splitting
├── 是 HTML？
│   └── BeautifulSoup 提取正文 → 视为纯文本 → recursive splitting
└── 是 .txt / .csv / 代码？
    └── recursive character splitting
```

#### 策略一：Recursive Character Splitting（默认）

**Benchmark 依据：Vecta 2026 评测 7 种策略，recursive 512-token 准确率 69%，排名第一。**

```
算法流程：
1. 按分隔符优先级递归分割：
   "\n\n"（段落） → "\n"（换行） → ". "（句号） → " "（空格） → ""（字符）
2. 每次分割后检查 chunk 大小：
   - 小于 chunk_size → 与下一段合并
   - 大于 chunk_size → 用更细的分隔符继续分割
3. 相邻 chunk 保留 overlap 重叠区（默认 64 tokens ≈ 12%）
4. 每个 chunk 保证 ≥ 100 tokens（避免碎片）

参数：
  chunk_size:    512 tokens（默认，Vecta benchmark 最优区间 400-512）
  chunk_overlap:  64 tokens（~12%，NVIDIA benchmark 推荐 10-20%）
  min_chunk:     100 tokens（碎片过滤阈值）
```

#### 策略二：Heading-Aware Recursive Splitting（Markdown 专用）

**在 recursive splitting 基础上增加 Markdown 结构感知。**

```
算法流程：
1. 解析 Markdown heading 层级（#, ##, ###, ####）
2. 构建 heading 树，每个 section 作为初始分割单元
3. 对每个 section：
   - 小于 chunk_size → 保持为单个 chunk
   - 大于 chunk_size → 内部用 recursive splitting 二次分割
4. 每个 chunk 自动添加 heading_path 元数据：
   "# EKS Guide > ## Troubleshooting > ### Pod Scheduling"
5. heading_path 也作为 chunk 内容的前缀参与 embedding
   → 搜索 "Pod 调度" 时，heading 上下文帮助匹配到正确的章节

优势（对比纯 recursive）：
  - 不会跨 section 边界切割（语义完整性）
  - heading_path 提供层级上下文（无需 LLM 即可增强）
  - 对结构化文档（技术手册、API 文档）效果显著

参数：同 recursive，额外参数：
  heading_levels: [1, 2, 3, 4]（参与分割的 heading 层级）
```

#### 策略三：Contextual Chunking（可选增强，`--contextual`）

**Benchmark 依据：Anthropic Contextual Retrieval 研究，召回率提升 35-49%。**

```
算法流程（在策略一或二完成分块后执行）：
1. 对每个 chunk，构造 prompt 发送给 LLM：
   ┌────────────────────────────────────────┐
   │ <document>                              │
   │ {{WHOLE_DOCUMENT}}                      │
   │ </document>                             │
   │                                         │
   │ 以下是文档中的一个片段：                   │
   │ <chunk>                                 │
   │ {{CHUNK_CONTENT}}                       │
   │ </chunk>                                │
   │                                         │
   │ 请用 2-3 句简短的话描述这个片段在文档中的    │
   │ 位置和上下文，帮助读者理解它属于哪部分、      │
   │ 讨论什么主题。只输出描述，不要解释。         │
   └────────────────────────────────────────┘
2. LLM 返回 context_prefix（通常 50-100 tokens）
3. Embedding 输入 = context_prefix + "\n\n" + chunk_content
4. metadata 分别存储 context_prefix 和 content
5. 搜索时返回 context_prefix 作为摘要

成本：
  - 使用 Haiku（最便宜）：~$0.00025/chunk（input）+ ~$0.00125/chunk（output）
  - 100 篇文档 × 30 chunks ≈ 3000 chunks × $0.0015 ≈ $4.5（一次性）
  - 对比标准模式 $0.015，贵 300x，但召回率提升 35-49%

适用场景：
  - 重要的参考文档（需要高召回率）
  - 文档内部结构不清晰（纯文本、会议记录）
  - 多主题混合的长文档
```

#### 策略对比总结

| 策略 | 准确率 | 额外成本 | 依赖 | 适用场景 |
|------|--------|---------|------|---------|
| **Recursive splitting** | 69%（Vecta） | 零 | 无 | 默认，所有文档 |
| **Heading-aware** | ~75%（估算） | 零 | 无 | Markdown 有 heading 结构 |
| **+ Contextual prefix** | +35-49%（Anthropic） | ~$0.0015/chunk（Haiku） | Bedrock Claude | 重要文档、高召回需求 |
| ~~Semantic chunking~~ | 54%（Vecta） | 高（每句 embedding） | — | **不采用**：碎片化严重 |

### 6.5 增量同步机制

```
对于 --sync 模式：

1. 扫描目标目录所有匹配文件
2. 计算每个文件的 content_hash (MD5)
3. 从 S3 Vectors 列出该 doc_id 的已有 chunk，读取 metadata.content_hash
4. 对比：
   - hash 相同 → 跳过（不重新 embedding）
   - hash 不同 → 删除旧 chunk，重新分块 + 写入
   - 文件已删除 → 删除对应 chunk
5. 输出同步报告
```

### 6.6 向量 key 命名规范

```
{doc_id}.chunk-{seq:04d}

示例：
  eks-best-practices.chunk-0000
  eks-best-practices.chunk-0001
  web-article-abc123.chunk-0000
```

`doc_id` 生成规则：
- `--doc-id` 明确指定 → 直接使用
- `--file` → 文件名（去扩展名，特殊字符替换为 `-`）
- `--dir` → 相对路径（`/` 替换为 `-`，去扩展名）

---

## 7. 与 OpenClaw Agent 的集成

### 7.1 知识库检索触发机制

Agent 何时主动搜索知识库？有两种实现方案：

#### 方案 A：SKILL.md 强指引（当前采用 ✅）

通过 SKILL.md 中的明确指令，引导 LLM 在回答问题前先搜知识库。

```
优点：零开发，SKILL.md 写好即可
缺点：LLM 不一定每次都遵循（实测约 80-90% 遵循率）
触发方式：LLM 读到 SKILL.md 中的指引后自主决定调用 search.py
```

SKILL.md 中的关键指引：
```markdown
## 回答问题前，优先检索知识库

当用户提问且问题可能在知识库中有答案时，先执行：
python3 {baseDir}/scripts/search.py --bucket openclaw-kb --index docs-v1 --query "用户问题" --top-k 3

- 有结果（score ≥ 0.6）→ 基于知识库回答，标注 📚 来源
- 无结果 → 用 web_search 或自身知识回答，标注 🌐 或 🤖
```

#### 方案 B：Plugin Hook（未来可选升级）

通过 OpenClaw `before_prompt_build` hook，每条消息到达前**代码级强制**搜索知识库，将结果注入 system prompt。

```
优点：100% 保证每条消息都经过知识库检索
缺点：需要开发 OpenClaw Plugin（~200 行 JS），增加每条消息的延迟（embedding + 查询 ~200ms）
触发方式：Plugin 自动执行，不依赖 LLM 判断
```

实现方式：
```javascript
// before_prompt_build hook
async function beforePromptBuild({ messages }) {
  const userQuery = extractLastUserMessage(messages);
  const results = await searchKnowledgeBase(userQuery, { topK: 3, threshold: 0.6 });
  if (results.length > 0) {
    return { prependContext: formatAsContext(results) };
  }
  return {};
}
```

**当前决策：采用方案 A。** 如果实际使用中发现 Agent 遗漏搜索的频率过高（>20%），再升级到方案 B。

### 7.2 SKILL.md 更新

在现有 SKILL.md 的 triggers 中增加：

```yaml
triggers:
  - 知识库
  - knowledge base
  - 存到知识库
  - 搜索知识库
  - ingest
  - 导入文档
```

在能力描述中增加：

```markdown
## 知识库管理

| 能力 | 脚本 | 说明 |
|------|------|------|
| 文档摄入 | `ingest.py` | 分块 + embedding + 写入 |
| 语义搜索 | `search.py` | query embedding + 相似度搜索 |
```

### 7.3 Agent 回答来源标注规范

Agent 回答时**必须标注信息来源**，用户一眼能区分：

| 图标 | 含义 | 触发条件 |
|------|------|---------|
| 📚 | **知识库** | search.py 返回 ≥1 条结果且相似度 ≥ 0.6 |
| 🌐 | **网络搜索** | 知识库无结果，fallback 到 web_search |
| 🤖 | **模型自身知识** | 知识库和网络都没有相关内容 |
| 📚+🌐 | **知识库 + 网络补充** | 知识库有部分结果，网络补充了额外信息 |

**回答格式模板：**
```
📚 以下回答基于知识库：

[正文内容]

来源：
[1] 文件名或URL (chunk X/Y, 相似度 0.XX)
[2] ...
```

**Agent 决策流程：**
```
用户提问
  → 1. 先搜知识库（search.py --top-k 3）
  → 2. 有高质量结果（score ≥ 0.6）？
       YES → 📚 基于知识库回答，附来源
       NO  → 3. web_search 补充？
             YES → 🌐 基于网络回答
             NO  → 🤖 基于模型知识回答
```

### 7.4 Agent 使用流程

**场景 A：用户发 URL，Agent 自动入库**

```
用户："把这个存到知识库 https://docs.aws.amazon.com/eks/latest/userguide/pod-scheduling.html"

Agent 内部步骤：
1. web_fetch(url) → 获取 markdown 内容
2. 写入临时文件 /tmp/ingest-xxx.md
3. exec: python3 scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
         --file /tmp/ingest-xxx.md --source "https://docs.aws.amazon.com/..." --tags "eks"
4. 回复用户摄入结果
```

**场景 B：用户提问，Agent 先搜知识库再回答**

```
用户："EKS 节点扩容的最佳实践是什么？"

Agent 内部步骤：
1. exec: python3 scripts/search.py --bucket openclaw-kb --index docs-v1 \
         --query "EKS node scaling best practices" --top-k 3 --output json
2. 将搜索结果作为上下文
3. 结合自身知识 + 搜索结果，给出回答并标注来源
```

**场景 C：重要文档精读入库**

```
用户："这个 Well-Architected Review 报告很重要，仔细存一下"

Agent 判断逻辑：
  - 关键词匹配："重要" / "仔细" / "精读" / "高质量" → 自动加 --contextual
  - 普通请求："存到知识库" → 标准模式

Agent 内部步骤：
1. exec: python3 scripts/ingest.py --bucket openclaw-kb --index docs-v1 \
         --file report.md --contextual --tags "war,architecture"
2. 回复："已精读入库，共 15 个 chunk，每个都加了上下文摘要"
```

---

## 8. 依赖和前置条件

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | >= 3.10 | 运行时 |
| boto3 | 最新版 | S3 Vectors + Bedrock |
| beautifulsoup4 | >= 4.12 | HTML 正文提取 |
| tiktoken（可选） | >= 0.7 | 精确 token 计数（无则按字符估算，1 token ≈ 4 chars） |

**AWS 权限：**
- `s3vectors:*`（向量桶 CRUD）
- `bedrock:InvokeModel`（Titan v2 embedding + Claude Haiku for contextual）

**已有资源复用：**
- `embed.py` — embedding 生成（含磁盘缓存）
- `put_vectors.py` — 向量写入
- `query_vectors.py` — 向量查询
- `delete_vectors.py` — 向量删除
- `common.py` — CLI 参数解析、错误处理

---

## 9. 成本估算

以 100 篇技术文档（平均 3000 tokens/篇，约 3000 chunks）为例：

### 标准模式

| 项目 | 计算 | 费用 |
|------|------|------|
| S3 Vectors 存储 | 3000 chunks × 1024d × 4B ≈ 12MB | ~$0.003/月 |
| S3 Vectors 查询 | ~1000 次/月 | ~$0.001/月 |
| Bedrock Embedding（首次摄入） | 3000 chunks × ~500 tokens | ~$0.015 一次性 |
| Bedrock Embedding（查询） | 1000 queries × ~50 tokens | ~$0.0005/月 |
| **合计** | | **< $0.02/月** |

### Contextual 模式（额外成本）

| 项目 | 计算 | 费用 |
|------|------|------|
| Claude Haiku 生成 context_prefix | 3000 chunks × (~2000 input + ~100 output tokens) | ~$4.50 一次性 |
| **合计（含标准成本）** | | **~$4.52 一次性 + $0.005/月** |

对比 Bedrock Knowledge Bases（OpenSearch Serverless 最低 ~$175/月），标准模式**成本低 4 个数量级**。

---

## 10. 里程碑

| 阶段 | 内容 | 状态 | 预估 |
|------|------|------|------|
| **M1** | `chunker.py` 模块：recursive splitting + heading-aware splitting + 策略自动选择 | ✅ 完成 | 2h |
| **M2** | `ingest.py`：单文件/stdin/目录批量 + 分块 + embedding + 写入 + sync + delete | ✅ 完成 | 4h |
| **M3** | `search.py`：语义搜索 + markdown/json 输出 + 原文摘要 + 来源标注 | ✅ 完成 | 1h |
| **M4** | `stats.py`：知识库状态查询（文档数、chunk 数、tag 分布、最近入库） | ✅ 完成 | 1h |
| **M5** | Tag 分类体系：`config/tags.json` + `manage_tags.py`（增删改查 + 重新分类） | ✅ 完成 | 1h |
| **M6** | `contextual.py` 模块：LLM 上下文前缀生成 + `--contextual` flag（已内联在 ingest.py） | ✅ 完成 | 1.5h |
| **M7** | HTML 支持（BeautifulSoup，已内联在 ingest.py） | ✅ 完成 | 0.5h |
| **M8** | SKILL.md 更新 + README 更新 + 端到端测试 | ✅ 完成 | 1h |

**总计：约 12 小时（全部完成 ✅）**

---

## 11. 风险和限制

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| S3 Vectors metadata 大小限制 | 原文过长无法完整存入 metadata | 截断到 2000 chars，存 `content_preview` |
| Bedrock Titan v2 限流 | 大量文档同时摄入时 429 | embed.py 已有重试 + jitter，批次间加延迟 |
| S3 Vectors 服务成熟度 | 2025 底 GA，API 可能变化 | 关注 boto3 changelog，用 common.py 封装调用 |
| Contextual 模式 LLM 成本 | 大批量文档摄入时 Haiku 费用累积 | 默认关闭，仅重要文档手动启用；dry-run 预估成本 |
| 无引用溯源高亮 | 不像 Bedrock KB 能精确定位原文位置 | 返回 chunk 原文 + heading_path + 来源 URL |
| tiktoken 不可用 | token 计数不精确 | 降级为字符估算（1 token ≈ 4 chars），chunk 大小可能有 ±15% 偏差 |

---

## 12. 技术决策记录

### 12.1 为什么不用 Semantic Chunking

Vecta 2026 benchmark 中 semantic chunking 仅 54% 准确率（7 种策略中倒数第二），原因是产生了大量碎片 chunk（平均 43 tokens），embedding 质量下降。Recursive splitting 以 69% 准确率排名第一，且实现简单、无额外依赖。

### 12.2 为什么选择 512 tokens 而非更大的 chunk

- Vecta benchmark 最优区间 400-512 tokens
- Chroma 2025 context rot 研究：上下文越长，检索性能越差（即使 GPT-4.1、Claude 4 也受影响）
- 更小的 chunk → 更精确的匹配 → 更好的 Top-K 召回
- Overlap 64 tokens（12%）足以保持跨块连续性

### 12.3 Contextual Chunking 为什么用 Haiku

- Anthropic 原始研究用 Claude 3.5 Sonnet，但 context prefix 任务简单（2-3 句描述）
- Haiku 成本仅 Sonnet 的 1/12，生成质量对此任务足够
- 仍然保留 `--contextual-model` 参数允许用户切换

### 12.4 为什么用 Tags 而非多索引分类

- 用户知识库规模短期 < 1000 条向量，单索引 + tag 过滤足够
- 很多问题跨类别（"EKS 部署问题" 可能同时和 work/ops 相关），全搜比指定类别更实用
- tags 方案零额外成本，不用管理多个索引
- 将来量大需要物理隔离时，可按 tag 导出到独立索引，迁移成本低

### 12.5 为什么用预定义 Tag 列表而非自由标签

- 自由标签必然导致泛滥（work/Work/工作/job 指同一件事）
- 预定义列表 + Agent 关键词映射 = 标签始终可控
- `config/tags.json` 让用户可以通过对话扩展，但 Agent 不会自己发明新 tag
- `allow_custom: false` 默认禁止自定义 tag，避免初期混乱

### 12.6 为什么允许中文 Tag 名

- 用户说中文是最自然的交互方式，不需要记英文翻译
- S3 Vectors metadata 支持 UTF-8，中文 tag 技术上无障碍
- 避免 Agent 翻译不一致（"架构韧性" 可能翻译成 architecture-resilience 或 arch-resilience）
- tag 名 = 用户说的原话，零认知负担
