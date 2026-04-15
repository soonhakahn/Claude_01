#!/usr/bin/env bash
# ============================================================
# 사회복지 뉴스레터 크론 설정 스크립트
# 실행: bash setup_cron.sh
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEWSLETTER_SCRIPT="$SCRIPT_DIR/newsletter.py"
LOG_DIR="$SCRIPT_DIR/logs"
ENV_FILE="$SCRIPT_DIR/.env"

# ── 로그 디렉터리 생성 ────────────────────────────────────
mkdir -p "$LOG_DIR"

# ── .env 파일 확인 ────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
    echo "⚠️  .env 파일이 없습니다. .env.example을 참고해 생성하세요."
    echo "   cp $SCRIPT_DIR/.env.example $ENV_FILE"
fi

# ── 크론 래퍼 스크립트 생성 ───────────────────────────────
WRAPPER="$SCRIPT_DIR/run_newsletter.sh"
cat > "$WRAPPER" << WRAPPER_EOF
#!/usr/bin/env bash
# 뉴스레터 실행 래퍼 (크론에서 호출)
set -euo pipefail

SCRIPT_DIR="$SCRIPT_DIR"
LOG_DIR="$LOG_DIR"
ENV_FILE="$ENV_FILE"

# .env 로드
if [ -f "\$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "\$ENV_FILE"
    set +a
fi

LOG_FILE="\$LOG_DIR/newsletter_\$(date +%Y%m%d_%H%M%S).log"

echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 뉴스레터 실행 시작" | tee "\$LOG_FILE"
python3 "$NEWSLETTER_SCRIPT" 2>&1 | tee -a "\$LOG_FILE"
echo "[\$(date '+%Y-%m-%d %H:%M:%S')] 완료" | tee -a "\$LOG_FILE"

# 30일 이상 된 로그 삭제
find "\$LOG_DIR" -name "newsletter_*.log" -mtime +30 -delete 2>/dev/null || true
WRAPPER_EOF

chmod +x "$WRAPPER"
echo "✅ 래퍼 스크립트 생성: $WRAPPER"

# ── 크론 등록 ─────────────────────────────────────────────
# 기존 뉴스레터 크론 항목 제거 후 재등록
CRON_COMMENT="# 사회복지 뉴스레터 자동화"
CRON_MORNING="0 22 * * * $WRAPPER  # 아침 에디션 (UTC 22:00 = KST 07:00)"
CRON_EVENING="0 10 * * * $WRAPPER  # 저녁 에디션 (UTC 10:00 = KST 19:00)"

# 현재 크론 읽기 → 뉴스레터 항목 제거 → 새 항목 추가
(
  crontab -l 2>/dev/null | grep -v "newsletter" | grep -v "사회복지 뉴스레터"
  echo ""
  echo "$CRON_COMMENT"
  echo "$CRON_MORNING"
  echo "$CRON_EVENING"
) | crontab -

echo ""
echo "✅ 크론 등록 완료:"
echo "   UTC 10:00 (KST 19:00) — 저녁 에디션 🌙"
echo "   UTC 22:00 (KST 07:00) — 아침 에디션 ☀️"
echo ""
echo "현재 크론 목록:"
crontab -l | grep -A3 "사회복지" || echo "  (크론 확인 실패)"
echo ""
echo "────────────────────────────────────────────"
echo "다음 단계: $ENV_FILE 파일에 환경변수를 설정하세요"
echo "────────────────────────────────────────────"
