# 사회복지 & 사회적협동조합 뉴스레터 자동화

Claude AI가 매일 두 번 한국 사회복지 뉴스를 수집하여 텔레그램과 이메일로 발송하는 자동화 시스템입니다.

## 파일 구조

```
claude_01_wellfare_news/
├── newsletter.py       # 메인 뉴스레터 생성·발송 스크립트
├── run_newsletter.sh   # 크론 실행 래퍼 (로그 포함)
├── setup_cron.sh       # 크론 자동 등록 스크립트
├── crontab.txt         # 크론 설정 파일 (수동 등록용)
├── .env.example        # 환경변수 템플릿
├── .env                # 실제 환경변수 (git 제외)
└── logs/               # 실행 로그 디렉터리
```

## 빠른 시작

### 1. 환경변수 설정

```bash
cp .env.example .env
nano .env   # 아래 값들을 실제 값으로 수정
```

| 변수 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude CLI 있으면 불필요) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 토큰 (@shahn01bot) |
| `TELEGRAM_CHAT_ID` | 텔레그램 채팅 ID |
| `GMAIL_SENDER` | 발신 Gmail 주소 |
| `GMAIL_APP_PASSWORD` | Gmail 앱 비밀번호 (16자리) |
| `GMAIL_TO` | 수신 이메일 주소 |

> Gmail 앱 비밀번호: Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호

### 2. 크론 등록

**자동 등록 (권장):**
```bash
bash setup_cron.sh
```

**수동 등록:**
```bash
crontab crontab.txt
# 또는
crontab -e   # 편집기에서 crontab.txt 내용 붙여넣기
```

### 3. 즉시 테스트 실행

```bash
bash run_newsletter.sh
```

## 실행 일정

| 에디션 | UTC | KST |
|--------|-----|-----|
| ☀️ 아침 에디션 | 22:00 | 07:00 |
| 🌙 저녁 에디션 | 10:00 | 19:00 |

## 뉴스레터 섹션

- **[법규 & 제도]** — 사회복지 법령 개정, 제도 변경
- **[지자체 소식]** — 각 지방자치단체 복지 정책
- **[사회적협동조합]** — 협동조합 관련 뉴스 및 정책
- **[법령 동향]** — 법제처 API 기반 법령 동향
- **[출처]** — 참고 URL 목록

## 발송 채널

- **텔레그램**: @shahn01bot → 채팅 ID `1472020115`
- **이메일**: Gmail SMTP → `soonhak.ahn@gmail.com`

## 로그 확인

```bash
ls -lt logs/
tail -f logs/newsletter_최신파일.log
```

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 텔레그램 401 | 봇 토큰 만료 | `.env`의 `TELEGRAM_BOT_TOKEN` 갱신 |
| Gmail 인증 실패 | 앱 비밀번호 오류 | Google 계정에서 앱 비밀번호 재생성 |
| Claude CLI 없음 | claude 미설치 | `ANTHROPIC_API_KEY` 설정으로 API 직접 호출 |
