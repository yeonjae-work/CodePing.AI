---
name: 🐛 Bug Report
about: 버그를 발견하셨나요? 문제 해결을 위해 상세한 정보를 제공해주세요.
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ['yeonjae-work']
---

# 🐛 Bug Report

## 📋 버그 요약
<!-- 발견한 버그에 대한 간단하고 명확한 설명을 작성해주세요 -->

## 🔄 재현 단계
<!-- 버그를 재현할 수 있는 단계별 과정을 작성해주세요 -->
1. 
2. 
3. 
4. 

## 🎯 예상 동작
<!-- 정상적으로 작동했다면 어떤 결과가 나와야 하는지 설명해주세요 -->

## 💥 실제 동작
<!-- 실제로 어떤 문제가 발생했는지 설명해주세요 -->

## 📸 스크린샷/로그
<!-- 가능하다면 스크린샷이나 에러 로그를 첨부해주세요 -->
```에러 로그나 스크린샷을 여기에 붙여넣어주세요
```

## 🖥️ 환경 정보

### 💻 시스템 환경
- **OS**: [예: macOS 14.5.0, Ubuntu 22.04, Windows 11]
- **Python 버전**: [예: 3.12.0]
- **CodePing.AI 버전**: [예: v1.0.0]

### 📦 패키지 버전
<!-- 관련된 PyPI 패키지들의 버전을 확인해주세요 -->
```bash
pip list | grep universal
```
```
패키지 목록을 여기에 붙여넣어주세요
```

### 🐳 Docker 환경 (해당하는 경우)
- **Docker 버전**: [예: 24.0.0]
- **Docker Compose 버전**: [예: 2.20.0]
- **컨테이너 이미지**: [예: ghcr.io/yeonjae-work/codeping.ai:latest]

## 📁 관련 파일/모듈
<!-- 버그가 발생한 것으로 추정되는 파일이나 모듈을 선택해주세요 -->
- [ ] 🔗 Webhook Receiver
- [ ] 📊 Data Storage
- [ ] 🔍 Git Data Parser
- [ ] 🤖 LLM Service
- [ ] 📱 Notification Service
- [ ] 📝 Notion Sync
- [ ] ⏰ Schedule Manager
- [ ] 🌐 HTTP API Client
- [ ] 🧠 Prompt Builder
- [ ] 📈 Data Aggregator
- [ ] 📥 Data Retriever
- [ ] 🔧 Diff Analyzer
- [ ] 🐳 Docker 설정
- [ ] ⚙️ CI/CD 파이프라인
- [ ] 📚 문서
- [ ] 🔧 기타

## 🔍 추가 컨텍스트

### 🕐 발생 빈도
- [ ] 항상 발생
- [ ] 가끔 발생 (재현율: ___%)
- [ ] 한 번만 발생
- [ ] 특정 조건에서만 발생

### 🎯 영향도
- [ ] 🔴 Critical - 서비스 전체 중단
- [ ] 🟠 High - 주요 기능 사용 불가
- [ ] 🟡 Medium - 일부 기능에 문제
- [ ] 🟢 Low - 사소한 불편함

### 🔧 시도한 해결 방법
<!-- 문제 해결을 위해 시도해본 방법들을 나열해주세요 -->
- [ ] 서비스 재시작
- [ ] 캐시 클리어
- [ ] 의존성 재설치
- [ ] 설정 파일 확인
- [ ] 로그 확인
- [ ] 기타: 

## 🔗 관련 이슈/PR
<!-- 관련된 이슈나 PR이 있다면 링크를 포함해주세요 -->
- Related to #이슈번호
- Duplicate of #이슈번호

## 📝 추가 정보
<!-- 위에서 다루지 않은 추가적인 정보나 컨텍스트가 있다면 작성해주세요 -->

---

### 🏷️ 라벨 가이드
**자동으로 추가되는 라벨:**
- `bug`: 버그 리포트
- `needs-triage`: 우선순위 검토 필요

**추가로 적용 가능한 라벨:**
- `critical`: 긴급 수정 필요
- `security`: 보안 관련 버그
- `performance`: 성능 관련 문제
- `documentation`: 문서 관련 버그
- `dependencies`: 의존성 관련 문제

### 📞 긴급 연락처
**Critical 버그의 경우:**
- GitHub: @yeonjae-work
- 이메일: team@codeping.ai

**참고사항:**
- 보안 관련 버그는 공개 이슈 대신 이메일로 직접 연락해주세요
- 가능한 한 상세한 정보를 제공해주시면 빠른 해결에 도움이 됩니다 