# Amazon S3 向量桶全功能管理 Skill

> Amazon S3 Vectors 全功能管理 OpenClaw Skill，覆盖向量桶、索引、向量数据的全生命周期管理，共 **16 个核心能力**。
> 基于 Amazon S3 Vectors（re:Invent 2025 GA），比传统向量数据库降低 **90%** 成本。

---

## ✨ 功能概览

| 类别 | 能力 |
|------|------|
| **向量桶管理** | 创建、删除、查询、列出向量桶 |
| **桶策略管理** | 设置、获取、删除桶策略 |
| **索引管理** | 创建、查询、列出、删除向量索引 |
| **向量数据操作** | 插入/更新、获取、列出、删除向量 |
| **相似度搜索** | Top-K 语义搜索，支持元数据过滤 |
| **Skill 路由（降本工具）** | 离线建库 + 在线路由 + Hook，Token 节省 **~91%** |

> 📖 完整 CLI 命令参考 → [references/cli-reference.md](references/cli-reference.md)

---

## 🚀 快速开始

### 前置条件

- Python 3.8+
- boto3（AWS Python SDK）

```bash
pip3 install boto3 --upgrade
```

### 准备凭证

支持以下三种认证方式（优先级从高到低）：

**方式 1：实例 IAM Role（推荐，EC2/EKS 上自动生效）**

绑定具有 `s3vectors:*` 权限的 IAM Role 即可，无需任何额外配置。

**方式 2：环境变量**

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="ap-northeast-1"
```

**方式 3：AWS Profile**

```bash
aws configure --profile my-profile
# 脚本中通过 --profile my-profile 使用
```

### 安装到 OpenClaw

```bash
# 方式 1：手动复制到 Skill 目录
cp -r s3-vector-skill ~/.openclaw/workspace-<agent>/skills/s3-vector-bucket

# 方式 2：Git 子模块（团队协作推荐）
git submodule add https://github.com/RadiumGu/s3-vector-skill .openclaw/skills/s3-vector-bucket
```

安装后，在 OpenClaw 对话中使用自然语言即可触发：

| 你说 | AI 自动执行 |
|------|------------|
| "帮我创建一个 S3 向量桶" | 调用 `create_vector_bucket.py` |
| "创建一个 1024 维的向量索引" | 调用 `create_index.py` |
| "插入 5 条测试向量数据" | 调用 `put_vectors.py` |
| "搜索和这段文本最相似的向量" | 调用 `query_vectors.py` |

**Skill 触发关键词：**
`vector bucket` · `vector index` · `vector search` · `向量桶` · `向量索引` · `向量搜索` · `向量存储` · `插入向量` · `相似度搜索` · `S3 vector` · `S3 vectors`

---

## 🧭 Skill 路由（Token 降本 ~91%）

> **灵感来源**：Amazon S3 Vectors 原生实现的 Skill 路由方案。
> 将单轮对话 Skill 相关 Token 从 ~4867 降至 ~430（节省 **~91%**）。

### 原理

OpenClaw 每轮对话都会将所有 Skill 描述注入 LLM 上下文，Skill 越多消耗越高。
Skill 路由的思路是：只注入**最相关的 Top-5 Skill**，其余忽略。

```
[离线建库]
所有 SKILL.md 描述文本
    → Bedrock Titan Embeddings v2（1024维）
    → S3 Vectors 向量索引

[在线路由]
用户消息（未来: message:received hook）
    → 相同 Embedding 模型
    → S3 Vectors Cosine 相似度搜索
    → Top-5 Skill → 注入上下文
```

### 快速使用

#### Step 1: 离线建库

```bash
# 自动扫描 OpenClaw 所有 Skill 目录并建库
python3 scripts/build_skill_index.py \
  --bucket my-skill-router \
  --index  skills-v1

# 指定自定义 Skill 目录
python3 scripts/build_skill_index.py \
  --bucket my-skill-router \
  --index  skills-v1 \
  --skills-dir ~/.openclaw/workspace-general-tech/skills \
               ~/.nvm/versions/node/v22.22.0/lib/node_modules/openclaw/skills

# 仅预览，不写入 S3
python3 scripts/build_skill_index.py --bucket x --index x --dry-run
```

**`build_skill_index.py` 参数：**

| 参数 | 必需 | 默认值 | 说明 |
|------|:---:|--------|------|
| `--bucket` | ✅ | — | S3 向量桶名称 |
| `--index` | ❌ | `skills-v1` | S3 向量索引名称 |
| `--skills-dir` | ❌ | OpenClaw 标准路径 | 要扫描的 Skill 目录（可多个） |
| `--region` | ❌ | `ap-northeast-1` | S3 Vectors Region |
| `--embed-region` | ❌ | 同 `--region` | Bedrock Embedding Region |
| `--profile` | ❌ | IAM Role | AWS CLI Profile |
| `--sync` | ❌ | false | 同步模式：自动删除已废弃 Skill 向量 |
| `--dry-run` | ❌ | false | 仅扫描，不写入 |

#### Step 2: 在线查询

```bash
# JSON 输出（适合脚本调用）
python3 scripts/skill_router.py \
  --bucket my-skill-router \
  --index  skills-v1 \
  --query  "AWS EKS Pod 故障排查" \
  --top-k  5

# Markdown 输出（适合注入 LLM 上下文）
python3 scripts/skill_router.py \
  --bucket my-skill-router \
  --index  skills-v1 \
  --query  "查一下今天天气" \
  --top-k  3 \
  --output markdown

# 只输出 Skill 名称（适合 shell 脚本）
python3 scripts/skill_router.py \
  --bucket my-skill-router \
  --index  skills-v1 \
  --query  "搜索 GitHub Issues" \
  --output names
```

**`skill_router.py` 参数：**

| 参数 | 必需 | 默认值 | 说明 |
|------|:---:|--------|------|
| `--bucket` | ✅ | — | S3 向量桶名称 |
| `--index` | ✅ | — | S3 向量索引名称 |
| `--query` | ✅ | — | 用户查询文本 |
| `--top-k` | ❌ | `5` | 返回 Top-K 数量 |
| `--output` | ❌ | `json` | 输出格式：`json` / `markdown` / `names` |
| `--score-threshold` | ❌ | `0` | 相似度分数过滤阈值（0~1） |
| `--embed-region` | ❌ | 同 `--region` | Bedrock Embedding Region |

#### Step 3: 安装 Hook（可选）

Hook 在 `agent:bootstrap` 时读取近期 Memory 上下文，自动筛选最相关 Top-5 Skill，
将结果写入 `BOOTSTRAP.md` 注入 LLM。

```bash
# 安装 Hook
cp -r hooks/skill-router-hook ~/.openclaw/hooks/

# ── 单 Agent 配置 ──────────────────────────────────────────
export SKILL_ROUTER_BUCKET=openclaw-skill-router
export SKILL_ROUTER_INDEX=skills-v1

# ── 多 Agent 配置（推荐）─────────────────────────────────────
# 先用 build_all.sh 并行建库（约 2 分钟）
SKILL_ROUTER_BUCKET=openclaw-skill-router ./scripts/build_all.sh

# Hook 从 sessionKey 自动提取 agent id → 选 skills-<agent_id> 索引
export SKILL_ROUTER_BUCKET=openclaw-skill-router
export SKILL_ROUTER_INDEX_PREFIX=skills   # ← 多 Agent 关键配置

# 启用 Hook
openclaw hooks enable skill-router-hook
```

**Hook 环境变量：**

| 变量 | 必需 | 说明 |
|------|:---:|------|
| `SKILL_ROUTER_BUCKET` | ✅ | S3 向量桶名称 |
| `SKILL_ROUTER_INDEX_PREFIX` | 多Agent推荐 | 索引前缀，自动拼接 agent id（`skills` → `skills-general-tech`）|
| `SKILL_ROUTER_INDEX` | 单Agent | 固定索引名，与 PREFIX 二选一，PREFIX 优先 |
| `SKILL_ROUTER_TOP_K` | ❌ | Top-K 数量（默认 5） |
| `SKILL_ROUTER_REGION` | ❌ | S3 Vectors Region（默认 ap-northeast-1） |
| `AWS_BEDROCK_REGION` | ❌ | Bedrock Embedding Region |

### 💰 成本分析（东京 ap-northeast-1，基于 AWS Pricing API 实时查询）

#### 价格基础数据

| 服务 | 计费项 | 单价（东京） |
|------|------|------------|
| Claude Sonnet 4（global 跨区） | 输入 tokens | $3.00 / 1M |
| Claude Sonnet 4（global 跨区） | 输出 tokens | $15.00 / 1M |
| Titan Text Embeddings V2 | 输入 tokens | $0.02 / 1M |
| S3 Vectors 查询请求 | QueryVectors | $2.70 / 1M 次 |
| S3 Vectors 存储 | 向量桶存储 | $0.066 / GB-月 |

#### 每轮对话成本对比（以 61 个 Skill 为基准）

| 成本项 | 无路由 | 有路由（Top-5） |
|--------|:------:|:--------------:|
| Skill 注入 tokens | 3,040 | ~305（avg） |
| Skill 注入 LLM 费 | $0.00912 | $0.000915 |
| S3 QueryVectors | — | $0.0000027 |
| Titan Embed（查询向量） | — | ~$0.0000006 |
| **Skill 部分合计** | **$0.00912** | **$0.000918** |
| **净节省（Skill 部分）** | — | **$0.00820（-90%）** |

路由开销（S3 + Embed）与节省相比：**净 ROI ≈ 1,800 倍**

#### 对整体 LLM 账单的影响

以典型一轮对话为例（含系统提示、对话历史、输出）：

| 成本项 | 无路由 | 有路由（Top-5） | 变化 |
|--------|:------:|:--------------:|:----:|
| 系统提示（~1,000 tokens） | $0.0030 | $0.0030 | — |
| **Skill 注入（3,040 → 305 tokens）** | **$0.0091** | **$0.0009** | **↓ 90%** |
| 对话历史 + 用户消息（~960 tokens） | $0.0029 | $0.0029 | — |
| 输出（~500 tokens） | $0.0075 | $0.0075 | — |
| **每轮合计** | **$0.0225** | **$0.0143** | **↓ 36%** |

> Skill 注入是唯一变化的成本项，其余不变。因此整体降幅 36%，而非 91%。

放大到 **1,000 轮/月**，差距更直观：

| 成本项 | 无路由 × 1,000 轮 | 有路由 × 1,000 轮 | 节省 |
|--------|:-----------------:|:-----------------:|:----:|
| 系统提示 | $3.00 | $3.00 | — |
| **Skill 注入** | **$9.12** | **$0.92** | **$8.20（↓ 90%）** |
| 对话历史 + 消息 | $2.88 | $2.88 | — |
| 输出 | $7.50 | $7.50 | — |
| S3 路由开销 | — | $0.003 | — |
| **月合计** | **$22.50** | **$14.33** | **$8.17（↓ 36%）** |

#### 月度规模效益

| 月活跃对话轮数 | 无路由月费 | 有路由月费 | 月节省 |
|:------------:|:---------:|:---------:|:------:|
| 1,000 轮 | $22.50 | $14.30 | **$8.20** |
| 10,000 轮 | $225 | $143 | **$82** |
| 50,000 轮 | $1,125 | $715 | **$410** |
| 100,000 轮 | $2,250 | $1,430 | **$820** |

#### 路由基础设施成本（可忽略）

| 项目 | 金额 |
|------|------|
| 首次建库（61 Skill Embeddings，一次性） | ~$0.000122 |
| S3 Vectors 存储（61 × 1024d × 4B ≈ 250KB） | ~$0.0000165/月 |
| 每次重建索引（增量） | ~$0.000177/次 |
| **基础设施总成本** | **< $0.001/月** |

---

### 实测性能（基于本机 61 个 Skill + 真实历史查询集）

> 测试环境：OpenClaw general-tech agent，61 个 Skill，Bedrock Titan Embeddings v2（1024 维），Region: ap-northeast-1

| 指标 | 数值 |
|------|------|
| Skill 总数 | 61 个 |
| 全量注入 Token / 轮 | **3,040 tokens** |
| 路由后 Token / 轮 | 193 ~ 417 tokens（随查询类型浮动） |
| **平均节省率** | **~91%** |
| 向量维度 | 1024（Titan Embeddings v2） |
| Skill 向量构建时间（首次） | ~18s（61个，含 API 调用） |
| 后续查询延迟（缓存命中） | < 1s |

#### 真实查询 Top-5 命中示例

| 真实查询 | 路由前 | 路由后 | 节省率 | Top-3 命中 Skill |
|---------|------:|------:|------:|-----------------|
| 查天气 | 3,040 | 209 | 93.1% | weather, openai-whisper, ordercli |
| EKS Pod 故障排查 | 3,040 | 306 | 89.9% | **aws-eks** ✅, aws-knowledge, session-logs |
| GitHub Issues 操作 | 3,040 | 262 | 91.4% | **gh-issues** ✅, **github** ✅, brave-web-search |
| CloudWatch 日志查询 | 3,040 | 302 | 90.1% | **aws-cloudwatch** ✅, healthcheck, aws-iac |
| 用代码 Agent 写代码 | 3,040 | 282 | 90.7% | **coding-agent** ✅, obsidian, model-usage |
| 发 Slack 消息 | 3,040 | 193 | 93.7% | **slack** ✅, discord, imsg |
| 股票行情查询 | 3,040 | 289 | 90.5% | ordercli, **stock-analysis** ✅, weather |
| 设置 Cron Job | 3,040 | 264 | 91.3% | **cron-mastery** ✅, apple-reminders, clawhub |
| AWS 文档搜索 | 3,040 | 356 | 88.3% | **aws-knowledge** ✅, aws-api, aws-iac |
| CDK 部署排障 | 3,040 | 417 | 86.3% | **aws-iac** ✅, aws-knowledge, healthcheck |

> **说明**：token 计数为近似估算（中文 ÷1.5，英文 ÷4）。✅ 表示 Top-1 命中目标 Skill。

#### 生成复现图表

```bash
# Step 1：提取真实历史查询
python3 scripts/extract_queries.py --limit 50 --output queries.json

# Step 2：跑基准测试并生成图表
python3 scripts/benchmark.py --output chart.png                         # Bedrock Embeddings（推荐）
python3 scripts/benchmark.py --use-tfidf --output chart.png             # 离线快速（不调 Bedrock）
python3 scripts/benchmark.py --use-s3 --bucket my-skill-router \        # 真实 S3 Vectors
  --index skills-v1 --output chart.png
```

### 当前局限 & 未来规划

| 能力 | 当前 | 未来（message:received Hook 支持上下文注入后） |
|------|------|--------------------------------------|
| 触发时机 | `agent:bootstrap`（会话启动） | 每条消息到达前 |
| 上下文来源 | 近期 Memory 文件 | 实时用户消息 |
| Skill 注入方式 | 写入 BOOTSTRAP.md | 动态替换 available_skills |
| Token 节省 | 部分（首轮有效） | **完整 ~91%** |

> ⚠️ OpenClaw 的 `message:received` Hook **已实现并上线**（PR [#9387](https://github.com/openclaw/openclaw/pull/9387)），
> 但当前为 `fireAndForgetHook` 模式（非阻塞），无法修改 system prompt 或 skills 列表。
> 社区已在 [#8807](https://github.com/openclaw/openclaw/issues/8807) 提议增加阻塞式上下文注入机制，
> 落地后可升级 Hook，实现完整的按消息动态路由。

### 🔧 索引维护

**何时需要重建索引？**

| 场景 | 操作 |
|------|------|
| 安装/更新/卸载 Skill | 重建索引（卸载建议加 `--sync`） |
| OpenClaw 升级 | 重建索引 |
| 修改 SKILL.md 的 name 或 description | 重建索引 |
| 日常对话、配置变更 | 无需操作 |

```bash
# Skill 变更后一键同步重建（推荐加 --sync）
python3 scripts/build_skill_index.py \
  --bucket my-skill-router \
  --index skills-v1 \
  --sync

# 多 Agent 全量同步重建
SKILL_ROUTER_BUCKET=my-skill-router ./scripts/build_all.sh
```

---

## 🏗️ 项目结构

```
s3-vector-skill/
├── README.md                              # 使用文档（本文件）
├── SKILL.md                               # OpenClaw Skill 定义文件
├── scripts/                               # 可执行脚本目录
│   ├── common.py                          # 公共模块
│   ├── create_vector_bucket.py            # 创建向量桶
│   ├── delete_vector_bucket.py            # 删除向量桶
│   ├── get_vector_bucket.py               # 查询向量桶信息
│   ├── list_vector_buckets.py             # 列出所有向量桶
│   ├── put_vector_bucket_policy.py        # 设置桶策略
│   ├── get_vector_bucket_policy.py        # 获取桶策略
│   ├── delete_vector_bucket_policy.py     # 删除桶策略
│   ├── create_index.py                    # 创建向量索引
│   ├── get_index.py                       # 查询索引信息
│   ├── list_indexes.py                    # 列出所有索引
│   ├── delete_index.py                    # 删除向量索引
│   ├── put_vectors.py                     # 插入/更新向量数据
│   ├── get_vectors.py                     # 获取指定向量
│   ├── list_vectors.py                    # 列出向量列表
│   ├── delete_vectors.py                  # 删除向量
│   ├── query_vectors.py                   # 相似度搜索
│   ├── build_skill_index.py               # Skill 路由：离线建库
│   ├── skill_router.py                    # Skill 路由：在线查询
│   ├── benchmark.py                       # Token 节省基准测试
│   ├── extract_queries.py                 # 真实查询集提取
│   └── embed.py                           # Bedrock Embedding 模块
├── hooks/
│   └── skill-router-hook/                 # OpenClaw Hook（Bootstrap 注入）
└── references/
    ├── api_reference.md                   # S3 Vectors API 参考
    └── cli-reference.md                   # 完整 CLI 命令参考
```

---

## ❓ 常见问题

**Q: 如何验证凭证是否有效？**
```bash
aws sts get-caller-identity
```

**Q: 如何确认 S3 Vectors 在当前 Region 可用？**
```bash
aws s3vectors list-vector-buckets --region ap-northeast-1
```
返回空列表说明可用；报 `Could not connect to endpoint` 说明该 Region 尚未支持。

**Q: 调用失败时如何排查？**
1. 检查 IAM Role / 凭证是否有 `s3vectors:*` 权限
2. 检查 Region 是否支持 S3 Vectors
3. 检查向量桶名称是否只含小写字母、数字和连字符
4. 查看返回的 `error_code` 和 `request_id`，在 AWS CloudTrail 中检索

**Q: 支持哪些 Region？**

| Region | 名称 |
|--------|------|
| `us-east-1` | 美国东部（弗吉尼亚） |
| `us-west-2` | 美国西部（俄勒冈） |
| `eu-west-1` | 欧洲（爱尔兰） |
| `ap-northeast-1` | 亚太（东京）✅ 本项目默认 |
| `ap-southeast-1` | 亚太（新加坡） |

---

## 📚 参考链接

- [Amazon S3 Vectors 产品主页](https://aws.amazon.com/s3/features/vectors/)
- [S3 Vectors GA 发布博客](https://aws.amazon.com/blogs/aws/amazon-s3-vectors-now-generally-available-with-increased-scale-and-performance/)
- [boto3 s3vectors API 文档](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3vectors.html)
- [Amazon Bedrock Titan Embeddings v2](https://docs.aws.amazon.com/bedrock/latest/userguide/titan-embedding-models.html)
- [re:Invent 2025 STG318 Session](https://www.youtube.com/watch?v=ghUW2SpEYPk)
- [OpenClaw 官网](https://openclaw.ai/)
- [ClawHub Skill 市场](https://clawhub.com/)

---

## 📄 License

MIT
