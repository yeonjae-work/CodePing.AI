# 🚀 CodePing.AI

AI-driven Modular Design 원칙을 따르는 코드 변경 추적 및 알림 시스템입니다.

## 📋 프로젝트 개요

CodePing.AI는 GitHub 웹훅을 통해 코드 변경사항을 실시간으로 추적하고, AI를 활용하여 의미있는 요약을 생성하여 Slack으로 알림을 보내는 시스템입니다.

## 🏗️ 아키텍처

- **모듈화된 설계**: 12개 PyPI 패키지로 분리된 재사용 가능한 모듈
- **간단한 CI/CD**: 단일 워크플로우 파일로 모든 기능 제공
- **자동 문서화**: 코드 변경 시 문서 자동 생성 및 배포

## 🚀 CI/CD 파이프라인

### 통합 워크플로우 (`.github/workflows/main.yml`)
- 🧪 **테스트 및 품질 검사**: 코드 품질, 보안, 테스트
- 🐳 **Docker 빌드**: 컨테이너 이미지 생성 및 테스트
- 📚 **문서 자동화**: API 문서, 메트릭, 변경 로그
- 🚀 **배포**: 프로덕션 환경 배포
- 📱 **알림**: 결과 통지

## 📚 문서

- [CI/CD 파이프라인 가이드](docs/cicd_pipeline_guide.md)
- [문서 자동화 가이드](docs/documentation_automation_guide.md)

## 🔧 모듈 구조

### 📦 PyPI 패키지 (업로드 완료)
모든 모듈이 `yeonjae-` prefix로 PyPI에 업로드되었습니다:

```bash
pip install yeonjae-universal-git-data-parser      # Git 데이터 파싱
pip install yeonjae-universal-http-api-client      # HTTP API 클라이언트  
pip install yeonjae-universal-llm-service          # LLM 서비스 연동
pip install yeonjae-universal-notification-service # 알림 서비스
pip install yeonjae-universal-notion-sync          # Notion 동기화
pip install yeonjae-universal-data-aggregator      # 데이터 집계
pip install yeonjae-universal-data-retriever       # 데이터 조회
pip install yeonjae-universal-data-storage         # 데이터 저장 및 관리
pip install yeonjae-universal-diff-analyzer        # 코드 차이 분석
pip install yeonjae-universal-prompt-builder       # 프롬프트 빌더
pip install yeonjae-universal-schedule-manager     # 스케줄 관리
pip install yeonjae-universal-webhook-receiver     # 웹훅 수신 및 처리
```

### 🏠 로컬 모듈
- `shared/` - 공통 설정, 데이터베이스, 유틸리티
- `infrastructure/` - AWS, GitHub, OpenAI, Slack 클라이언트

> **참고**: 현재 대부분의 모듈이 로컬에서 개발 중이며, 안정화 후 순차적으로 PyPI에 업로드될 예정입니다.

## 🛠️ 개발 환경 설정

```bash
# 저장소 클론
git clone https://github.com/yeonjae-work/CodePing.AI.git
cd CodePing.AI

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt
```

## 🧪 테스트 실행

```bash
# 전체 테스트 실행
python -m pytest tests/ -v

# 커버리지 포함 테스트
python -m pytest tests/ --cov=. --cov-report=term-missing

# 코드 품질 검사
black --check .
flake8 .
```

## 🐳 Docker 실행

```bash
# Docker 이미지 빌드
docker build -t codeping-ai:latest .

# 컨테이너 실행
docker run --rm codeping-ai:latest
```

## 🔧 VS Code 사용자를 위한 팁

VS Code에서 삭제된 워크플로우 파일에 대한 진단 오류가 표시될 수 있습니다. 이는 캐시 문제로, 다음 방법으로 해결할 수 있습니다:

1. **VS Code 재시작**: `Cmd+Shift+P` → "Developer: Reload Window"
2. **작업 공간 새로고침**: `Cmd+Shift+P` → "Developer: Restart Extension Host"
3. **캐시 클리어**: VS Code를 완전히 종료 후 재시작

## 📈 성능 특징

- **간소화된 CI/CD**: 6개 → 1개 워크플로우 파일 (82% 코드 감소)
- **모듈화된 아키텍처**: 높은 재사용성과 유지보수성
- **자동화된 문서**: 코드 변경 시 자동 문서 생성 및 배포

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 연락처

- GitHub: [@yeonjae-work](https://github.com/yeonjae-work)
- 프로젝트 링크: [https://github.com/yeonjae-work/CodePing.AI](https://github.com/yeonjae-work/CodePing.AI) 