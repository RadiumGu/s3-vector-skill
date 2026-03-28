#!/usr/bin/env bash
# install.sh — S3 Vectors 知识库初始化
#
# 前置检查 → 创建向量桶 → 创建索引
#
# 用法:
#   ./install.sh --bucket my-kb --index docs-v1
#   ./install.sh --bucket my-kb --index docs-v1 --yes

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}ℹ️  $*${NC}"; }
ok()    { echo -e "${GREEN}✅ $*${NC}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${NC}"; }
fail()  { echo -e "${RED}❌ $*${NC}"; exit 1; }

BUCKET=""
INDEX="docs-v1"
REGION="${AWS_DEFAULT_REGION:-ap-northeast-1}"
DIMENSION=1024
YES=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bucket)    BUCKET="$2"; shift 2 ;;
    --index)     INDEX="$2"; shift 2 ;;
    --region)    REGION="$2"; shift 2 ;;
    --dimension) DIMENSION="$2"; shift 2 ;;
    --yes|-y)    YES=true; shift ;;
    *) fail "未知参数: $1" ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 前置检查 ──────────────────────────────────────────────────────────
info "Step 1: 前置检查"

python3 -c "import boto3; boto3.client('s3vectors', region_name='$REGION'); print('boto3 s3vectors OK')" \
  || fail "boto3 不支持 s3vectors，请 pip3 install boto3 --upgrade"

aws sts get-caller-identity --query 'Arn' --output text \
  || fail "AWS 凭证无效"

ok "前置检查通过"

# ── 交互式输入 ──────────────────────────────────────────────────────────
if [[ -z "$BUCKET" ]]; then
  read -rp "请输入 S3 向量桶名称: " BUCKET
fi
[[ -z "$BUCKET" ]] && fail "向量桶名称不能为空"

echo ""
info "配置确认:"
echo "  向量桶:  $BUCKET"
echo "  索引:    $INDEX"
echo "  Region:  $REGION"
echo "  维度:    $DIMENSION"
echo ""

if [[ "$YES" != true ]]; then
  read -rp "确认? (y/N) " CONFIRM
  [[ "$CONFIRM" =~ ^[Yy] ]] || { echo "已取消"; exit 0; }
fi

# ── 创建向量桶 ──────────────────────────────────────────────────────────
info "Step 2: 创建向量桶"
python3 "$SCRIPT_DIR/scripts/create_vector_bucket.py" --bucket "$BUCKET" --region "$REGION" \
  && ok "向量桶已创建: $BUCKET" \
  || warn "向量桶可能已存在（忽略错误继续）"

# ── 创建索引 ──────────────────────────────────────────────────────────
info "Step 3: 创建索引"
python3 "$SCRIPT_DIR/scripts/create_index.py" --bucket "$BUCKET" --index "$INDEX" --dimension "$DIMENSION" --region "$REGION" \
  && ok "索引已创建: $INDEX (${DIMENSION}d, cosine)" \
  || warn "索引可能已存在（忽略错误继续）"

echo ""
ok "初始化完成！"
echo ""
echo "使用示例："
echo "  # 插入向量"
echo "  python3 $SCRIPT_DIR/scripts/put_vectors.py --bucket $BUCKET --index $INDEX --vectors '[...]'"
echo ""
echo "  # 相似度搜索"
echo "  python3 $SCRIPT_DIR/scripts/query_vectors.py --bucket $BUCKET --index $INDEX --query-vector '[...]' --top-k 5"
