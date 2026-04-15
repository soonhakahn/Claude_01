#!/usr/bin/env python3
"""
Gmail 실제 발송 스크립트 (Gmail REST API over HTTPS)
- SMTP 대신 Gmail API를 사용 (포트 443만 필요)
- Refresh Token으로 Access Token을 자동 갱신
- 성공: exit 0 + JSON {"status":"OK","message":"..."}
- 실패: exit 1 + JSON {"status":"FAIL","message":"..."}

.env 필요 항목:
  GMAIL_SENDER        발신 Gmail 주소
  GMAIL_CLIENT_ID     Google OAuth 클라이언트 ID
  GMAIL_CLIENT_SECRET Google OAuth 클라이언트 보안 비밀
  GMAIL_REFRESH_TOKEN OAuth Refresh Token (setup_gmail_oauth.py 로 발급)
  GMAIL_TO            수신 주소 (기본: soonhak.ahn@gmail.com)
"""

import base64
import json
import os
import sys
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText

NEWSLETTER_FILE = "/tmp/newsletter.txt"
KST = timezone(timedelta(hours=9))
GMAIL_SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
TOKEN_URL = "https://oauth2.googleapis.com/token"


def result(status: str, message: str, extra: dict = None):
    data = {"status": status, "message": message, **(extra or {})}
    print(json.dumps(data, ensure_ascii=False))
    sys.exit(0 if status == "OK" else 1)


def get_access_token(client_id: str, client_secret: str, refresh_token: str) -> str:
    """Refresh Token으로 Access Token 발급"""
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        TOKEN_URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            token_data = json.loads(resp.read())
            access_token = token_data.get("access_token")
            if not access_token:
                result("FAIL", f"Access Token 발급 실패: {token_data}")
            return access_token
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        result("FAIL", f"Token 갱신 실패 ({e.code}): {body[:200]}")
    except Exception as e:
        result("FAIL", f"Token 요청 오류: {e}")


def send_via_gmail_api(access_token: str, sender: str, to: str,
                       subject: str, body: str) -> dict:
    """Gmail REST API로 이메일 실제 발송"""
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    payload = json.dumps({"raw": raw}).encode()
    req = urllib.request.Request(
        GMAIL_SEND_URL, data=payload,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        result("FAIL", f"Gmail API 발송 실패 ({e.code}): {body[:300]}")
    except Exception as e:
        result("FAIL", f"Gmail API 오류: {e}")


def get_edition_label() -> str:
    hour_utc = datetime.now(timezone.utc).hour
    if 10 <= hour_utc <= 12:
        return "🌙 저녁 에디션"
    elif hour_utc >= 22 or hour_utc == 0:
        return "☀️ 아침 에디션"
    return "🌙 저녁 에디션"


def main():
    # ── 환경변수 로드 ──────────────────────────────────────
    sender        = os.environ.get("GMAIL_SENDER", "").strip()
    client_id     = os.environ.get("GMAIL_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GMAIL_REFRESH_TOKEN", "").strip()
    to_addr       = os.environ.get("GMAIL_TO", "soonhak.ahn@gmail.com").strip()

    # ── 환경변수 검증 ──────────────────────────────────────
    missing = [k for k, v in {
        "GMAIL_SENDER": sender,
        "GMAIL_CLIENT_ID": client_id,
        "GMAIL_CLIENT_SECRET": client_secret,
        "GMAIL_REFRESH_TOKEN": refresh_token,
    }.items() if not v]
    if missing:
        result("FAIL",
               f"환경변수 미설정: {', '.join(missing)} "
               f"— python3 setup_gmail_oauth.py 실행 필요")

    # ── 뉴스레터 파일 읽기 ────────────────────────────────
    if not os.path.exists(NEWSLETTER_FILE):
        result("FAIL", f"뉴스레터 파일 없음: {NEWSLETTER_FILE}")

    with open(NEWSLETTER_FILE, "r", encoding="utf-8") as f:
        body = f.read().strip()

    if len(body) < 100:
        result("FAIL", f"뉴스레터 내용 너무 짧음 ({len(body)}자)")

    # ── 제목 생성 ─────────────────────────────────────────
    date_str = datetime.now(KST).strftime("%Y년 %m월 %d일")
    subject  = f"[사회복지 뉴스레터] {date_str} {get_edition_label()}"

    # ── Access Token 발급 ─────────────────────────────────
    access_token = get_access_token(client_id, client_secret, refresh_token)

    # ── Gmail API 발송 ────────────────────────────────────
    api_result = send_via_gmail_api(access_token, sender, to_addr, subject, body)

    msg_id = api_result.get("id", "unknown")
    result("OK", f"Gmail 발송 성공", {
        "to": to_addr,
        "subject": subject,
        "message_id": msg_id,
        "size": len(body),
    })


if __name__ == "__main__":
    main()
