 # 🚀 CodePing.AI CI/CD Pipeline 가이드

## 📋 개요

CodePing.AI 프로젝트의 CI/CD 파이프라인은 GitHub Actions를 기반으로 구축되어 있으며, 코드 품질, 보안, 테스트, 배포를 자동화합니다.

## 🏗️ 파이프라인 구조

### 📁 워크플로우 파일들
```
.github/
├── workflows/
│   ├── ci.yml              # 🧪 CI 파이프라인
│   ├── cd.yml              # 🚀 CD 파이프라인
│   ├── release.yml         # 🏷️ 릴리스 관리
│   ├── security.yml        # 🔐 보안 스캔
│   ├── docs.yml            # 📚 문서 자동화
│   └── docs-config.yml     # 📋 문서 설정
├── dependabot.yml          # 🤖 의존성 자동 업데이트
├── pull_request_template.md # 📝 PR 템플릿
└── ISSUE_TEMPLATE/         # 📋 이슈 템플릿
    ├── bug_report.md
    └── feature_request.md
```

## 🧪 CI 파이프라인 (ci.yml)

### 🎯 목적
- 코드 품질 검증
- 보안 취약점 검사
- 자동화된 테스트 실행
- Docker 이미지 빌드 및 테스트

### 🔄 실행 조건
```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  workflow_dispatch:
```

### 📊 Job 구성

#### 1. 🔍 Code Quality & Security
- **Black**: 코드 포맷팅 검사
- **isort**: Import 정렬 검사
- **Flake8**: 린팅 검사
- **Bandit**: 보안 취약점 스캔
- **Safety**: 의존성 보안 검사
- **MyPy**: 타입 검사

#### 2. 🧪 Tests
- **Matrix Strategy**: Python 3.11, 3.12 버전 테스트
- **PostgreSQL Service**: 테스트용 데이터베이스
- **Coverage Report**: 코드 커버리지 측정
- **Integration Tests**: 통합 테스트 실행

#### 3. 🐳 Docker Build & Test
- **Multi-platform Build**: AMD64, ARM64
- **Security Scan**: Docker 이미지 보안 검사
- **Smoke Test**: 기본 동작 확인

#### 4. 🔐 Security Scan
- **Trivy**: 컨테이너 취약점 스캔
- **SARIF Upload**: GitHub Security 탭 연동

#### 5. 📈 Performance Test
- **Memory Usage**: 메모리 사용량 모니터링
- **Load Testing**: 성능 기준선 확인

### 🚀 사용법

#### 자동 실행
```bash
# main 브랜치에 푸시
git push origin main

# PR 생성
gh pr create --title "feat: new feature" --body "Description"
```

#### 수동 실행
GitHub Actions 탭에서 "🚀 CodePing.AI CI Pipeline" 워크플로우 선택 후 "Run workflow" 클릭

## 🚀 CD 파이프라인 (cd.yml)

### 🎯 목적
- 자동화된 배포
- 환경별 배포 관리
- 롤백 준비
- 배포 후 모니터링

### 🔄 실행 조건
```yaml
on:
  workflow_run:
    workflows: ["🚀 CodePing.AI CI Pipeline"]
    types: [completed]
    branches: [main]
  workflow_dispatch:
    inputs:
      environment: [staging, production]
      force_deploy: [true, false]
```

### 📊 Job 구성

#### 1. 🔍 Pre-deployment Check
- 배포 환경 결정
- 버전 생성
- 배포 준비 상태 확인

#### 2. 🐳 Build & Push Docker Image
- 멀티 플랫폼 이미지 빌드
- Container Registry 푸시
- 이미지 보안 스캔

#### 3. 🏗️ Deploy to Staging
- Staging 환경 배포
- Smoke Test 실행
- 헬스체크 확인

#### 4. 🎯 Deploy to Production
- 수동 승인 필요
- Rolling Update
- Production Smoke Test

#### 5. 📊 Post-deployment Monitoring
- 5분간 헬스체크
- 성능 기준선 확인
- 메트릭 수집

### 🚀 사용법

#### 자동 배포 (Staging)
CI 파이프라인 성공 시 자동으로 Staging 환경에 배포

#### 수동 배포 (Production)
```bash
# GitHub Actions에서 수동 실행
# Environment: production 선택
# Force deploy: 필요시 체크
```

## 🏷️ 릴리스 관리 (release.yml)

### 🎯 목적
- 자동 버전 관리
- 체인지로그 생성
- GitHub Release 생성
- 배포 아티팩트 관리

### 🔄 실행 조건
```yaml
on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version_type: [major, minor, patch]
      pre_release: [true, false]
```

### 📊 Job 구성

#### 1. 🏷️ Version Management
- 현재 버전 확인
- 새 버전 계산
- 체인지로그 생성
- Git 태그 생성

#### 2. 📦 Build Release
- PyPI 패키지 빌드
- 배포 아티팩트 생성
- 메타데이터 설정

#### 3. 🐳 Release Docker Image
- 릴리스용 Docker 이미지
- 멀티 플랫폼 빌드
- Latest 태그 업데이트

#### 4. 📄 Create GitHub Release
- GitHub Release 생성
- 아티팩트 첨부
- 릴리스 노트 자동 생성

### 🚀 사용법

#### 자동 릴리스 (태그 기반)
```bash
# 새 태그 생성 및 푸시
git tag v1.2.0
git push origin v1.2.0
```

#### 수동 릴리스
```bash
# GitHub Actions에서 수동 실행
# Version type: patch/minor/major 선택
# Pre-release: 베타 버전인 경우 체크
```

## 🔐 보안 스캔 (security.yml)

### 🎯 목적
- 정기적 보안 스캔
- 취약점 자동 탐지
- 보안 리포트 생성
- 자동 보안 업데이트

### 🔄 실행 조건
```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # 매일 오전 2시 (UTC)
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

### 📊 Job 구성

#### 1. 🔍 Dependency Vulnerability Scan
- **Safety**: Python 패키지 취약점
- **pip-audit**: 의존성 감사
- **SARIF 리포트**: GitHub Security 연동

#### 2. 🛡️ Code Security Scan
- **Bandit**: Python 코드 보안
- **Semgrep**: 정적 분석
- **보안 패턴 탐지**

#### 3. 🐳 Docker Security Scan
- **Trivy**: 컨테이너 취약점
- **Docker Scout**: 이미지 분석
- **베이스 이미지 검사**

#### 4. 🔐 Secrets Scan
- **TruffleHog**: 시크릿 탐지
- **GitLeaks**: Git 히스토리 스캔
- **API 키 노출 검사**

#### 5. 📊 Security Summary
- **통합 리포트**: 모든 스캔 결과 요약
- **권장사항**: 해결 방법 제시
- **우선순위**: 위험도별 분류

#### 6. 🔄 Auto Security Update
- **자동 업데이트**: 취약한 의존성 수정
- **PR 생성**: 보안 패치 제안
- **테스트 실행**: 업데이트 검증

### 🚀 사용법

#### 자동 실행
- 매일 오전 2시 (UTC) 자동 실행
- main 브랜치 푸시 시 실행
- PR 생성 시 실행

#### 수동 실행
GitHub Actions 탭에서 "🔐 Security Scanning" 워크플로우 선택

## 📚 문서 자동화 (docs.yml)

### 🎯 목적
- 코드 변경 기반 문서 자동 생성
- API 문서, 아키텍처 다이어그램 자동 업데이트
- 코드 메트릭 및 품질 리포트 생성
- GitHub Pages 자동 배포

### 🔄 실행 조건
```yaml
on:
  push:
    branches: [ main, develop ]
    paths: ['**/*.py', '**/*.md', 'requirements.txt', 'docs/**']
  pull_request:
    branches: [ main ]
    paths: ['**/*.py', '**/*.md', 'requirements.txt', 'docs/**']
  schedule:
    - cron: '0 3 * * 0'  # 매주 일요일 오전 3시 (UTC)
  workflow_dispatch:
    inputs:
      doc_type: [all, api, architecture, changelog, coverage]
```

### 📊 Job 구성

#### 1. 📊 Code Analysis & Metrics
- **코드 복잡도**: Radon을 통한 순환 복잡도 분석
- **테스트 커버리지**: pytest-cov 기반 커버리지 리포트
- **문서 품질**: Docstring 커버리지 측정
- **메트릭 시각화**: 마크다운 테이블 및 차트 생성

#### 2. 🔧 API Documentation Generation
- **pdoc3**: PyPI 패키지 API 문서 자동 생성
- **Sphinx**: 고급 문서화 기능 (타입 힌트, 크로스 레퍼런스)
- **12개 Universal 패키지**: 모든 PyPI 패키지 문서화
- **메인 애플리케이션**: shared, infrastructure 모듈 문서화

#### 3. 🏗️ Architecture Documentation
- **Mermaid 다이어그램**: 모듈 의존성 및 시스템 아키텍처
- **프로젝트 구조**: 디렉터리 트리 자동 생성
- **의존성 분석**: PyPI 패키지 간 관계 시각화

#### 4. 📝 Changelog Generation
- **Git 기반 변경 로그**: 커밋 메시지 분류 (feat, fix, docs 등)
- **태그 기반 릴리스 노트**: 버전별 변경사항 정리
- **최근 활동 요약**: 7일간 변경사항 하이라이트

#### 5. 📚 Documentation Deployment
- **GitHub Pages**: 통합 문서 사이트 자동 배포
- **문서 허브**: 모든 문서 유형을 한 곳에서 접근
- **아티팩트 관리**: 생성된 문서 파일 저장 및 관리

### 🚀 사용법

#### 자동 실행
```bash
# 코드 변경 시 자동 트리거 (CI 파이프라인 연동)
git push origin main  # Python 파일 변경 시

# 문서 변경 시 자동 실행
git add docs/
git commit -m "docs: update documentation"
git push origin main
```

#### 수동 실행
```bash
# GitHub CLI 사용
gh workflow run docs.yml --ref main -f doc_type=all

# 특정 문서 유형만 생성
gh workflow run docs.yml --ref main -f doc_type=api
gh workflow run docs.yml --ref main -f doc_type=architecture
```

### 📖 생성되는 문서

#### 문서 사이트 구조
```
https://[owner].github.io/[repo]/docs/
├── index.html                 # 📚 메인 문서 허브
├── api/                       # 🔧 API 문서
│   ├── universal_data_storage/
│   ├── universal_webhook_receiver/
│   └── ... (12개 PyPI 패키지)
├── architecture/              # 🏗️ 아키텍처 문서
├── metrics/                   # 📊 코드 메트릭
├── coverage/                  # 📈 테스트 커버리지
├── quality/                   # 📋 문서 품질
└── changelog/                 # 📝 변경 로그
```

#### CI/CD 통합
- **CI 성공 시**: 자동으로 문서 업데이트 트리거
- **변경 감지**: 코드, 문서, 설정 파일 변경 감지
- **실패 허용**: 문서 생성 실패가 CI 전체를 중단시키지 않음

### ⚙️ 설정 커스터마이징

#### 환경 변수 (docs-config.yml)
```yaml
env:
  COVERAGE_THRESHOLD: 70      # 최소 테스트 커버리지
  COMPLEXITY_THRESHOLD: 10    # 최대 순환 복잡도
  DOCSTRING_THRESHOLD: 80     # 최소 docstring 커버리지
  ARCHITECTURE_DEPTH: 3       # 디렉터리 트리 깊이
```

#### PyPI 패키지 추가
새로운 universal 패키지 추가 시 `docs.yml`의 모듈 목록 업데이트:
```bash
modules=(
  "universal_data_storage"
  "universal_webhook_receiver"
  # ... 기존 모듈들
  "universal_new_module"  # 새 모듈 추가
)
```

## 🤖 Dependabot 설정

### 🎯 목적
- 의존성 자동 업데이트
- 보안 패치 자동 적용
- 정기적 업데이트 관리

### 📊 구성

#### Python 의존성
- **스케줄**: 매주 월요일 오전 9시 (KST)
- **PR 제한**: 최대 10개
- **자동 라벨**: `dependencies`, `python`

#### GitHub Actions
- **스케줄**: 매주 화요일 오전 9시 (KST)
- **PR 제한**: 최대 5개
- **자동 라벨**: `dependencies`, `github-actions`

#### Docker
- **스케줄**: 매주 수요일 오전 9시 (KST)
- **PR 제한**: 최대 3개
- **자동 라벨**: `dependencies`, `docker`

## 📝 템플릿 활용

### 🔄 Pull Request Template
- **체크리스트**: 코드 품질, 테스트, 보안
- **상세 정보**: 변경사항, 테스트 방법
- **리뷰 가이드**: 검토 포인트 명시

### 🐛 Bug Report Template
- **재현 단계**: 상세한 버그 재현 방법
- **환경 정보**: 시스템, 패키지 버전
- **영향도**: Critical, High, Medium, Low

### ✨ Feature Request Template
- **문제 정의**: 해결하고자 하는 문제
- **제안 해결책**: 구체적인 기능 명세
- **기술적 고려사항**: 구현 복잡도, 의존성

## 🔧 설정 및 환경변수

### 필수 GitHub Secrets
```bash
# Container Registry
GITHUB_TOKEN                 # GitHub 토큰 (자동 제공)

# 외부 서비스 (선택사항)
SLACK_WEBHOOK_URL            # Slack 알림
SENTRY_DSN                   # 에러 모니터링
GITLEAKS_LICENSE             # GitLeaks 라이선스
```

### 환경 변수 템플릿
프로젝트 루트에 `.env.template` 파일 참조

## 📊 모니터링 및 알림

### GitHub Actions 모니터링
- **워크플로우 상태**: Actions 탭에서 실시간 확인
- **실패 알림**: 이메일 자동 발송
- **아티팩트**: 빌드 결과물 다운로드 가능

### 보안 모니터링
- **Security 탭**: 취약점 요약 확인
- **Dependabot 알림**: 의존성 업데이트 알림
- **SARIF 리포트**: 상세 보안 분석

### 성능 모니터링
- **테스트 커버리지**: Codecov 연동
- **빌드 시간**: Actions 실행 시간 추적
- **아티팩트 크기**: Docker 이미지 크기 모니터링

## 🚨 트러블슈팅

### 일반적인 문제들

#### 1. CI 파이프라인 실패
```bash
# 로컬에서 테스트 실행
python -m pytest tests/ -v
python examples/simple_integration_test.py

# 코드 품질 검사
black --check .
flake8 .
bandit -r .
```

#### 2. Docker 빌드 실패
```bash
# 로컬에서 Docker 빌드 테스트
docker build -t codeping-ai:test .
docker run --rm codeping-ai:test python -c "print('Hello World')"
```

#### 3. 보안 스캔 실패
```bash
# 로컬에서 보안 스캔
safety check
bandit -r .
```

#### 4. 의존성 문제
```bash
# 의존성 재설치
pip install -r requirements.txt --force-reinstall

# 캐시 클리어
pip cache purge
```

### 🔧 디버깅 팁

#### GitHub Actions 디버깅
```yaml
# 워크플로우에 디버그 스텝 추가
- name: Debug Environment
  run: |
    echo "Python version: $(python --version)"
    echo "Pip version: $(pip --version)"
    echo "Current directory: $(pwd)"
    echo "Environment variables:"
    env | sort
```

#### 로컬 테스트
```bash
# act 도구로 로컬에서 GitHub Actions 실행
brew install act
act -j test  # test job만 실행
```

## 📈 성능 최적화

### 빌드 시간 단축
- **캐시 활용**: 의존성, Docker 레이어 캐시
- **병렬 실행**: 매트릭스 전략 활용
- **조건부 실행**: 변경된 파일만 테스트

### 리소스 최적화
- **워커 수 제한**: 동시 실행 job 수 관리
- **타임아웃 설정**: 무한 대기 방지
- **아티팩트 정리**: 자동 삭제 정책

## 🔮 향후 개선 계획

### 단기 계획 (1-2개월)
- [ ] E2E 테스트 추가
- [ ] 성능 벤치마크 자동화
- [ ] 모바일 앱 CI/CD (해당시)

### 중기 계획 (3-6개월)
- [ ] Kubernetes 배포 지원
- [ ] Blue-Green 배포 구현
- [ ] 자동 롤백 시스템

### 장기 계획 (6개월+)
- [ ] Multi-cloud 배포
- [ ] GitOps 워크플로우
- [ ] AI 기반 코드 리뷰

## 📞 지원 및 문의

### 📋 이슈 리포팅
- **버그**: [Bug Report 템플릿](../.github/ISSUE_TEMPLATE/bug_report.md) 사용
- **기능 요청**: [Feature Request 템플릿](../.github/ISSUE_TEMPLATE/feature_request.md) 사용

### 📞 연락처
- **GitHub**: @yeonjae-work
- **이메일**: team@codeping.ai
- **Discussions**: GitHub Discussions 활용

### 📚 추가 자료
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker 베스트 프랙티스](https://docs.docker.com/develop/dev-best-practices/)
- [Python 패키징 가이드](https://packaging.python.org/)

---

**📝 마지막 업데이트**: 2024년 12월
**🔄 다음 리뷰**: 2025년 3월