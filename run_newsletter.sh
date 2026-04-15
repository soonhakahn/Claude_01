#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="/home/user/claude_01_wellfare_news"
LOG_DIR="$SCRIPT_DIR/logs"
ENV_FILE="$SCRIPT_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

LOG_FILE="$LOG_DIR/newsletter_$(date +%Y%m%d_%H%M%S).log"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 뉴스레터 실행 시작" | tee "$LOG_FILE"
python3 "$SCRIPT_DIR/newsletter.py" 2>&1 | tee -a "$LOG_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 완료" | tee -a "$LOG_FILE"
find "$LOG_DIR" -name "newsletter_*.log" -mtime +30 -delete 2>/dev/null || true
