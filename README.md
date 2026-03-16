# Amazon S3 向量桶全功能管理 Skill

> Amazon S3 Vectors 全功能管理 OpenClaw Skill，覆盖向量桶、索引、向量数据的全生命周期管理，共 **16 个核心能力**。
> 基于 Amazon S3 Vectors（re:Invent 2025 GA），比传统向量数据库降低 **90%** 成本。

## ✨ 功能概览

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
| **Skill 路由（降本工具）** | 离线建库 | `build_skill_index.py` |
| | 在线路由查询 | `skill_router.py` |
| | Token 节省基准测试 | `benchmark.py` |
| | 真实查询集提取 | `extract_queries.py` |
| | Bedrock Embedding 模块 | `embed.py` |
| | 获取指定向量 | `get_vectors.py` |
| | 列出向量列表 | `list_vectors.py` |
| | 删除向量 | `delete_vectors.py` |
| | 相似度搜索 | `query_vectors.py` |

---

## 🚀 快速开始

### 前置条件

- Python 3.8+
- boto3（AWS Python SDK）

```bash
pip3 install boto3 --upgrade
```

### 验证安装

```bash
python3 -c "import boto3; client = boto3.client('s3vectors', region_name='ap-northeast-1'); print('boto3 安装成功')"
```

### 准备凭证

支持以下三种认证方式（优先级从高到低）：

#### 方式 1：实例 IAM Role（推荐，EC2/EKS 上自动生效，无需配置）

在 EC2 或 EKS 上运行时，绑定具有 `s3vectors:*` 权限的 IAM Role 即可，无需任何额外配置。

#### 方式 2：环境变量（临时使用）

```bash
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="ap-northeast-1"
```

#### 方式 3：AWS Profile（通过 `--profile` 参数）

```bash
aws configure --profile my-profile

python3 scripts/list_vector_buckets.py \
  --region "ap-northeast-1" \
  --profile "my-profile"
```

### 公共参数

所有脚本支持以下参数：

| 参数 | 必需 | 说明 |
|------|:---:|------|
| `--bucket` | ✅ | 向量桶名称（list_vector_buckets 除外） |
| `--region` | ❌ | AWS Region，默认 `ap-northeast-1` 或 `AWS_DEFAULT_REGION` |
| `--profile` | ❌ | AWS CLI Profile 名称 |

---

## 📖 使用指南

### 一、向量桶管理

#### 1. 创建向量桶

```bash
python3 scripts/create_vector_bucket.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --sse-type SSE-S3    # 可选，启用 SSE-S3 加密（也支持 SSE-KMS）
```

#### 2. 查询向量桶信息

```bash
python3 scripts/get_vector_bucket.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1"
```

#### 3. 列出所有向量桶

```bash
python3 scripts/list_vector_buckets.py \
  --region "ap-northeast-1" \
  --max-results 20 \   # 可选，限制返回数量
  --prefix "my-"       # 可选，前缀过滤
```

#### 4. 删除向量桶

```bash
python3 scripts/delete_vector_bucket.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1"
```

### 二、桶策略管理

#### 5. 设置桶策略

```bash
python3 scripts/put_vector_bucket_policy.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --policy '{"Statement": [{"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::123456789012:role/MyRole"}, "Action": "s3vectors:*", "Resource": "*"}]}'
```

#### 6. 获取桶策略

```bash
python3 scripts/get_vector_bucket_policy.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1"
```

#### 7. 删除桶策略

```bash
python3 scripts/delete_vector_bucket_policy.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1"
```

### 三、索引管理

#### 8. 创建索引

```bash
python3 scripts/create_index.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --dimension 1024 \
  --data-type float32 \
  --distance-metric cosine
```

| 参数 | 必需 | 说明 |
|------|:---:|------|
| `--index` | ✅ | 索引名称 |
| `--dimension` | ✅ | 向量维度（1-4096），Bedrock Titan v2 推荐 1024 |
| `--data-type` | ❌ | 数据类型，默认 `float32` |
| `--distance-metric` | ❌ | 距离度量：`cosine`（默认）或 `euclidean` |
| `--non-filterable-keys` | ❌ | 非过滤元数据键，逗号分隔 |

#### 9. 查询索引信息

```bash
python3 scripts/get_index.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index"
```

#### 10. 列出所有索引

```bash
python3 scripts/list_indexes.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --max-results 10
```

#### 11. 删除索引

```bash
python3 scripts/delete_index.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index"
```

### 四、向量数据操作

#### 12. 插入/更新向量

**方式 1：命令行传入 JSON**
```bash
python3 scripts/put_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --vectors '[{"key":"doc-001","data":{"float32":[0.1,0.2,0.3]},"metadata":{"title":"文档1","category":"AI"}}]'
```

**方式 2：通过文件传入**
```bash
# 准备 vectors.json 文件
cat > vectors.json << 'EOF'
[
  {
    "key": "doc-001",
    "data": {"float32": [0.1, 0.2, 0.3]},
    "metadata": {"title": "人工智能简介", "category": "AI"}
  },
  {
    "key": "doc-002",
    "data": {"float32": [0.4, 0.5, 0.6]},
    "metadata": {"title": "机器学习算法", "category": "AI"}
  }
]
EOF

python3 scripts/put_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --vectors-file vectors.json
```

#### 13. 获取指定向量

```bash
python3 scripts/get_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --keys "doc-001,doc-002" \
  --return-data \
  --return-metadata
```

#### 14. 列出向量列表

```bash
python3 scripts/list_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --max-results 10 \
  --return-metadata
```

#### 15. 删除向量

```bash
python3 scripts/delete_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --keys "doc-001,doc-002"
```

#### 16. 相似度搜索 🔍

这是最核心的能力 —— 根据查询向量找到最相似的 K 个结果。

```bash
python3 scripts/query_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --query-vector '[0.1, 0.2, 0.3]' \
  --top-k 5 \
  --filter '{"category": {"$eq": "AI"}}' \
  --return-metadata
```

也可以通过文件传入查询向量：
```bash
python3 scripts/query_vectors.py \
  --bucket "my-skill-vectors" \
  --region "ap-northeast-1" \
  --index "my-index" \
  --query-vector-file query.json \
  --top-k 5 \
  --return-metadata
```

---

## 🤖 作为 OpenClaw Skill 使用

这个仓库可以直接作为 [OpenClaw](https://openclaw.ai/) 的 AI Skill 使用，让 AI 助手自动调用向量桶操作。

### 安装方式

#### 方式 1：手动安装到 OpenClaw Skill 目录

```bash
# 复制到 OpenClaw workspace skills 目录
cp -r /home/ubuntu/tech/s3-vector-skill \
  ~/.openclaw/workspace-general-tech/skills/s3-vector-bucket
```

#### 方式 2：Git 子模块（团队协作推荐）

```bash
git submodule add <repo-url> .openclaw/skills/s3-vector-bucket
git commit -m "feat: 添加 S3 向量桶 skill"
```

### 使用方式

安装后，在 OpenClaw 对话中使用自然语言即可触发：

| 你说 | AI 自动执行 |
|------|------------|
| "帮我创建一个 S3 向量桶" | 调用 `create_vector_bucket.py` |
| "创建一个 1024 维的向量索引" | 调用 `create_index.py` |
| "插入 5 条测试向量数据" | 调用 `put_vectors.py` |
| "列出所有向量数据" | 调用 `list_vectors.py` |
| "搜索和这段文本最相似的向量" | 调用 `query_vectors.py` |
| "删除 demo-index 索引" | 调用 `delete_index.py` |

### Skill 触发关键词

以下关键词会自动触发 skill 加载：

`vector bucket` · `vector index` · `vector search` · `向量桶` · `向量索引` · `向量搜索` · `向量存储` · `插入向量` · `相似度搜索` · `S3 vector` · `S3 vectors`

---

## 🏗️ 项目结构

```
s3-vector-skill/
├── README.md                              # 使用文档（本文件）
├── SKILL.md                               # OpenClaw Skill 定义文件
├── scripts/                               # 可执行脚本目录
│   ├── common.py                          # 公共模块（boto3 客户端、错误处理）
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
│   └── query_vectors.py                   # 相似度搜索
└── references/
    └── api_reference.md                   # API 参考文档
```

---

## 🔧 技术细节

| 配置项 | 说明 |
|--------|------|
| **boto3 客户端** | `boto3.client('s3vectors', region_name=...)` 专用客户端 |
| **参数命名** | camelCase（`vectorBucketName`、`indexName`、`topK`） |
| **认证方式** | IAM Role（推荐）> 环境变量 > AWS Profile |
| **桶名规则** | 小写字母、数字和连字符 `-`，长度 3-63 字符，全局唯一 |
| **向量维度** | 1-4096，Bedrock Titan Embeddings v2 推荐 **1024** |
| **数据类型** | `float32` |
| **距离度量** | `cosine`（余弦相似度，RAG 推荐）、`euclidean`（欧氏距离） |
| **加密类型** | `SSE-S3`（S3 托管密钥）或 `SSE-KMS`（AWS KMS 密钥） |
| **规模上限** | 单索引最多 **20 亿向量**，查询延迟 **< 100ms** |

### 输出格式

所有脚本统一输出 JSON 格式：

```json
// 成功
{"success": true, "action": "create_index", "bucket": "...", "index": "...", ...}

// 失败
{"success": false, "error": "错误信息", "error_code": "...", "request_id": "..."}
```

### 公共模块 `common.py`

| 函数 | 功能 |
|------|------|
| `base_parser()` | 创建包含区域和认证参数的基础解析器 |
| `create_client()` | 初始化 boto3 s3vectors 客户端 |
| `success_output()` | 统一的成功输出格式 |
| `fail()` | 统一的错误输出格式并退出 |
| `handle_error()` | 统一异常处理（ClientError / BotoCoreError） |
| `run()` | 包装主函数并捕获异常 |

---

## ❓ 常见问题

### Q: boto3 安装失败怎么办？

```bash
pip3 install boto3 --upgrade --force-reinstall
```

### Q: 如何验证凭证是否有效？

```bash
aws sts get-caller-identity
```

返回账号 ID 和 ARN 说明凭证有效。

### Q: 如何确认 S3 Vectors 在当前 Region 可用？

```bash
aws s3vectors list-vector-buckets --region ap-northeast-1
```

返回空列表（`{}`）说明可用；报 `Could not connect to endpoint` 说明该 Region 尚未支持。

### Q: 调用失败时如何排查？

1. 检查 IAM Role / 凭证是否有 `s3vectors:*` 权限
2. 检查 Region 是否支持 S3 Vectors
3. 检查向量桶名称是否只含小写字母、数字和连字符
4. 查看返回的 `error_code` 和 `request_id`，在 AWS CloudTrail 中检索

### Q: 与腾讯云 COS 向量桶有什么区别？

| 维度 | COS 版 | AWS S3 版（本 Skill） |
|------|--------|----------------------|
| 云平台 | 腾讯云 | AWS |
| SDK | cos-python-sdk-v5 | boto3 |
| 认证 | SecretId / SecretKey | IAM Role / 环境变量 |
| Embedding | ONNX text2vec (768d) | Bedrock Titan v2 (1024d) |
| 最大向量数/索引 | 未公开 | **20 亿** |
| 查询延迟 | 毫秒级 | **< 100ms** |

### Q: 支持哪些 Region？

S3 Vectors 已在主要 Region 正式 GA（re:Invent 2025）：

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

## 🧭 Skill 路由（Token 降本 ~91%）

> **灵感来源**：仿照腾讯云 COS Vector 向量桶 Skill 路由方案，AWS 原生实现。
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
| `--embed-region` | ❌ | 同 `--region` | Bedrock Embedding Region（默认跟 `--region` 一致；若该 region 无 Titan v2 可手动指定） |
| `--profile` | ❌ | IAM Role | AWS CLI Profile |
| `--sync` | ❌ | false | 同步模式：写入后自动删除索引中已不存在的废弃 Skill 向量 |
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
| `--embed-region` | ❌ | 同 `--region` | Bedrock Embedding Region（默认跟 `--region` 一致；若该 region 无 Titan v2 可手动指定） |

#### Step 3: 安装 Hook（可选）

Hook 在 `agent:bootstrap` 时读取近期 Memory 上下文，自动筛选最相关 Top-5 Skill，
将结果写入 `BOOTSTRAP.md` 注入 LLM。

```bash
# 安装 Hook
cp -r hooks/skill-router-hook ~/.openclaw/hooks/

# ── 单 Agent 配置 ──────────────────────────────────────────
export SKILL_ROUTER_BUCKET=openclaw-skill-router
export SKILL_ROUTER_INDEX=skills-v1       # 固定索引名

# ── 多 Agent 配置（推荐）─────────────────────────────────────
# 先用 build_all.sh 并行建库（约 2 分钟）
SKILL_ROUTER_BUCKET=openclaw-skill-router ./scripts/build_all.sh

# Hook 从 sessionKey 自动提取 agent id → 选 skills-<agent_id> 索引
export SKILL_ROUTER_BUCKET=openclaw-skill-router
export SKILL_ROUTER_INDEX_PREFIX=skills   # ← 多 Agent 关键配置（PREFIX 优先于 INDEX）

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
| `AWS_BEDROCK_REGION` | ❌ | Bedrock Embedding Region（默认跟 `SKILL_ROUTER_REGION` 一致；若该 region 无 Titan v2 可手动设置） |

### 实测性能（基于本机 61 个 Skill + 真实历史查询集）

> 测试环境：OpenClaw general-tech agent，61 个 Skill，Bedrock Titan Embeddings v2（1024 维），Region: ap-northeast-1

| 指标 | 数值 |
|------|------|
| Skill 总数 | 61 个 |
| 全量注入 Token / 轮 | **3,040 tokens** |
| 路由后 Token / 轮 | 193 ~ 417 tokens（随查询类型浮动） |
| **平均节省率** | **~91%**（token 计数为近似估算，方法：中文 ÷1.5，英文 ÷4） |
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

> **说明**：以上数据来自 Bedrock Titan Embeddings v2 语义路由实测，token 计数使用近似算法（中文 ÷1.5，英文 ÷4），与实际 LLM tokenizer 有轻微偏差。✅ 表示 Top-1 命中目标 Skill。

#### 生成复现图表

```bash
# Step 1：提取真实历史查询（自动从 session logs 抽取）
python3 scripts/extract_queries.py --limit 50 --output queries.json

# Step 2：跑基准测试并生成图表（默认 Bedrock Embeddings）
python3 scripts/benchmark.py --output chart.png

# 其他模式
python3 scripts/benchmark.py --use-tfidf --output chart.png   # 离线快速（不调 Bedrock）
python3 scripts/benchmark.py --use-s3 \                       # 真实 S3 Vectors（最准）
  --bucket my-skill-router --index skills-v1 --output chart.png
```

**benchmark.py 三种路由模式对比：**

| 模式 | 命令参数 | 优点 | 适用场景 |
|------|---------|------|---------|
| Bedrock Embeddings（默认） | 无需参数 | 语义准确，首次缓存后快 | **推荐，生产演示** |
| TF-IDF 本地 | `--use-tfidf` | 零成本，纯离线 | 快速验证，无 AWS 环境 |
| S3 Vectors 真实路由 | `--use-s3 --bucket ...` | 与线上完全一致 | 生产环境验收 |

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

### 🔧 维护注意事项

**何时需要重建索引？**

| 场景 | 操作 |
|------|------|
| 安装新 Skill（`clawhub install`） | 重建索引 |
| 更新 Skill（`clawhub update`） | 重建索引（描述可能变化） |
| 卸载 Skill | 用 `--sync` 重建，自动清理废弃向量 |
| OpenClaw 升级（内置 Skill 可能变化） | 重建索引 |
| 修改 SKILL.md 的 name 或 description | 重建索引 |
| 日常对话、配置变更 | 无需操作 |

**推荐操作流程：**

```bash
# Skill 变更后，一键同步重建（推荐加 --sync）
python3 scripts/build_skill_index.py \
  --bucket my-skill-router \
  --index skills-v1 \
  --sync

# 多 Agent 全量同步重建
SKILL_ROUTER_BUCKET=my-skill-router ./scripts/build_all.sh
```

`--sync` 会在写入新向量后，自动列出索引中所有 key，对比磁盘上扫描到的 Skill names，删除已不存在的废弃向量。这可以避免路由命中已卸载的 Skill。

**不加 `--sync` 的风险**：已删除的 Skill 向量仍留在索引中，路由可能命中已不存在的 Skill，LLM 会尝试加载不存在的 SKILL.md 文件而失败。

---

## 📄 License

MIT
