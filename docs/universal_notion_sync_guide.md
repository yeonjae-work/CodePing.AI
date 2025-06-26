# 범용 Notion 동기화 모듈 사용 가이드

이 가이드는 **완전히 독립적으로 설계된 범용 Notion 동기화 모듈**을 다른 프로젝트에서 사용하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [설치 및 설정](#설치-및-설정)
3. [기본 사용법](#기본-사용법)
4. [고급 기능](#고급-기능)
5. [API 레퍼런스](#api-레퍼런스)
6. [실제 사용 예시](#실제-사용-예시)
7. [문제 해결](#문제-해결)

---

## 📖 개요

### 특징

✅ **완전 독립적**: 프로젝트별 의존성 없음, 어떤 프로젝트에서도 재사용 가능  
✅ **범용 설계**: 어떤 Notion 워크스페이스에서도 사용 가능  
✅ **관계 기반 필터링**: 데이터베이스 관계 속성으로 필터링 지원  
✅ **완전한 테이블 처리**: 노션 테이블 → 마크다운 테이블 완벽 변환  
✅ **다양한 출력 형식**: Markdown, JSON, Plain Text  
✅ **CLI 도구**: 완전 독립적인 관리 인터페이스  
✅ **증분 동기화**: 변경된 내용만 효율적으로 동기화  
✅ **계층 구조 발견**: 데이터베이스 간 관계 자동 탐색  

### 지원 기능

- **페이지 동기화**: Notion 페이지를 마크다운으로 변환 (모든 블록 타입 지원)
- **데이터베이스 동기화**: 스키마, 메타데이터, 페이지 내용 모두 추출
- **테이블 블록 처리**: 노션 테이블을 마크다운 테이블로 완벽 변환
- **관계 필터링**: 특정 페이지와 관련된 데이터만 동기화
- **배치 동기화**: 여러 대상을 한 번에 동기화
- **설정 관리**: JSON 기반 설정 파일로 재사용 가능

---

## 🚀 설치 및 설정

### 1. 파일 복사

프로젝트 루트에 다음 파일들을 복사하세요:

```bash
# 핵심 모듈 복사
cp -r modules/notion_sync/ YOUR_PROJECT/modules/notion_sync/
cp manage_notion.py YOUR_PROJECT/

# 파일 구조
YOUR_PROJECT/
├── modules/notion_sync/
│   ├── __init__.py
│   ├── models.py      # 데이터 모델 (완전 독립적)
│   └── service.py     # 동기화 엔진 (범용 설계)
└── manage_notion.py   # CLI 도구 (독립 실행 가능)
```

### 2. 의존성 설치

```bash
pip install click httpx pydantic
```

### 3. Notion API 토큰 설정

#### 방법 1: 환경변수

```bash
export NOTION_TOKEN="secret_your_notion_integration_token"
```

#### 방법 2: .env 파일

```bash
echo "NOTION_TOKEN=secret_your_notion_integration_token" >> .env
```

### 4. Notion API 토큰 발급 방법

1. [Notion 개발자 포털](https://www.notion.so/my-integrations) 접속
2. "New integration" 클릭
3. 통합 이름 입력 및 워크스페이스 선택
4. "Submit" 클릭하여 토큰 발급
5. 동기화할 페이지/데이터베이스에 통합 권한 부여

---

## 🎯 기본 사용법

### CLI 도구 사용

#### 1. 연결 테스트

```bash
python manage_notion.py test-connection
```

#### 2. 페이지 추가 및 동기화

```bash
# 페이지를 동기화 대상에 추가
python manage_notion.py add-page PAGE_ID \
  --name "프로젝트 문서" \
  --output "docs/project.md" \
  --format markdown

# 동기화 실행
python manage_notion.py sync
```

#### 3. 데이터베이스 추가 및 동기화

```bash
# 데이터베이스를 동기화 대상에 추가
python manage_notion.py add-database DATABASE_ID \
  --name "작업 목록" \
  --output "docs/tasks.md" \
  --format markdown

# 관계 필터링과 함께 데이터베이스 추가
python manage_notion.py add-database DATABASE_ID \
  --name "상세설계서" \
  --output "docs/design.md" \
  --filter-by "프로젝트 마스터:21c18a4c52a1804ba78ddbcc2ba649d4"

# 동기화 실행
python manage_notion.py sync
```

#### 4. 계층 구조 자동 발견

```bash
# 데이터베이스 관계 탐색
python manage_notion.py discover-hierarchy DATABASE_ID --max-depth 3

# 발견된 구조를 자동으로 동기화 대상에 추가
python manage_notion.py discover-hierarchy DATABASE_ID --auto-add
```

#### 5. 빠른 동기화 (설정 파일 없이)

```bash
# 단일 페이지 즉시 동기화
python manage_notion.py quick-page PAGE_ID output.md

# 단일 데이터베이스 즉시 동기화
python manage_notion.py quick-database DATABASE_ID database.md
```

### 프로그래밍 방식 사용

#### 1. 빠른 동기화

```python
import asyncio
from modules.notion_sync.service import quick_sync_page, quick_sync_database
from modules.notion_sync.models import ContentFormat

async def main():
    # 페이지 동기화
    success = await quick_sync_page(
        notion_token="your_token",
        page_id="page_id_here",
        output_file="output.md",
        format=ContentFormat.MARKDOWN
    )
    
    # 데이터베이스 동기화
    success = await quick_sync_database(
        notion_token="your_token", 
        database_id="database_id_here",
        output_file="database.md",
        format=ContentFormat.MARKDOWN
    )

asyncio.run(main())
```

#### 2. 고급 설정 사용

```python
import asyncio
from modules.notion_sync.service import UniversalNotionSyncEngine, ConfigurationManager
from modules.notion_sync.models import (
    NotionCredentials, SyncConfiguration, SyncTarget,
    ContentFormat, SyncStrategy
)

async def main():
    # 설정 생성
    credentials = NotionCredentials(token="your_token")
    config = SyncConfiguration(credentials=credentials)
    
    # 동기화 대상 추가 (관계 필터링 포함)
    target = SyncTarget(
        id="database_id_here",
        type="database",
        name="상세설계서",
        output_path="docs/design.md",
        format=ContentFormat.MARKDOWN,
        strategy=SyncStrategy.INCREMENTAL,
        relation_filter={"프로젝트 마스터": "21c18a4c52a1804ba78ddbcc2ba649d4"}
    )
    config.add_target(target)
    
    # 엔진 생성 및 동기화
    engine = UniversalNotionSyncEngine(config)
    result = await engine.sync_target(target)
    
    print(f"동기화 결과: {result.success}")
    
    # 설정 저장 (재사용 가능)
    config_manager = ConfigurationManager("my_sync_config.json")
    config_manager.save_configuration(config)

asyncio.run(main())
```

---

## 🔧 고급 기능

### 1. 관계 기반 필터링

특정 페이지와 관련된 데이터만 동기화할 수 있습니다:

```bash
# CLI에서 관계 필터링
python manage_notion.py add-database DATABASE_ID \
  --name "관련 문서들" \
  --output "docs/related.md" \
  --filter-by "프로젝트:PAGE_ID"
```

```python
# 프로그래밍 방식
target = SyncTarget(
    id="database_id",
    type="database",
    name="필터된 DB",
    output_path="filtered.md",
    relation_filter={
        "프로젝트 마스터": "21c18a4c52a1804ba78ddbcc2ba649d4",
        "담당자": "user_page_id"
    }
)
```

### 2. 사용자 정의 변환 함수

프로젝트별 요구사항에 맞는 변환 로직을 작성할 수 있습니다:

```python
def cursor_rules_transformer(notion_data, target):
    """Cursor Rules 형식으로 변환"""
    markdown = notion_data.to_markdown()
    
    return f"""name: {target.name.lower().replace(' ', '-')}
alwaysApply: true
content: |
{_indent_content(markdown, 2)}
  
  ---
  **🔄 Last Synced**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
  **📝 Source**: [Notion Document]({notion_data.url})
"""

def _indent_content(content, spaces):
    indent = " " * spaces
    return "\n".join(f"{indent}{line}" for line in content.split("\n"))

# 엔진에 등록
engine.register_transformer("cursor_rules", cursor_rules_transformer)

# 사용
target = SyncTarget(
    id="page_id",
    type="page", 
    name="Architecture Rules",
    output_path=".cursor/rules/architecture.mdc",
    custom_transformer="cursor_rules"
)
```

### 3. 배치 동기화

```python
async def batch_sync():
    engine = await create_notion_sync_engine("your_token")
    
    # 여러 대상 추가
    targets = [
        SyncTarget(id="page1", type="page", name="Doc1", output_path="doc1.md"),
        SyncTarget(id="page2", type="page", name="Doc2", output_path="doc2.md"),
        SyncTarget(id="db1", type="database", name="DB1", output_path="db1.md"),
    ]
    
    for target in targets:
        engine.config.add_target(target)
    
    # 배치 동기화 실행
    batch_result = await engine.sync_all_targets()
    
    print(f"성공률: {batch_result.success_rate:.2%}")
    print(f"소요 시간: {batch_result.duration_seconds:.2f}초")
```

### 4. 설정 파일 관리

```python
from modules.notion_sync.service import ConfigurationManager

# 설정 저장
config_manager = ConfigurationManager("my_config.json")
config_manager.save_configuration(config)

# 설정 로드
loaded_config = config_manager.load_configuration()

# CLI에서 특정 설정 파일 사용
python manage_notion.py --config my_config.json sync
```

---

## 📚 API 레퍼런스

### 주요 클래스

#### `UniversalNotionSyncEngine`

핵심 동기화 엔진

```python
class UniversalNotionSyncEngine:
    def __init__(self, config: SyncConfiguration)
    
    async def sync_target(self, target: SyncTarget) -> SyncResult
    async def sync_all_targets(self) -> BatchSyncResult
    async def discover_and_add_hierarchy(self, root_database_id: str) -> List[SyncTarget]
    
    def register_transformer(self, name: str, transformer: Callable)
```

#### `SyncTarget`

동기화 대상 정의

```python
@dataclass
class SyncTarget:
    id: str                         # 페이지/데이터베이스 ID
    type: str                       # "page" 또는 "database"
    name: str                       # 식별용 이름
    output_path: str                # 출력 파일 경로
    format: ContentFormat           # 출력 형식
    strategy: SyncStrategy          # 동기화 전략
    custom_transformer: str         # 사용자 정의 변환 함수명
    relation_filter: Dict[str, str] # 관계 기반 필터링
    last_sync: Optional[datetime]   # 마지막 동기화 시간
```

#### `SyncConfiguration`

전체 동기화 설정

```python
@dataclass 
class SyncConfiguration:
    credentials: NotionCredentials
    targets: List[SyncTarget]
    output_base_path: str
    relation_discovery: RelationDiscoveryMode
    max_hierarchy_depth: int
    batch_size: int
```

### 편의 함수

```python
# 간편한 동기화
async def quick_sync_page(token: str, page_id: str, output_file: str, format: ContentFormat) -> bool
async def quick_sync_database(token: str, database_id: str, output_file: str, format: ContentFormat) -> bool

# 엔진 생성
async def create_notion_sync_engine(token: str, output_path: str, config_file: str) -> UniversalNotionSyncEngine
```

### CLI 명령어

```bash
# 대상 관리
python manage_notion.py add-page PAGE_ID --name "이름" --output "파일.md"
python manage_notion.py add-database DB_ID --name "이름" --output "파일.md" --filter-by "속성:값"
python manage_notion.py list-targets
python manage_notion.py remove TARGET_ID

# 동기화
python manage_notion.py sync [--target TARGET_NAME]
python manage_notion.py quick-page PAGE_ID output.md
python manage_notion.py quick-database DB_ID output.md

# 탐색 및 테스트
python manage_notion.py discover-hierarchy DB_ID [--auto-add]
python manage_notion.py test-connection
```

---

## 💼 실제 사용 예시

### 예시 1: 개발 문서 동기화

```python
# sync_docs.py
import asyncio
from modules.notion_sync.service import create_notion_sync_engine
from modules.notion_sync.models import SyncTarget, ContentFormat

async def sync_development_docs():
    """개발 문서를 자동으로 동기화"""
    engine = await create_notion_sync_engine(
        notion_token="your_token",
        output_base_path="./docs/",
        config_file="dev_docs_config.json"
    )
    
    # 문서 목록 정의
    docs = [
        {
            "id": "architecture_page_id",
            "name": "Architecture", 
            "output": "architecture.md"
        },
        {
            "id": "api_spec_page_id",
            "name": "API Specification",
            "output": "api/spec.md"
        },
        {
            "id": "tasks_db_id",
            "name": "Task Database",
            "output": "tasks.md",
            "type": "database",
            "filter": {"프로젝트": "current_project_id"}
        }
    ]
    
    # 대상 추가
    for doc in docs:
        target = SyncTarget(
            id=doc["id"],
            type=doc.get("type", "page"),
            name=doc["name"],
            output_path=doc["output"],
            format=ContentFormat.MARKDOWN,
            relation_filter=doc.get("filter")
        )
        engine.config.add_target(target)
    
    # 동기화 실행
    result = await engine.sync_all_targets()
    print(f"동기화 완료: {result.successful_syncs}/{result.total_targets}")

if __name__ == "__main__":
    asyncio.run(sync_development_docs())
```

### 예시 2: 프로젝트별 규칙 생성

```python
# generate_rules.py
import asyncio
from datetime import datetime
from modules.notion_sync.service import create_notion_sync_engine
from modules.notion_sync.models import SyncTarget

def project_rules_transformer(notion_data, target):
    """프로젝트 규칙 형식으로 변환"""
    content = notion_data.to_markdown()
    
    return f"""# {target.name}

> **📍 출처**: [Notion 문서]({notion_data.url})  
> **🔄 최종 업데이트**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{content}

---
*이 문서는 Notion에서 자동 동기화됩니다.*
"""

async def generate_project_rules():
    engine = await create_notion_sync_engine("your_token", "./rules/")
    engine.register_transformer("project_rules", project_rules_transformer)
    
    # 프로젝트 문서들
    project_pages = [
        ("coding_standards_id", "코딩 표준", "coding-standards.md"),
        ("architecture_id", "아키텍처 가이드", "architecture.md"),
        ("deployment_id", "배포 가이드", "deployment.md"),
    ]
    
    for page_id, name, output in project_pages:
        target = SyncTarget(
            id=page_id,
            type="page",
            name=name,
            output_path=output,
            custom_transformer="project_rules"
        )
        engine.config.add_target(target)
    
    await engine.sync_all_targets()

asyncio.run(generate_project_rules())
```

### 예시 3: 계층적 문서 구조 동기화

```python
# sync_hierarchy.py
import asyncio
from modules.notion_sync.service import create_notion_sync_engine

async def sync_project_hierarchy():
    """프로젝트 전체 계층 구조 동기화"""
    engine = await create_notion_sync_engine(
        notion_token="your_token", 
        output_base_path="./docs/",
        config_file="hierarchy_config.json"
    )
    
    # 루트 데이터베이스에서 시작하여 전체 구조 발견
    root_database_id = "project_master_db_id"
    discovered = await engine.discover_and_add_hierarchy(root_database_id)
    
    print(f"발견된 문서: {len(discovered)}개")
    for target in discovered:
        print(f"  - {target.name} ({target.type})")
    
    # 전체 동기화
    result = await engine.sync_all_targets()
    print(f"\n동기화 결과: {result.successful_syncs}/{result.total_targets} 성공")

asyncio.run(sync_project_hierarchy())
```

---

## 🛠 문제 해결

### 자주 발생하는 문제

#### 1. "Unauthorized" 오류

```
해결: Notion API 토큰 확인
- 토큰이 올바른지 확인
- 페이지/데이터베이스에 통합 권한이 있는지 확인
```

#### 2. "Object not found" 오류

```
해결: ID 및 권한 확인
- 페이지/데이터베이스 ID가 올바른지 확인
- 해당 객체가 존재하는지 확인
- 통합에 읽기 권한이 있는지 확인
```

#### 3. 테이블이 동기화되지 않음

```
해결: 블록 처리 확인
- 현재 모든 테이블 블록 타입 지원됨 ✅
- 파이프 문자 이스케이프 처리됨 ✅
- 헤더 행과 데이터 행 구분 처리됨 ✅
```

#### 4. 관계 필터가 작동하지 않음

```
해결: 필터 설정 확인
- 속성명이 정확한지 확인
- 대상 페이지 ID가 올바른지 확인
- 관계 속성이 실제로 존재하는지 확인
```

### 디버깅 팁

#### 1. 로깅 활성화

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. 연결 테스트

```bash
python manage_notion.py test-connection
```

#### 3. 단일 페이지 테스트

```bash
python manage_notion.py quick-page PAGE_ID test_output.md
```

#### 4. 설정 확인

```bash
python manage_notion.py list-targets
```

### 성능 최적화

#### 1. 증분 동기화 사용

```python
target.strategy = SyncStrategy.INCREMENTAL  # 변경된 내용만 동기화
```

#### 2. 배치 크기 조정

```python
config.batch_size = 50  # 한 번에 처리할 항목 수
```

#### 3. 관계 발견 깊이 제한

```python
config.max_hierarchy_depth = 3  # 탐색 깊이 제한
```

---

## 📝 지원되는 노션 블록 타입

### 완전 지원 (✅)
- **텍스트**: paragraph, heading_1~3, bulleted_list_item, numbered_list_item
- **서식**: code, quote, callout, toggle, divider
- **테이블**: table, table_row (마크다운 테이블로 완벽 변환)
- **Rich Text**: 볼드, 이탤릭, 코드, 링크

### 특수 처리
- **파이프 문자**: `|` → `\|` 자동 이스케이프
- **테이블 구조**: 헤더와 데이터 행 자동 구분
- **중첩 블록**: 자식 블록 재귀적 처리

---

## 📈 추가 리소스

### 관련 문서

- [Notion API 공식 문서](https://developers.notion.com/)
- [Notion 통합 가이드](https://developers.notion.com/docs/getting-started)

### 예제 프로젝트 구조

```bash
my_project/
├── modules/notion_sync/     # 복사된 동기화 모듈
├── manage_notion.py         # CLI 도구
├── sync_docs.py            # 사용자 정의 동기화 스크립트
├── notion_sync_config.json # 동기화 설정 파일
├── docs/                   # 동기화된 문서 출력
└── .env                    # 환경변수 설정
```

### 설정 파일 예시

```json
{
  "credentials": {
    "token": "secret_your_token",
    "version": "2022-06-28"
  },
  "targets": [
    {
      "id": "page_id",
      "type": "page",
      "name": "프로젝트 문서",
      "output_path": "docs/project.md",
      "format": "markdown",
      "strategy": "incremental"
    },
    {
      "id": "database_id",
      "type": "database", 
      "name": "작업 목록",
      "output_path": "docs/tasks.md",
      "format": "markdown",
      "relation_filter": {
        "프로젝트": "project_page_id"
      }
    }
  ]
}
```

---

**이제 완전히 독립적인 범용 Notion 동기화 모듈을 자유롭게 활용하세요!** 🚀 

**🎯 핵심 특징**: 
- ✅ 테이블 처리 완벽 구현
- ✅ 관계 기반 필터링 지원  
- ✅ 프로젝트 독립적 설계
- ✅ CLI와 프로그래밍 API 모두 제공 