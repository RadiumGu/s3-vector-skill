# S3 Vector Skill — 优化清单

> 2026-03-16 架构审阅猫审阅，不扩张功能范围，仅优化现有代码质量。

## 修改项

| # | 问题 | 文件 | 状态 |
|---|------|------|------|
| 1 | `build_all.sh` 硬编码 Agent 列表 → 自动扫描 workspace-* | `scripts/build_all.sh` | ✅ |
| 2 | `build_skill_index.py` 无增量构建 → desc_hash 对比，只 embed 变化的 Skill | `scripts/build_skill_index.py` | ✅ |
| 3 | `embed.py` 缓存仅内存 → 加磁盘缓存（~/.cache/s3-vector-skill/） | `scripts/embed.py` | ✅ |
| 4 | `handler.ts` extractRecentContext 质量低 → 标题+段落优先截断 | `hooks/skill-router-hook/handler.ts` | ✅ |
| 5 | `skill_router.py` 默认不过滤低分 → 默认 0.3 阈值 + handler 传参 | `scripts/skill_router.py` + `handler.ts` | ✅ |
| 6 | YAML 解析用正则太脆弱 → 优先 pyyaml + regex fallback | `scripts/common.py` | ✅ |
| 7 | `handler.ts` 路径硬编码 → 移除 + install.sh 注入 SKILL_ROUTER_SCRIPT | `handler.ts` + `install.sh` | ✅ |
| 8 | benchmark.py 重复 Skill 扫描逻辑 → 抽到 common.py 共享 | `scripts/common.py` + `scripts/benchmark.py` | ✅ |
| 9 | 错误处理缺 ThrottlingException + embed 重试无 jitter | `scripts/common.py` + `scripts/embed.py` | ✅ |
| 10 | SKILL.md description 过长 → 精简至 ~200 字 + triggers 独立字段 | `SKILL.md` | ✅ |

## 变更摘要

### common.py（重构最大）
- 新增 `parse_skill_md()`、`find_skills()`、`desc_hash()`、`DEFAULT_SKILL_DIRS`
- `handle_error()` 增加 ThrottlingException 识别和提示

### embed.py
- 新增磁盘缓存层（`~/.cache/s3-vector-skill/embed_cache.json`）
- 重试加 jitter（`random.uniform(0, 1)`）

### build_skill_index.py
- 增量构建：通过 `desc_hash` 对比已有 metadata，只 embed 变化/新增的 Skill
- 新增 `--force` 参数跳过增量对比
- 复用 common.py 的 `find_skills()` / `parse_skill_md()`
- 写入时 metadata 包含 `desc_hash` 用于下次增量对比

### build_all.sh
- Agent 列表从硬编码改为自动扫描 `~/.openclaw/workspace*`

### handler.ts
- `extractRecentContext()` 优先提取标题行 + 近期段落
- `resolveScript()` 移除硬编码个人路径
- spawn 调用加 `--score-threshold` 参数

### install.sh
- 环境变量注入增加 `SKILL_ROUTER_SCRIPT`

### benchmark.py
- 移除重复的 `parse_skill_md` / `load_skills` / `DEFAULT_SKILL_DIRS`
- 改用 `from common import find_skills`

### SKILL.md
- description 从 470+ 字精简到 ~200 字
- trigger phrases 独立为 `triggers` 列表字段
