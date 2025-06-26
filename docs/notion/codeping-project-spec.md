# CodePing.AI 프로젝트 기획서 - 보완된 버전

---
**Page ID**: 21c18a4c-52a1-804b-a78d-dbcc2ba649d4
**Created**: 2025-06-24T09:37:00+00:00
**Last Edited**: 2025-06-26T11:51:00+00:00
**URL**: https://www.notion.so/CodePing-AI-21c18a4c52a1804ba78ddbcc2ba649d4
---

# 💡 자연어 요구사항
GitHub(추후확장가능)에서 푸시할때, **코드베이스의 diff 정보를 기준으로** 변경/반영사항을 LLM이 요약하여 슬랙으로 알림전송.
요약내용은 개발자별로 하루동안 개발한 내용에 대한 요약임. 개발자감시역할(너 어제 얼마나, 뭐 코딩했어?)
---
## 🎯 프로젝트 목적
### 핵심 목표
- GitHub 저장소의 **코드 변경사항(diff)**을 실시간으로 모니터링하여 개발자 생산성을 향상시키고 팀의 협업 효율성을 높이는 자동화 도구
- 개발자들의 **일일 코드 작업 내용을 체계적으로 추적**하여 프로젝트 관리와 코드 품질 관리를 지원
- **diff 기반 코드 분석**을 통해 의미있는 개발 활동 인사이트 제공
### 대상 사용자
- 소프트웨어 개발팀, 프로젝트 매니저, 테크 리드가 개발 진행상황을 실시간으로 파악하고자 할 때 사용
- GitHub 변경사항을 **코드 diff 분석**을 통해 LLM이 분석하여 Slack으로 자동 알림 전송하는 개발자 활동 모니터링 시스템
---
## 📝 핵심 요구사항 (diff 정보 중심)
### ✅ 필수 기능
- **GitHub Push 이벤트 실시간 감지 및 diff 정보 추출**
- **코드 변경사항(diff)을 LLM으로 분석하여 의미있는 요약 생성**
- **개발자별 일일 작업 내용 자동 요약 및 Slack 알림 전송**
- **다양한 Git 플랫폼(GitLab, Bitbucket) 확장 가능한 구조**
- **다양한 알림 채널(Email, Discord) 확장 가능한 구조**
### 🔍 diff 분석 상세 요구사항
- **파일별 diff 정보 파싱**: 추가/수정/삭제된 라인 정확한 카운팅
- **코드 의미론적 분석**: 단순 라인 수가 아닌 기능적 변경사항 이해
- **언어별 차별화 분석**: Python, JavaScript, Java 등 언어 특성 고려
- **바이너리 파일 변경 감지**: 이미지, 문서 등 코드 외 파일 변경도 추적
- **커밋 메시지와 diff 상관관계 분석**: 커밋 의도와 실제 변경사항 일치도 검증
---
## ⚙️ 기술 설계 (diff 처리 중심)
### 핵심 기술 스택
- **Python 3.11+, FastAPI, GitHub Webhooks, OpenAI GPT-4, Slack API, Docker**
- **추가: python-diff-parser, GitPython, tree-sitter (코드 파싱)**
### 하이브리드 아키텍처 (diff 정보 포함)
```plain text
Push 이벤트 수신 → diff 정보 추출 → 코드 분석 →
데이터 저장 → 오전 8시 스케줄링 →
diff 기반 데이터 조회 → LLM 코드 분석 → Slack 전송

```
### 예상 구현 시간
- **2-3일 (바이브코딩)**: diff 파싱 추가로 약간 증가
- **1-2주 (일반 개발)**: diff 분석 복잡도로 인한 증가
---
## 🧩 모듈 구성 및 설계 요약 (diff 정보 추가)
재사용성을 극대화한 11개 모듈 구성으로 재설계되었습니다. 각 모듈은 단일 책임 원칙을 따르며, 인터페이스를 통해 느슨하게 결합되어 있어 유지보수성과 확장성이 뛰어납니다.
| 모듈명 | 주요 기능 설명 | 입력 | 출력 | 재사용성(⭐) |
| --- | --- | --- | --- | --- |
| **WebhookReceiver** | webhook 수신 및 검증 | HTTP Request | Validated Event Data | ⭐⭐⭐⭐⭐ |
| **HTTPAPIClient** | 범용 API 호출 서비스 | API Config + Params | API Response | ⭐⭐⭐⭐⭐ |
| **GitDataParser** | Git 데이터 파싱 및 구조화 | Raw Git Data | Structured Data | ⭐⭐⭐⭐ |
| **DiffAnalyzer** | 코드 변경사항 분석 | Diff Data | Analyzed Changes | ⭐⭐⭐⭐⭐ |
| **DataStorage** | 다양한 저장소 지원 | Any Data | Storage Status | ⭐⭐⭐⭐⭐ |
| **ScheduleManager** | 스케줄링 작업 관리 | Schedule Config | Trigger Events | ⭐⭐⭐⭐⭐ |
| **DataRetriever** | 데이터 조회 및 필터링 | Query Parameters | Filtered Data | ⭐⭐⭐⭐⭐ |
| **DataAggregator** | 데이터 가공 및 집계 | Raw Data | Aggregated Report | ⭐⭐⭐⭐⭐ |
| **PromptBuilder** | LLM 프롬프트 동적 생성 | Template + Data | Formatted Prompt | ⭐⭐⭐⭐⭐ |
| **LLMService** | 다양한 LLM 통합 관리 | Prompt + Config | LLM Response | ⭐⭐⭐⭐⭐ |
| **NotificationService** | 범용 알림 전송 | Message + Channel | Send Status | ⭐⭐⭐⭐⭐ |
**🔍 실제 모듈 구성 근거 설명**
| **모듈** | **모듈 분리한 이유** | **재사용 시나리오** |
| --- | --- | --- |
| **WebhookReceiver** | HTTP 수신 로직을 다른 비즈니스 로직과 분리 | GitLab, Bitbucket, Jenkins 등 다양한 webhook 수신 |
| **HTTPAPIClient** | API 호출 로직을 재사용 가능한 형태로 추상화 | GitHub, GitLab, Slack, Discord API 등 모든 HTTP API |
| **GitDataParser** | Git 플랫폼별 데이터 형식 차이 효율적 처리 | GitHub, GitLab, Bitbucket 등 각 플랫폼용 파서 |
| **DiffAnalyzer** | 코드 분석 로직을 다양한 용도로 활용 | 코드 리뷰, 품질 분석, 복잡도 측정, 보안 스캔 |
| **DataStorage** | 저장소 종류와 비즈니스 로직 분리 | PostgreSQL, MongoDB, Redis, S3 등 다양한 저장소 |
| **ScheduleManager** | 스케줄링 로직을 비즈니스와 독립적으로 관리 | 일일, 주간, 월간 리포트, 정기 비리어링 작업 |
| **DataRetriever** | 데이터 조회 로직을 저장소와 독립적으로 추상화 | 다양한 조건의 데이터 조회, 필터링, 정렬 |
| **DataAggregator** | 집계 로직을 다양한 리포트에 재사용 | 개발자 생산성, 팀 성과, 프로젝트 진도 등 다양한 메트릭 |
| **PromptBuilder** | LLM 프롬프트 생성을 다양한 용도로 활용 | 코드 리뷰, 요약, 번역, 문서화 등 다양한 LLM 작업 |
| **LLMService** | LLM 제공업체 변경 시 영향도 최소화 | OpenAI, Anthropic, 로컬 LLM 등 다양한 LLM 서비스 |
| **NotificationService** | 알림 채널 증가 시 추가 개발 최소화 | Slack, Discord, Email, SMS, Webhook 등 모든 알림 |
---
## 🛠️ 상세 기술 스택 (diff 처리 추가)
### 기존 기술 스택
- Python 3.11+ - 메인 개발 언어 및 런타임
- FastAPI - Webhook 수신 서버 및 API 엔드포인트
- GitHub Webhooks API - Git 이벤트 실시간 수신
- OpenAI Python SDK - **GPT-4 API 코드 diff 분석** 및 요약 생성
- slack-sdk - Slack API 메시지 전송 및 알림
- APScheduler - Python 기반 스케줄링 및 매일 오전 8시 작업
- SQLAlchemy + PostgreSQL - 데이터베이스 ORM 및 **커밋+diff 데이터** 저장
- Pydantic - 데이터 검증 및 직렬화
- Docker + Docker Compose - 컨테이너화 및 배포
- pytest - 단위 테스트 및 통합 테스트
### 추가 기술 스택 (diff 처리용)
- **GitPython** - Git 저장소 조작 및 diff 정보 추출
- **python-diff-parser** - diff 형식 파싱 및 분석
- **tree-sitter** - 프로그래밍 언어별 코드 구문 분석
- **pygments** - 코드 하이라이팅 및 언어 감지
- **radon** - 코드 복잡도 분석 (추가/삭제된 코드의 복잡도 측정)
---
## 📊 실현 가능성 검토 (diff 분석 포함)
### ✅ 강점
- **기술적 실현 가능성**: 모든 사용 기술이 안정적이고 널리 사용되는 기술이므로 구현 리스크 낮음
- **비용 효율성**: OpenAI API 비용이 주요 변동 비용이나, **diff 기반 분석으로 더 정확한 토큰 사용량 예측 가능**
- **확장성**: 모듈화 설계로 GitLab, Bitbucket 등 추가 플랫폼 연동이 매우 용이함
- **유지보수성**: Python + Pydantic 사용과 모듈화 설계로 코드 품질과 유지보수성이 높음
- **성능**: Webhook 기반 이벤트 처리로 실시간 반응성 우수하고, 비동기 처리로 대량 이벤트 처리 가능
### ⚠️ 주의사항 (diff 처리 관련)
- **diff 파싱 복잡도**: 다양한 diff 형식과 대용량 diff 처리 시 성능 최적화 필요
- **언어별 차별화**: 프로그래밍 언어별 특성을 고려한 분석 로직 개발 필요
- **LLM 토큰 제한**: 대용량 diff 정보 처리 시 토큰 제한 고려한 청킹 전략 필요
---
## 🔄 수정된 데이터 흐름 (diff 중심)
```plain text
GitHub/GitLab Push Event
    ↓
[WebhookReceiver] → webhook 수신 및 검증
    ↓
[HTTPAPIClient] → 필요시 추가 API 호출 (diff 상세정보)
    ↓
[GitDataParser] → Git 데이터 파싱 및 구조화
    ↓
[DiffAnalyzer] → 코드 변경사항 분석 및 의미 추출
    ↓
[DataStorage] → 분석된 데이터 저장
    ↓
[ScheduleManager] → 매일 8시 트리거
    ↓
[DataRetriever] → 어제 데이터 조회
    ↓
[DataAggregator] → 개발자별 활동 집계 및 통계
    ↓
[PromptBuilder] → LLM용 프롬프트 동적 생성
    ↓
[LLMService] → 코드 분석 및 요약 생성
    ↓
[NotificationService] → Slack 등 다양한 채널로 알림 전송

```
---
## 🎯 diff 기반 분석 예시
### 개발자별 일일 리포트 예시
```plain text
🔍 김개발님의 2025-06-25 개발 활동

📊 전체 통계:
- 커밋 수: 5개
- 변경 파일: 8개
- 추가된 라인: 127줄
- 삭제된 라인: 43줄

🚀 주요 작업 내용:
1. 사용자 인증 기능 구현 (auth.py, models.py)
   - JWT 토큰 기반 인증 로직 추가 (+89줄)
   - User 모델 확장 (+15줄)

2. API 에러 처리 개선 (api/errors.py)
   - 커스텀 예외 클래스 추가 (+23줄)
   - 기존 에러 핸들링 리팩토링 (-31줄)

3. 테스트 코드 보강 (tests/)
   - 인증 관련 테스트 케이스 추가 (+38줄)

📈 코드 품질:
- 순환 복잡도: 평균 2.3 (양호)
- 테스트 커버리지 증가: +5.2%
- 중복 코드 감소: -12줄

⏰ 작업 패턴:
- 첫 커밋: 09:30
- 마지막 커밋: 17:45
- 평균 커밋 간격: 2시간 15분

```
이 보완된 기획서는 **diff 정보를 중심으로 한 코드 변경사항 분석**에 초점을 맞추어 실제 요구사항을 충족할 수 있도록 설계되었습니다.