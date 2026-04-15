#!/usr/bin/env python3
"""
사회복지 & 사회적협동조합 뉴스레터 자동화 스크립트
- 매일 10:00 UTC (저녁 에디션) / 22:00 UTC (아침 에디션) 실행
- 텔레그램 전송 + Gmail 발송
"""

import subprocess
import urllib.request
import urllib.parse
import json
import smtplib
import os
import sys
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── 설정 ──────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8550163156:AAEQYbsXM30m_PqUM4zG2qSqMK-Y9erWZt8")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "1472020115")
TELEGRAM_API_URL   = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

GMAIL_SENDER   = os.environ.get("GMAIL_SENDER", "")       # 발신 Gmail 주소
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")  # Gmail 앱 비밀번호
GMAIL_TO       = os.environ.get("GMAIL_TO", "soonhak.ahn@gmail.com")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
NEWSLETTER_PATH   = "/tmp/newsletter.txt"
MAX_CHUNK_SIZE    = 3800  # Telegram 메시지 최대 글자 수

KST = timezone(timedelta(hours=9))


def get_edition():
    """UTC 시각 기준으로 에디션 결정"""
    hour_utc = datetime.now(timezone.utc).hour
    if 10 <= hour_utc <= 12:
        return "저녁", "🌙"
    elif hour_utc >= 22 or hour_utc == 0:
        return "아침", "☀️"
    else:
        # 기본값: 저녁 에디션
        return "저녁", "🌙"


def get_kst_date():
    now_kst = datetime.now(KST)
    return now_kst.strftime("%Y년 %m월 %d일"), now_kst.strftime("%Y-%m-%d")


def generate_newsletter_via_claude():
    """Claude CLI를 통해 뉴스레터 생성"""
    edition_name, edition_icon = get_edition()
    kst_date_kr, kst_date = get_kst_date()

    prompt = f"""당신은 사회복지 뉴스레터 에이전트입니다. 오늘 날짜 {kst_date_kr} ({edition_icon} {edition_name} 에디션) 기준으로 아래 형식의 한국 사회복지 뉴스레터를 작성해주세요.

다음 주제를 웹에서 검색해 최신 뉴스를 반영하세요:
1. 한국 사회복지 법령 개정 동향
2. 지자체 사회복지 정책 소식
3. 사회적협동조합 관련 뉴스
4. 사회복지관 현장 소식
5. 사회보장 제도 변경 사항

형식:
=====[ 사회복지 & 사회적협동조합 뉴스레터 ]=====
{kst_date_kr} (KST) | {edition_icon} {edition_name} 에디션

[법규 & 제도] 섹션
[지자체 소식] 섹션
[사회적협동조합] 섹션
[법령 동향] 섹션
[출처] 섹션

Claude AI 자동 생성 | 중요 사안은 공식 채널에서 확인하세요"""

    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"[WARN] Claude CLI 오류: {result.stderr[:200]}")
            return None
    except FileNotFoundError:
        print("[WARN] claude CLI 없음 — Anthropic API 직접 호출 시도")
        return generate_via_api(prompt)
    except subprocess.TimeoutExpired:
        print("[ERROR] Claude CLI 타임아웃")
        return None


def generate_via_api(prompt):
    """Anthropic API 직접 호출로 뉴스레터 생성"""
    if not ANTHROPIC_API_KEY:
        print("[ERROR] ANTHROPIC_API_KEY 환경변수 미설정")
        return None

    payload = json.dumps({
        "model": "claude-sonnet-4-6",
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data["content"][0]["text"]
    except Exception as e:
        print(f"[ERROR] Anthropic API 호출 실패: {e}")
        return None


def split_into_chunks(text, max_size=MAX_CHUNK_SIZE):
    """텔레그램 전송용 청크 분할 (섹션 경계 우선)"""
    if len(text) <= max_size:
        return [text]

    chunks = []
    section_markers = ["[법규 & 제도]", "[지자체 소식]", "[사회적협동조합]", "[법령 동향]", "[출처]"]

    # 섹션 경계에서 분할 시도
    remaining = text
    while len(remaining) > max_size:
        split_idx = max_size
        # 섹션 마커 기준 분할점 탐색
        for marker in section_markers:
            idx = remaining.rfind(marker, 0, max_size)
            if idx > 0:
                split_idx = idx
                break
        # 마커 없으면 줄바꿈 기준
        if split_idx == max_size:
            newline_idx = remaining.rfind("\n", 0, max_size)
            if newline_idx > 0:
                split_idx = newline_idx

        chunks.append(remaining[:split_idx].rstrip())
        remaining = remaining[split_idx:].lstrip()

    if remaining:
        chunks.append(remaining)
    return chunks


def send_telegram(text):
    """텔레그램으로 뉴스레터 전송"""
    chunks = split_into_chunks(text)
    success = 0
    for i, chunk in enumerate(chunks, 1):
        data = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": chunk
        }).encode("utf-8")
        req = urllib.request.Request(
            TELEGRAM_API_URL, data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    print(f"  ✅ 텔레그램 청크 {i}/{len(chunks)} 전송 성공")
                    success += 1
                else:
                    print(f"  ❌ 텔레그램 청크 {i} 실패: {result.get('description')}")
        except Exception as e:
            print(f"  ❌ 텔레그램 청크 {i} 오류: {e}")
    return success == len(chunks)


def send_email(subject, body):
    """Gmail SMTP로 이메일 전송"""
    if not GMAIL_SENDER or not GMAIL_PASSWORD:
        print("  [SKIP] Gmail 자격증명 미설정 (GMAIL_SENDER, GMAIL_APP_PASSWORD)")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_SENDER
    msg["To"]      = GMAIL_TO
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, [GMAIL_TO], msg.as_string())
        print(f"  ✅ Gmail 전송 성공 → {GMAIL_TO}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  ❌ Gmail 인증 실패 — 앱 비밀번호 확인 필요")
        return False
    except Exception as e:
        print(f"  ❌ Gmail 전송 오류: {e}")
        return False


def main():
    edition_name, edition_icon = get_edition()
    kst_date_kr, kst_date = get_kst_date()

    print(f"\n{'='*50}")
    print(f"사회복지 뉴스레터 생성 시작")
    print(f"날짜: {kst_date_kr} | 에디션: {edition_icon} {edition_name}")
    print(f"{'='*50}\n")

    # 1. 뉴스레터 생성
    print("[1/3] 뉴스레터 생성 중...")
    newsletter = generate_newsletter_via_claude()

    if not newsletter:
        print("[ERROR] 뉴스레터 생성 실패. 종료.")
        sys.exit(1)

    # 파일 저장
    with open(NEWSLETTER_PATH, "w", encoding="utf-8") as f:
        f.write(newsletter)
    print(f"  → {NEWSLETTER_PATH} 저장 완료 ({len(newsletter)}자)")

    # 2. 텔레그램 전송
    print("\n[2/3] 텔레그램 전송 중...")
    tg_ok = send_telegram(newsletter)

    # 3. 이메일 전송
    print("\n[3/3] 이메일 전송 중...")
    email_subject = f"[사회복지 뉴스레터] {kst_date} {edition_icon} {edition_name} 에디션"
    email_ok = send_email(email_subject, newsletter)

    print(f"\n{'='*50}")
    print(f"완료 — 텔레그램: {'✅' if tg_ok else '❌'} | 이메일: {'✅' if email_ok else '❌'}")
    print(f"{'='*50}\n")

    if not tg_ok and not email_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
