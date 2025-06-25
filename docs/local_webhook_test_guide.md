# CodePing.AI WebhookReceiver (Phase 1) 로컬 테스트 가이드

`yeonjae-work/vizier-rule-ai-system` GitHub 저장소의 **Push 이벤트**가 로컬에서 실행 중인 CodePing.AI WebhookReceiver 로 정상 수신·처리되는지 검증하는 절차를 단계별로 정리했습니다.

> ⚙️ 본 가이드는 macOS (Native) 환경을 기준으로 작성되었습니다. Windows/Linux 도 동일 명령으로 동작합니다.

---

## 1. 사전 준비

| 항목 | 버전/설명 |
|------|-----------|
| Python | **3.11 또는 3.12**<br/>(3.13 미지원) |
| pip / virtualenv | 최신 버전 권장 |
| GitHub 계정 | `push` 이벤트 발생용 |
| GitHub Personal Access Token | API 호출(옵션) |
| 포트 포워딩 도구 | **하나 선택** → `ngrok`, `cloudflared`, `localhost.run` 등 |

---

## 2. CodePing.AI 프로젝트 세팅

```bash
# ① 레포지토리 클론
$ git clone https://github.com/roselinelee/CodePing.AI.git
$ cd CodePing.AI

# ② 가상환경 생성 및 활성화
# macOS 기본 환경: Homebrew python@3.12 사용 예시
$ brew install python@3.12     # 이미 설치돼 있으면 건너뜀
$ /usr/local/opt/python@3.12/bin/python3 -m venv .venv && source .venv/bin/activate

# ③ 의존성 설치
$ pip install -r requirements.txt

# ④ 환경 변수 파일 작성(.env)
$ cat > .env <<'EOF'
GITHUB_WEBHOOK_SECRET=mydevsecret
DATABASE_URL=sqlite+aiosqlite:///./dev.db

# ----- (선택) diff 패치 저장 관련 -----
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_ALWAYS_EAGER=true         # 워커 없이 즉시 실행 (디버깅)
# AWS_ACCESS_KEY_ID=xxx            # S3 업로드(256 KB 초과 patch)
# AWS_SECRET_ACCESS_KEY=yyy
# AWS_S3_BUCKET=codeping-dev-diff
EOF
```

### 2-1. 서버 구동
```bash
$ uvicorn app.main:app --reload --port 9000
```

정상적으로 기동되면 `http://localhost:9000/docs` 에서 Swagger UI를 확인할 수 있습니다.

### 2-2. Celery 워커 구동 (선택)
> diff 패치를 실제로 저장하려면 Celery와 브로커(Redis 등)가 필요합니다.

```bash
# ① Redis (Homebrew) 설치 후 실행
a$ brew install redis && brew services start redis

# ② Celery 워커 실행 (별도 터미널 탭)
$ source .venv/bin/activate
$ celery -A app.celery_app worker --loglevel=info
```

`CELERY_ALWAYS_EAGER=true` 값을 사용하면 워커 없이도 테스트 가능하지만, **diff 패치 본문은 저장되지 않고 메타데이터만 기록**됩니다.

---

## 3. 터널링(옵션)
로컬 서버를 외부 GitHub Webhook과 연결하려면 공용 URL이 필요합니다. `ngrok` 사용 예시는 다음과 같습니다.

> ⚠️ 처음 사용하는 경우, `ngrok` 실행 전에 **가입 → Authtoken 등록**이 필요합니다.
> 1) https://dashboard.ngrok.com/signup 에서 무료 계정 생성  
> 2) 대시보드 `Your Authtoken` 복사  
> 3) 터미널에서 `ngrok config add-authtoken <복사한-토큰>` 실행 (v3 기준)  
>    - 구버전(v2)은 `ngrok authtoken <토큰>` 형식

```bash
# ngrok 설치가 안 되어 있다면 ↓
# brew install --cask ngrok

# 9000 포트를 외부로 노출
$ ngrok http 9000

# 예시 출력
Forwarding https://e3ab-99-999-999-99.ngrok-free.app -> http://localhost:9000
```

`Forwarding` URL(예: `https://e3ab-99-…ngrok-free.app`)을 복사해 두세요.

---

## 4. GitHub Webhook 설정

1. 저장소 **Settings → Webhooks → Add webhook** 선택  
2. **Payload URL**  
   `https://<Forwarding-URL>/webhook` (예: `https://e3ab-99-…ngrok-free.app/webhook`)
3. **Content type**: `application/json`
4. **Secret**: `.env` 에서 지정한 `GITHUB_WEBHOOK_SECRET` 값 (`mydevsecret`)
5. **Which events would you like to trigger this webhook?** →  **Just the push event** 선택
6. **Active** 체크 후 **Add webhook** 저장

> ✅ _Phase 1 MVP는 Push 이벤트만 처리합니다._ 다른 이벤트는 추후 지원 예정입니다.

---

## 5. 테스트 실행

### 5-1. 실제 커밋 푸시
```bash
$ cd /path/to/vizier-rule-ai-system
$ echo "# test" >> README.md
$ git add README.md && git commit -m "docs: test webhook" && git push origin main
```
푸시가 완료되면:

* GitHub Actions CI/CD가 실행됨 (기존 워크플로)  
* 동시적으로 **Webhook** POST → CodePing 서버 수신

### 5-2. 결과 확인

1. CodePing.AI 서버 터미널에서 다음과 같은 로그가 찍히는지 확인합니다.
   ```text
   Received ValidatedEvent(repository='yeonjae-work/vizier-rule-ai-system', ...)
   Saved to DB: commits=1
   ```
2. SQLite DB(`dev.db`) 검사 *(선택)*
   ```bash
   $ sqlite3 dev.db "SELECT id, repository, pusher_name, received_at FROM events;"
   ```

### 5-3. diff 패치 저장 확인 (선택)
Celery 워커가 정상 동작 중이라면 push 이벤트 이후 워커 로그에 다음과 같은 메시지가 출력됩니다.
```text
[diff_tasks.process_webhook] gzip_size=12.3 KB stored_in=db added=210 deleted=53 files=4
```
DB에서도 `diff_patch`(BLOB) 또는 `diff_url`(S3) 필드가 채워진 것을 확인할 수 있습니다.
```bash
$ sqlite3 dev.db "SELECT repository, commit_sha, length(diff_patch) AS bytes, diff_url FROM events ORDER BY id DESC LIMIT 3;"
```

---

## 6. (선택) GitHub Actions 후처리 방식
배포까지 성공한 경우에만 CodePing으로 보내고 싶다면 workflow YAML에 다음 스텝을 추가할 수 있습니다.
```yaml
- name: Notify CodePing (on success)
  if: ${{ success() }}
  env:
    CODEPING_SECRET: ${{ secrets.CODEPING_SECRET }}
  run: |
    curl -X POST \
      -H "X-CodePing-Secret: $CODEPING_SECRET" \
      -H "Content-Type: application/json" \
      --data @<(jq -n --arg repo "$GITHUB_REPOSITORY" \
                      --arg sha "$GITHUB_SHA" \
                      --arg author "${{ github.actor }}" \
                      --arg now "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '
          {repository:{full_name:$repo}, after:$sha, pusher:{name:$author},
           commits:[{id:$sha, timestamp:$now, message:"CI success"}]}
      ') \
      https://<Forwarding-URL>/webhook
```

---

## 7. 문제 해결 FAQ
| 증상 | 원인/해결 |
|------|-----------|
| `401 Unauthorized` | Secret 값 불일치 → GitHub Webhook Secret & `.env` 확인 |
| `404 Not Found` | Payload URL 오타 또는 터널 종료됨 → ngrok 세션 확인 |
| `sqlite3.OperationalError: no such table` | 서버 처음 실행 시 테이블 생성 안 됨 → 서버 재시작 또는 `/startup` 로그에서 `Created tables` 확인 |
| `diff_patch=NULL` | Celery 미동작 또는 `CELERY_ALWAYS_EAGER=true` 설정 → 워커 동작 여부 및 환경 변수 확인 |
| `redis.exceptions.ConnectionError` | Redis 미기동 또는 브로커 URL 오타 → `brew services start redis` 및 `CELERY_BROKER_URL` 확인 |

---

## 8. End-to-End 파이프라인 점검 (08:00 KST 요약 제외)
> Push → Webhook → Celery → DB/S3 전 과정을 한 번에 검증합니다.
> Slack 일일 요약(08:00 KST) 기능은 Phase 2에서 구현될 예정입니다.

---

### ✅ 이제 로컬 환경에서 CodePing.AI WebhookReceiver가 vizier-rule-ai-system 저장소의 Push 이벤트를 정상 수신·처리합니다. 추가 질문이 있으면 언제든 말씀해주세요! 