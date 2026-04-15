#!/usr/bin/env python3
"""
Gmail OAuth2 초기 설정 스크립트 (최초 1회 실행)
- Google Cloud Console에서 발급받은 Client ID/Secret으로 Refresh Token 획득
- 발급된 Refresh Token을 .env 파일에 자동 저장
- 이후 크론에서 send_email.py가 Refresh Token으로 Access Token을 갱신하며 실제 발송

사전 조건:
  1. https://console.cloud.google.com → 프로젝트 생성
  2. Gmail API 활성화
  3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱 유형)
  4. Client ID / Client Secret 복사
"""

import json
import os
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"
SCOPE = "https://www.googleapis.com/auth/gmail.send"
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"  # 복사+붙여넣기 방식


def update_env(key: str, value: str):
    """기존 .env 파일의 키를 업데이트하거나 추가"""
    lines = []
    found = False
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if line.startswith(f"{key}="):
                lines.append(f'{key}="{value}"')
                found = True
            else:
                lines.append(line)
    if not found:
        lines.append(f'{key}="{value}"')
    ENV_FILE.write_text("\n".join(lines) + "\n")


def main():
    print("=" * 55)
    print("  Gmail OAuth2 설정 (최초 1회)")
    print("=" * 55)
    print()
    print("사전 준비 (Google Cloud Console):")
    print("  1. https://console.cloud.google.com 접속")
    print("  2. 새 프로젝트 생성 (예: wellfare-newsletter)")
    print("  3. 왼쪽 메뉴 → API 및 서비스 → 라이브러리")
    print("     → 'Gmail API' 검색 → 사용 설정")
    print("  4. API 및 서비스 → 사용자 인증 정보")
    print("     → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID")
    print("     → 애플리케이션 유형: 데스크톱 앱 → 만들기")
    print("  5. 클라이언트 ID / 클라이언트 보안 비밀번호 복사")
    print()

    client_id = input("Client ID 입력: ").strip()
    if not client_id:
        print("❌ Client ID가 비어 있습니다.")
        sys.exit(1)

    client_secret = input("Client Secret 입력: ").strip()
    if not client_secret:
        print("❌ Client Secret이 비어 있습니다.")
        sys.exit(1)

    # OAuth 인증 URL 생성
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPE,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)

    print()
    print("아래 URL을 브라우저에서 열어 soonhak.ahn@gmail.com 계정으로 로그인 후")
    print("권한을 허용하면 인증 코드가 표시됩니다:")
    print()
    print(f"  {auth_url}")
    print()
    try:
        webbrowser.open(auth_url)
        print("  (브라우저가 자동으로 열렸습니다)")
    except Exception:
        pass

    auth_code = input("인증 코드 붙여넣기: ").strip()
    if not auth_code:
        print("❌ 인증 코드가 비어 있습니다.")
        sys.exit(1)

    # 인증 코드 → Access Token + Refresh Token 교환
    print()
    print("토큰 발급 중...")
    token_data = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=token_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"❌ 토큰 발급 실패: {e.code} {body}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("❌ Refresh Token이 없습니다. 이미 동일 계정으로 인증한 경우,")
        print("   Google Cloud Console → OAuth 동의 화면 → 테스트 사용자에서 앱을 재설정하세요.")
        sys.exit(1)

    # .env 저장
    update_env("GMAIL_CLIENT_ID", client_id)
    update_env("GMAIL_CLIENT_SECRET", client_secret)
    update_env("GMAIL_REFRESH_TOKEN", refresh_token)

    print()
    print("✅ 설정 완료! .env에 저장되었습니다:")
    print(f"   GMAIL_CLIENT_ID    = {client_id[:20]}...")
    print(f"   GMAIL_CLIENT_SECRET = {client_secret[:8]}...")
    print(f"   GMAIL_REFRESH_TOKEN = {refresh_token[:20]}...")
    print()
    print("이제 크론에서 Gmail 발송이 가능합니다.")
    print("테스트: python3 send_email.py")


if __name__ == "__main__":
    main()
