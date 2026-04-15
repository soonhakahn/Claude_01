#!/usr/bin/env python3
"""
Gmail SMTP 발송 스크립트
- /tmp/newsletter.txt 를 읽어 soonhak.ahn@gmail.com 으로 전송
- 성공: exit 0 + JSON {"status":"OK","message":"..."}
- 실패: exit 1 + JSON {"status":"FAIL","message":"..."}

환경변수 (run_newsletter.sh 에서 .env 로드):
  GMAIL_SENDER       발신 Gmail 주소
  GMAIL_APP_PASSWORD Gmail 앱 비밀번호 (16자리)
  GMAIL_TO           수신 주소 (기본: soonhak.ahn@gmail.com)
"""

import json
import os
import smtplib
import sys
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

NEWSLETTER_FILE = "/tmp/newsletter.txt"
KST = timezone(timedelta(hours=9))


def result(status: str, message: str, extra: dict = None):
    data = {"status": status, "message": message, **(extra or {})}
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if status == "OK" else 1)


def main():
    sender   = os.environ.get("GMAIL_SENDER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    to_addr  = os.environ.get("GMAIL_TO", "soonhak.ahn@gmail.com").strip()

    # ── 환경변수 검증 ─────────────────────────────────────
    if not sender:
        result("FAIL", "GMAIL_SENDER 환경변수 미설정")
    if not password:
        result("FAIL", "GMAIL_APP_PASSWORD 환경변수 미설정")

    # ── 뉴스레터 파일 읽기 ────────────────────────────────
    if not os.path.exists(NEWSLETTER_FILE):
        result("FAIL", f"뉴스레터 파일 없음: {NEWSLETTER_FILE}")

    with open(NEWSLETTER_FILE, "r", encoding="utf-8") as f:
        body = f.read().strip()

    if len(body) < 100:
        result("FAIL", f"뉴스레터 내용이 너무 짧음 ({len(body)}자) — 생성 실패 가능성")

    # ── 제목 생성 ─────────────────────────────────────────
    now_kst = datetime.now(KST)
    hour_utc = datetime.now(timezone.utc).hour
    if 10 <= hour_utc <= 12:
        edition = "🌙 저녁 에디션"
    elif hour_utc >= 22 or hour_utc == 0:
        edition = "☀️ 아침 에디션"
    else:
        edition = "🌙 저녁 에디션"

    date_str = now_kst.strftime("%Y년 %m월 %d일")
    subject  = f"[사회복지 뉴스레터] {date_str} {edition}"

    # ── 이메일 구성 ───────────────────────────────────────
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = to_addr
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # ── Gmail SMTP 전송 ───────────────────────────────────
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(sender, password)
            server.sendmail(sender, [to_addr], msg.as_string())

        result("OK", f"이메일 전송 성공", {
            "to": to_addr,
            "subject": subject,
            "size": len(body),
        })

    except smtplib.SMTPAuthenticationError:
        result("FAIL", "Gmail 인증 실패 — 앱 비밀번호를 확인하세요 "
               "(Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호)")
    except smtplib.SMTPException as e:
        result("FAIL", f"SMTP 오류: {e}")
    except OSError as e:
        result("FAIL", f"네트워크 오류: {e}")


if __name__ == "__main__":
    main()
