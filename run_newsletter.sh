#!/usr/bin/env bash
# ============================================================
# 사회복지 뉴스레터 실행 래퍼
# - claude -p 로 전체 워크플로 실행 (웹검색 → 텔레그램 → Gmail)
# - /etc/cron.d/wellfare-newsletter 에서 호출
# ============================================================
set -euo pipefail

SCRIPT_DIR="/home/user/claude_01_wellfare_news"
LOG_DIR="$SCRIPT_DIR/logs"
PROMPT_FILE="$SCRIPT_DIR/newsletter_prompt.txt"
ENV_FILE="$SCRIPT_DIR/.env"

# 로그 디렉터리 생성
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/newsletter_$(date +%Y%m%d_%H%M%S).log"

echo "[$(date '+%Y-%m-%d %H:%M:%S KST')] ===== 뉴스레터 실행 시작 =====" | tee "$LOG_FILE"

# .env 로드 (있을 경우)
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# claude CLI 존재 확인
if ! command -v claude &> /dev/null; then
    echo "[ERROR] claude CLI가 설치되어 있지 않습니다." | tee -a "$LOG_FILE"
    echo "  설치: npm install -g @anthropic-ai/claude-code" | tee -a "$LOG_FILE"
    exit 1
fi

# 프롬프트 파일 확인
if [ ! -f "$PROMPT_FILE" ]; then
    echo "[ERROR] 프롬프트 파일 없음: $PROMPT_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] claude 실행 중..." | tee -a "$LOG_FILE"

# claude -p 로 전체 뉴스레터 워크플로 실행
claude -p "$(cat "$PROMPT_FILE")" \
    --output-format text \
    2>&1 | tee -a "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo "" | tee -a "$LOG_FILE"
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 완료" | tee -a "$LOG_FILE"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ 실패 (exit=$EXIT_CODE)" | tee -a "$LOG_FILE"
fi

# 30일 이상 된 로그 삭제
find "$LOG_DIR" -name "newsletter_*.log" -mtime +30 -delete 2>/dev/null || true

exit "$EXIT_CODE"
