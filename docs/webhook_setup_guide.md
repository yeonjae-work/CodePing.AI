# 🔗 웹훅 설정 가이드

CodePing.AI 웹훅 시스템 설정 방법을 안내합니다.

## 🎯 개요

CodePing.AI는 GitHub 웹훅을 통해 코드 변경사항을 실시간으로 수신하고 처리합니다.

### 📦 현재 모듈 구조
- **로컬 모듈**: `shared/`, `infrastructure/` 사용 중
- **PyPI 패키지**: `universal_llm_service` 설치됨
- **웹훅 처리**: 내장 FastAPI 라우터 사용

## 🌐 웹훅 엔드포인트

### 기본 엔드포인트
- **GitHub 전용**: `POST /webhook/github`
- **범용 웹훅**: `POST /webhook/`

### 환경별 페이로드 URL

#### 🔧 로컬 개발 환경
```
https://your-ngrok-url.ngrok.io/webhook/github
```

#### 🐳 Docker 환경
```
http://your-server-ip:8000/webhook/github
```

#### 🚀 프로덕션 환경
```
https://your-domain.com/webhook/github
```

## ⚙️ GitHub 웹훅 설정

### 1. GitHub 저장소 설정

1. GitHub 저장소로 이동
2. **Settings** → **Webhooks** → **Add webhook**

### 2. 웹훅 구성

| 설정 항목 | 값 |
|----------|---|
| **Payload URL** | `https://your-domain.com/webhook/github` |
| **Content type** | `application/json` |
| **Secret** | 환경변수 `WEBHOOK_SECRET` 값 |
| **SSL verification** | Enable SSL verification |

### 3. 이벤트 선택

다음 이벤트를 선택하세요:

- ✅ **Push events** - 코드 푸시 시
- ✅ **Pull request events** - PR 생성/업데이트 시
- ✅ **Release events** - 릴리스 생성 시

### 4. 활성화

- ✅ **Active** 체크박스 선택

## 🔐 보안 설정

### 환경 변수 설정

```bash
# .env 파일
WEBHOOK_SECRET=your-webhook-secret-key
GITHUB_TOKEN=your-github-token
SLACK_BOT_TOKEN=your-slack-bot-token
OPENAI_API_KEY=your-openai-api-key
```

### Secret 검증

웹훅 요청의 진위를 확인하기 위해 GitHub Secret을 사용합니다:

```python
# 내장 검증 로직 (shared/utils/ 모듈에서 처리)
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 🧪 테스트

### 1. 웹훅 테스트

GitHub 웹훅 설정 페이지에서:
1. **Recent Deliveries** 섹션 확인
2. **Redeliver** 버튼으로 재전송 테스트

### 2. 로컬 테스트

```bash
# 애플리케이션 실행
python main.py

# 또는 Docker로 실행
docker run -p 8000:8000 codeping-ai:latest
```

### 3. 수동 테스트

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{"ref": "refs/heads/main", "repository": {"name": "test-repo"}}'
```

## 🔍 트러블슈팅

### 일반적인 문제들

#### 1. 웹훅이 도달하지 않는 경우
- 방화벽 설정 확인
- 포트 8000 개방 여부 확인
- HTTPS 인증서 유효성 확인

#### 2. Secret 검증 실패
```bash
# 환경 변수 확인
echo $WEBHOOK_SECRET

# GitHub 설정과 일치하는지 확인
```

#### 3. 모듈 import 오류
```bash
# 현재 사용 중인 모듈 구조
ls -la shared/
ls -la infrastructure/

# PyPI 패키지 확인
pip list | grep universal
```

#### 4. 데이터베이스 연결 오류
```bash
# 환경 변수 확인
echo $DATABASE_URL

# 데이터베이스 상태 확인
python -c "from shared.config.database import engine; print('DB OK')"
```

### 로그 확인

```bash
# 애플리케이션 로그
tail -f logs/app.log

# Docker 로그
docker logs container-name
```

## 📊 모니터링

### 웹훅 통계 확인

GitHub 저장소 설정에서:
1. **Webhooks** → 해당 웹훅 클릭
2. **Recent Deliveries** 섹션에서 성공/실패 확인

### 응답 코드

| 코드 | 의미 |
|------|------|
| 200 | 성공적으로 처리됨 |
| 400 | 잘못된 요청 형식 |
| 401 | 인증 실패 (Secret 불일치) |
| 500 | 서버 내부 오류 |

## 🚀 고급 설정

### 조건부 처리

특정 브랜치나 파일 변경 시에만 처리하려면:

```python
# shared/utils/webhook_filter.py (예시)
def should_process_webhook(payload):
    ref = payload.get('ref', '')
    if ref == 'refs/heads/main':  # main 브랜치만
        return True
    return False
```

### 배치 처리

대량의 웹훅 처리를 위한 큐 시스템:

```python
# Celery 작업자 (shared/config/celery_app.py)
from celery import Celery

app = Celery('webhook_processor')

@app.task
def process_webhook_async(payload):
    # 비동기 웹훅 처리
    pass
```

## 📞 지원

문제가 발생하면:
1. [GitHub Issues](https://github.com/yeonjae-work/CodePing.AI/issues) 확인
2. 로그 파일과 함께 이슈 생성
3. 환경 정보 (OS, Python 버전, Docker 버전) 포함

---

> **참고**: 현재 대부분의 기능이 로컬 모듈(`shared/`, `infrastructure/`)로 구현되어 있으며, 
> 안정화 후 순차적으로 PyPI 패키지로 마이그레이션될 예정입니다. 