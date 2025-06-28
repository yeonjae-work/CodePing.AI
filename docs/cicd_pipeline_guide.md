# 🚀 CodePing.AI 간단한 CI/CD 파이프라인

## 📋 개요

CodePing.AI의 CI/CD 파이프라인을 간단하고 이해하기 쉽게 구성했습니다. 하나의 워크플로우 파일로 모든 핵심 기능을 제공합니다.

## 🏗️ 파이프라인 구조

```
🚀 CodePing.AI CI/CD Pipeline
├── 🧪 Test & Quality Check    # 테스트 및 코드 품질 검사
├── 🐳 Docker Build           # Docker 이미지 빌드 (main 브랜치만)
├── 📚 Documentation          # 문서 자동 생성 (main 브랜치만)
├── 🚀 Deploy to Production   # 프로덕션 배포 (main 브랜치만)
└── 📱 Notification          # 결과 알림
```

## 📁 워크플로우 파일

### `.github/workflows/main.yml`
- **역할**: 모든 CI/CD 기능을 통합한 단일 워크플로우
- **트리거**: 
  - `main`, `develop` 브랜치 push
  - `main` 브랜치 PR
  - 수동 실행 (`workflow_dispatch`)

## 🔧 Job 상세 설명

### 1. 🧪 Test & Quality Check
**실행 조건**: 모든 트리거에서 실행

**수행 작업**:
- Python 환경 설정 (3.12)
- PostgreSQL 테스트 DB 준비
- 의존성 설치
- 코드 품질 검사:
  - `black`: 코드 포매팅 검사
  - `flake8`: 린팅 검사
  - `bandit`: 보안 스캔
  - `safety`: 의존성 취약점 검사
- 테스트 실행:
  - `pytest`: 단위 테스트
  - 코드 커버리지 측정
  - PyPI 패키지 12개 import 테스트
- 커버리지 리포트 업로드 (Codecov)

### 2. 🐳 Docker Build
**실행 조건**: `main` 브랜치 push 시, 테스트 성공 후

**수행 작업**:
- Docker 이미지 빌드
- 이미지 내부에서 Python 및 모듈 import 테스트

### 3. 📚 Documentation
**실행 조건**: `main` 브랜치 push 시, 테스트 성공 후

**수행 작업**:
- 코드/문서 변경 감지
- API 문서 생성 (pdoc3)
- 코드 메트릭 수집 (커버리지, 복잡도)
- 변경 로그 생성 (최근 10개 커밋)
- GitHub Pages 배포

### 4. 🚀 Deploy to Production
**실행 조건**: `main` 브랜치 push 시, 테스트와 Docker 빌드 성공 후

**수행 작업**:
- 프로덕션 배포 시뮬레이션
- 배포 정보 출력
- 헬스 체크

### 5. 📱 Notification
**실행 조건**: 모든 Job 완료 후 (성공/실패 관계없이)

**수행 작업**:
- 파이프라인 결과 요약
- 성공 시: 문서 링크 제공
- 실패 시: 오류 알림

## 🎯 핵심 특징

### ✅ 간단함
- **1개 워크플로우 파일**로 모든 기능 제공
- 복잡한 템플릿이나 재사용 컴포넌트 제거
- 직관적인 Job 이름과 구조

### ⚡ 효율성
- 병렬 실행으로 빠른 피드백
- 조건부 실행으로 불필요한 작업 방지
- 캐시 활용으로 빌드 시간 단축

### 🔒 안전성
- 보안 스캔 포함
- 의존성 취약점 검사
- 테스트 실패 시 배포 중단

### 📊 투명성
- 각 단계별 명확한 로그
- 이모지를 활용한 시각적 구분
- 실시간 진행 상황 확인

## 🚀 사용 방법

### 자동 실행
```bash
# main 브랜치에 push (전체 파이프라인 실행)
git push origin main

# develop 브랜치에 push (테스트만 실행)
git push origin develop

# PR 생성 (테스트만 실행)
gh pr create --base main
```

### 수동 실행
GitHub Actions 탭에서 "Run workflow" 버튼 클릭

### CLI 실행
```bash
# GitHub CLI 사용
gh workflow run "🚀 CodePing.AI CI/CD"
```

## 📊 생성되는 문서

### 📚 GitHub Pages 사이트
- **URL**: `https://[username].github.io/[repository]/docs/`
- **구성**:
  - 메인 페이지: 문서 허브
  - API 문서: `shared`, `infrastructure` 모듈
  - 코드 메트릭: 커버리지, 복잡도
  - 변경 로그: 최근 커밋 이력

### 📈 메트릭 정보
- 테스트 커버리지 비율
- 코드 복잡도 분석
- PyPI 패키지 import 성공률

## 🔧 설정 및 커스터마이징

### 환경 변수
```yaml
env:
  PYTHON_VERSION: "3.12"  # Python 버전
```

### 품질 기준 조정
```bash
# 코드 포매팅 (black)
black --check . --line-length=88

# 린팅 (flake8)
flake8 . --max-line-length=88 --extend-ignore=E203,W503

# 보안 스캔 (bandit)
bandit -r . -f json -o bandit-report.json
```

### 테스트 대상 패키지
현재 12개 PyPI 패키지를 자동으로 테스트합니다:
- `universal_data_storage`
- `universal_webhook_receiver`
- `universal_git_data_parser`
- `universal_llm_service`
- `universal_notification_service`
- `universal_notion_sync`
- `universal_schedule_manager`
- `universal_http_api_client`
- `universal_prompt_builder`
- `universal_data_aggregator`
- `universal_data_retriever`
- `universal_diff_analyzer`

## 🐛 트러블슈팅

### 일반적인 문제

**1. 테스트 실패**
```bash
# 로컬에서 테스트 실행
python -m pytest tests/ -v

# 코드 포매팅 확인
black --check .
flake8 .
```

**2. Docker 빌드 실패**
```bash
# 로컬에서 Docker 빌드 테스트
docker build -t codeping-ai:latest .
docker run --rm codeping-ai:latest python -c "import shared.config.settings"
```

**3. 문서 생성 실패**
```bash
# 로컬에서 문서 생성 테스트
pip install pdoc3 radon
pdoc3 --html --output-dir docs-site shared
```

### 로그 확인
GitHub Actions 탭에서 각 Job의 상세 로그를 확인할 수 있습니다.

## 📈 성능 최적화

### 빌드 시간 단축
- pip 캐시 활용
- Docker layer 캐시 활용
- 조건부 실행으로 불필요한 작업 스킵

### 리소스 사용량
- PostgreSQL 서비스는 테스트 Job에서만 실행
- 문서 생성은 변경 감지 후에만 실행
- 배포는 main 브랜치에서만 실행

## 🔮 향후 계획

### 단기 개선사항
- Slack 알림 통합
- 더 상세한 테스트 리포트
- 성능 벤치마크 추가

### 중기 개선사항
- 스테이징 환경 배포
- 자동 롤백 기능
- A/B 테스트 지원

### 장기 개선사항
- 멀티 환경 배포
- 고급 모니터링 통합
- 자동 스케일링

## 📞 지원

문제가 발생하거나 개선 사항이 있으면 GitHub Issues에 등록해주세요.

---

> 💡 **팁**: 이 파이프라인은 간단함과 기능성의 균형을 맞춘 설계입니다. 필요에 따라 추가 기능을 점진적으로 확장할 수 있습니다.