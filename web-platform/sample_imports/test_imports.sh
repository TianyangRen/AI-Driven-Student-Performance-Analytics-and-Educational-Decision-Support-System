#!/usr/bin/env bash
# 一键手动测试 CSV/Excel 导入功能。
# 前提：后端已在 http://localhost:8000 运行。
# 用法：bash test_imports.sh
set -euo pipefail

BASE="http://localhost:8000/api/v1"
DIR="$(cd "$(dirname "$0")" && pwd)"
U="teacher_$(date +%s)"          # 每次跑用不同用户名，避免撞唯一约束
PW="pw123456"

echo "==> 1) 注册教师 $U"
REG=$(curl -s -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$U\",\"password\":\"$PW\",\"full_name\":\"Test Teacher\",\"email\":\"$U@x.com\",\"role\":\"INSTRUCTOR\"}")
TOKEN=$(echo "$REG" | jq -r '.data.token')
USER_ID=$(echo "$REG" | jq -r '.data.user.id')
echo "    token=${TOKEN:0:12}...  user_id=$USER_ID"
AUTH="Authorization: Token $TOKEN"

echo "==> 2) 建课程"
COURSE_ID=$(curl -s -X POST "$BASE/courses" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d '{"code":"COMP8567","name":"AI Analytics","term":"S26"}' | jq -r '.id')
echo "    course_id=$COURSE_ID"

echo "==> 3) 建教学班"
SECTION_ID=$(curl -s -X POST "$BASE/sections" -H "$AUTH" \
  -H "Content-Type: application/json" \
  -d "{\"course\":$COURSE_ID,\"section_code\":\"01\",\"status\":\"ACTIVE\",\"instructor\":$USER_ID}" | jq -r '.id')
echo "    section_id=$SECTION_ID"

upload () {  # $1=type  $2=file
  echo "==> 导入 $1 ($2)"
  curl -s -X POST "$BASE/sections/$SECTION_ID/imports" -H "$AUTH" \
    -F "import_type=$1" -F "file=@$DIR/$2" | jq '.data'
}

echo "==> 4) 依次导入"
upload ROSTER   roster.csv
upload SCORE    score.csv
upload ACTIVITY activity.csv

echo "==> 5) 导入一个含错误的成绩文件（预期 PARTIAL, valid_rows=1）"
RESP=$(curl -s -X POST "$BASE/sections/$SECTION_ID/imports" -H "$AUTH" \
  -F "import_type=SCORE" -F "file=@$DIR/score_with_errors.csv")
echo "$RESP" | jq '.data'
BATCH=$(echo "$RESP" | jq -r '.data.batch_id')

echo "==> 6) 查看该批次的错误明细"
curl -s "$BASE/imports/$BATCH/errors" -H "$AUTH" | jq '.data.errors'

echo "==> 7) 下载模板（CSV 列头预览）"
curl -s "$BASE/imports/template?type=SCORE&fmt=csv" -H "$AUTH" | head -1

echo ""
echo "全部完成。section_id=$SECTION_ID（可在前端登录 $U / $PW 查看该班数据）"
