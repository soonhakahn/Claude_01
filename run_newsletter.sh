#!/usr/bin/env bash
# ============================================================
# 사회복지 뉴스레터 실행 래퍼 (크론용)
#
# 실행 순서:
#   1. claude -p  → 뉴스 수집 + /tmp/newsletter.txt 저장 + 텔레그램 전송
#   2. send_email.py → Gmail SMTP 실제 발송
#   3. 각 단계 성공/실패 검증
#   4. 최종 결과를 텔레그램으로 통보
# ============================================================
set -uo pipefail

SCRIPT_DIR="/home/user/claude_01_wellfare_news"
LOG_DIR="$SCRIPT_DIR/logs"
PROMPT_FILE="$SCRIPT_DIR/newsletter_prompt.txt"
SEND_EMAIL="$SCRIPT_DIR/send_email.py"
ENV_FILE="$SCRIPT_DIR/.env"
NEWSLETTER_FILE="/tmp/newsletter.txt"

TELEGRAM_BOT_TOKEN="8550163156:AAEQYbsXM30m_PqUM4zG2qSqMK-Y9erWZt8"
TELEGRAM_CHAT_ID="1472020115"
TELEGRAM_API="https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage"

# ── 초기화 ────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/newsletter_$(date +%Y%m%d_%H%M%S).log"
STEP_CLAUDE="❓"
STEP_FILE="❓"
STEP_TELEGRAM="❓"
STEP_EMAIL="❓"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }
log_sep() { echo "──────────────────────────────────────────" | tee -a "$LOG_FILE"; }

# ── 텔레그램 메시지 전송 함수 ─────────────────────────────
tg_send() {
    local text="$1"
    python3 - <<PYEOF 2>/dev/null
import urllib.request, json
data = json.dumps({"chat_id": "$TELEGRAM_CHAT_ID", "text": """$text"""}).encode()
req = urllib.request.Request("$TELEGRAM_API", data=data,
      headers={"Content-Type": "application/json"})
try:
    urllib.request.urlopen(req, timeout=15)
except Exception as e:
    pass
PYEOF
}

log "===== 사회복지 뉴스레터 시작 ====="
log_sep

# ── .env 로드 ─────────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    log ".env 로드 완료"
fi

# ── 사전 확인 ─────────────────────────────────────────────
if ! command -v claude &> /dev/null; then
    log "[ERROR] claude CLI 없음 — npm install -g @anthropic-ai/claude-code"
    tg_send "❌ [뉴스레터] claude CLI 없음 — 크론 실행 실패 ($(date '+%m/%d %H:%M'))"
    exit 1
fi
if [ ! -f "$PROMPT_FILE" ]; then
    log "[ERROR] 프롬프트 파일 없음: $PROMPT_FILE"
    tg_send "❌ [뉴스레터] 프롬프트 파일 없음 — 크론 실행 실패"
    exit 1
fi

# ────────────────────────────────────────────────────────
# STEP 1: claude -p 실행 (뉴스 수집 + 텔레그램 전송)
# ────────────────────────────────────────────────────────
log_sep
log "[STEP 1] claude -p 실행 — 뉴스 수집 + 텔레그램 전송"

rm -f "$NEWSLETTER_FILE"   # 이전 파일 제거

CLAUDE_OUTPUT=$(claude -p "$(cat "$PROMPT_FILE")" --output-format text 2>&1)
CLAUDE_EXIT=$?

echo "$CLAUDE_OUTPUT" | tee -a "$LOG_FILE"

if [ "$CLAUDE_EXIT" -eq 0 ]; then
    STEP_CLAUDE="✅"
    log "[STEP 1] claude 실행 완료 (exit=0)"
else
    STEP_CLAUDE="❌"
    log "[STEP 1] claude 실행 실패 (exit=$CLAUDE_EXIT)"
fi

# ────────────────────────────────────────────────────────
# STEP 2: 뉴스레터 파일 생성 확인
# ────────────────────────────────────────────────────────
log_sep
log "[STEP 2] 뉴스레터 파일 검증: $NEWSLETTER_FILE"

if [ -f "$NEWSLETTER_FILE" ]; then
    FILE_SIZE=$(wc -c < "$NEWSLETTER_FILE")
    if [ "$FILE_SIZE" -gt 200 ]; then
        STEP_FILE="✅"
        log "[STEP 2] 파일 확인 완료 — ${FILE_SIZE}자"
    else
        STEP_FILE="❌"
        log "[STEP 2] 파일 너무 작음 — ${FILE_SIZE}자 (생성 실패 의심)"
    fi
else
    STEP_FILE="❌"
    log "[STEP 2] 파일 없음 — 뉴스레터 생성 실패"
fi

# ────────────────────────────────────────────────────────
# STEP 3: 텔레그램 전송 결과 확인 (claude 출력 파싱)
# ────────────────────────────────────────────────────────
log_sep
log "[STEP 3] 텔레그램 전송 결과 확인"

if echo "$CLAUDE_OUTPUT" | grep -qiE "(TELEGRAM_STATUS=OK|텔레그램.*성공|전송 성공|msg_id=)"; then
    STEP_TELEGRAM="✅"
    log "[STEP 3] 텔레그램 전송 확인됨"
elif echo "$CLAUDE_OUTPUT" | grep -qiE "(TELEGRAM_STATUS=FAIL|텔레그램.*실패|401|Unauthorized)"; then
    STEP_TELEGRAM="❌"
    log "[STEP 3] 텔레그램 전송 실패 감지"
else
    STEP_TELEGRAM="⚠️"
    log "[STEP 3] 텔레그램 전송 결과 불명확 — claude 출력 확인 필요"
fi

# ────────────────────────────────────────────────────────
# STEP 4: Gmail SMTP 실제 발송
# ────────────────────────────────────────────────────────
log_sep
log "[STEP 4] Gmail SMTP 발송 시작"

if [ "$STEP_FILE" != "✅" ]; then
    STEP_EMAIL="❌"
    EMAIL_MSG="뉴스레터 파일 없음 — 이메일 발송 건너뜀"
    log "[STEP 4] $EMAIL_MSG"
else
    EMAIL_RESULT=$(python3 "$SEND_EMAIL" 2>&1)
    EMAIL_EXIT=$?
    log "[STEP 4] send_email.py 출력: $EMAIL_RESULT"

    if [ "$EMAIL_EXIT" -eq 0 ]; then
        STEP_EMAIL="✅"
        EMAIL_MSG=$(echo "$EMAIL_RESULT" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null \
            || echo "전송 완료")
        log "[STEP 4] Gmail 발송 성공 — $EMAIL_MSG"
    else
        STEP_EMAIL="❌"
        EMAIL_MSG=$(echo "$EMAIL_RESULT" | python3 -c \
            "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null \
            || echo "$EMAIL_RESULT")
        log "[STEP 4] Gmail 발송 실패 — $EMAIL_MSG"
    fi
fi

# ────────────────────────────────────────────────────────
# STEP 5: 최종 결과 텔레그램 통보
# ────────────────────────────────────────────────────────
log_sep
log "[STEP 5] 최종 결과 텔레그램 통보"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M KST')

SUMMARY="📋 뉴스레터 발송 결과 (${TIMESTAMP})
──────────────────────
${STEP_CLAUDE} STEP1 뉴스 수집 (claude)
${STEP_FILE} STEP2 파일 생성 검증
${STEP_TELEGRAM} STEP3 텔레그램 전송
${STEP_EMAIL} STEP4 Gmail 발송
──────────────────────"

if [ "$STEP_EMAIL" = "✅" ] && [ "$STEP_FILE" = "✅" ]; then
    SUMMARY="${SUMMARY}
✅ 모든 단계 성공"
else
    SUMMARY="${SUMMARY}
⚠️ 일부 단계 실패 — 로그 확인: ${LOG_FILE}"
fi

tg_send "$SUMMARY"
log "[STEP 5] 결과 통보 완료"

# ── 최종 로그 ─────────────────────────────────────────────
log_sep
log "claude=${STEP_CLAUDE} | 파일=${STEP_FILE} | 텔레그램=${STEP_TELEGRAM} | 이메일=${STEP_EMAIL}"
log "===== 완료 ====="

# 30일 이상 된 로그 삭제
find "$LOG_DIR" -name "newsletter_*.log" -mtime +30 -delete 2>/dev/null || true

# 이메일 실패 시 비정상 종료
[ "$STEP_EMAIL" = "✅" ] && exit 0 || exit 1
