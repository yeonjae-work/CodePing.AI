# DataStorage MVP 버전 사용 가이드

## 📋 개요

DataStorage 모듈 MVP 버전은 설계서를 바탕으로 구현된 간소화된 커밋 데이터 저장 시스템입니다. 복잡한 이벤트 소싱이나 캐싱 없이 핵심 기능만 제공하여 빠른 프로토타입 개발을 지원합니다.

## 🏗️ 아키텍처

```
[GitDataParser] → [DataStorageManager] → [PostgreSQL/SQLite]
                        ↓
                  [StorageResult]
```

### 핵심 컴포넌트

- **DataStorageManager**: 메인 저장 관리자
- **CommitRecord**: 커밋 정보 테이블
- **DiffRecord**: Diff 정보 테이블 (압축 지원)
- **StorageResult**: 저장 결과 응답

## 🚀 빠른 시작

### 1. 기본 사용법

```python
from datetime import datetime, timezone
from modules.data_storage.models import CommitData, DiffData
from modules.data_storage.service import DataStorageManager

# 데이터 준비
commit_data = CommitData(
    commit_hash="abc123def456",
    message="Add new feature",
    author="developer@example.com",
    timestamp=datetime.now(timezone.utc),
    repository="owner/repo",
    branch="main"
)

diff_data = [
    DiffData(
        file_path="src/main.py",
        additions=10,
        deletions=5,
        changes="Added new function",
        diff_content=b"diff --git a/src/main.py..."
    )
]

# 저장
manager = DataStorageManager()
result = manager.store_commit(commit_data, diff_data)

if result.success:
    print(f"✅ 커밋 저장 성공: {result.commit_id}")
    print(f"📊 통계: +{result.metadata['total_additions']}/-{result.metadata['total_deletions']}")
else:
    print(f"❌ 저장 실패: {result.message}")
```

### 2. 커밋 조회

```python
# 해시로 커밋 조회
commit_with_diffs = manager.get_commit_by_hash("abc123def456")

if commit_with_diffs:
    commit = commit_with_diffs.commit
    print(f"커밋: {commit.message}")
    print(f"작성자: {commit.author}")
    print(f"파일 수: {commit.diff_count}")
    
    for diff in commit_with_diffs.diffs:
        print(f"  {diff.file_path}: +{diff.additions}/-{diff.deletions}")

# 최근 커밋 목록
recent_commits = manager.get_recent_commits("owner/repo", limit=10)
for commit in recent_commits:
    print(f"{commit.hash[:8]} - {commit.message}")
```

## 📊 데이터 모델

### CommitData (입력)

```python
class CommitData(BaseModel):
    commit_hash: str          # 커밋 해시 (40자)
    message: str             # 커밋 메시지
    author: str              # 작성자
    author_email: Optional[str] = None
    timestamp: datetime      # 커밋 시간
    repository: str          # 저장소 (owner/repo)
    branch: str             # 브랜치명
    pusher: Optional[str] = None
    commit_count: int = 1    # 커밋 수
```

### DiffData (입력)

```python
class DiffData(BaseModel):
    file_path: str                    # 파일 경로
    additions: int = 0               # 추가된 라인 수
    deletions: int = 0               # 삭제된 라인 수
    changes: Optional[str] = None    # 변경 내용 요약
    diff_content: Optional[bytes] = None  # 실제 diff 내용
```

### StorageResult (출력)

```python
class StorageResult(BaseModel):
    success: bool                    # 성공 여부
    status: StorageStatus           # 상태 (SUCCESS, FAILED, DUPLICATE)
    commit_id: Optional[int] = None # 생성된 커밋 ID
    message: str                    # 결과 메시지
    timestamp: datetime             # 처리 시간
    metadata: Dict[str, Any] = {}   # 추가 정보
```

## 🔧 고급 기능

### 1. 압축 및 S3 오프로딩

```python
# 큰 diff 파일 자동 처리
# - 256KB 이하: DB에 gzip 압축 저장
# - 256KB 초과: S3 업로드 (설정된 경우)

# S3 설정 (환경변수)
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_S3_BUCKET=codeping-diffs
```

### 2. 중복 커밋 처리

```python
# 같은 해시의 커밋 저장 시도
result = manager.store_commit(existing_commit_data, diff_data)

if result.status == StorageStatus.DUPLICATE:
    print("이미 존재하는 커밋입니다.")
```

### 3. 트랜잭션 관리

```python
from shared.config.database import get_session

# 수동 세션 관리
with get_session() as session:
    manager = DataStorageManager(session)
    
    # 여러 커밋을 하나의 트랜잭션으로
    for commit_data, diff_data in commit_batches:
        result = manager.store_commit(commit_data, diff_data)
        if not result.success:
            # 자동 롤백됨
            break
```

## 🧪 테스트

### 단위 테스트 실행

```bash
python -m pytest tests/modules/data_storage/test_mvp_storage.py -v
```

### 테스트 커버리지

```bash
python -m pytest tests/modules/data_storage/test_mvp_storage.py --cov=modules.data_storage
```

## 📈 성능 특성

### MVP 버전 제한사항

- **동기 처리**: 비동기 처리 미지원
- **단일 노드**: 분산 처리 미지원
- **기본 압축**: gzip만 지원
- **제한된 인덱싱**: 기본 인덱스만 제공

### 권장 사용 범위

- **커밋 수**: 일일 1,000건 이하
- **diff 크기**: 파일당 10MB 이하
- **동시 사용자**: 10명 이하

## 🔄 마이그레이션

### 데이터베이스 초기 설정

```bash
python scripts/migrate_database.py
```

### 기존 이벤트 데이터 마이그레이션

```python
from modules.data_storage.service import LegacyDataStorageService

# 기존 코드 호환성 유지
legacy_service = LegacyDataStorageService()
legacy_service.store_event_with_diff(payload, headers, diff_data)
```

## 🐛 문제 해결

### 일반적인 오류

1. **ImportError: cannot import name 'get_session'**
   ```bash
   # 데이터베이스 설정 확인
   python -c "from shared.config.database import get_session; print('OK')"
   ```

2. **SQLAlchemy 테이블 없음**
   ```bash
   python scripts/migrate_database.py
   ```

3. **압축 오류**
   ```python
   # diff_content가 bytes인지 확인
   assert isinstance(diff_data.diff_content, bytes)
   ```

### 로그 레벨 설정

```python
import logging
logging.getLogger('modules.data_storage').setLevel(logging.DEBUG)
```

## 🔮 향후 개선 계획

### Phase 2: 확장 기능

- **이벤트 소싱**: 변경 이력 추적
- **Redis 캐싱**: 성능 향상
- **비동기 처리**: 동시성 개선
- **샤딩**: 확장성 증대

### Phase 3: 엔터프라이즈

- **Kafka 메시징**: 이벤트 스트리밍
- **모니터링**: Prometheus/Grafana
- **백업/복구**: 자동화된 백업
- **API 확장**: RESTful API

## 📞 지원

문제가 발생하거나 개선 제안이 있으시면:

1. **로그 확인**: `logs/data_storage.log`
2. **테스트 실행**: 관련 테스트 케이스 확인
3. **문서 참조**: 설계서와 비교
4. **이슈 제기**: 구체적인 재현 방법 포함 