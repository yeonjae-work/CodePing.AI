"""
범용 Notion 동기화 모듈 - 데이터 모델

이 모듈은 완전히 독립적으로 설계되어 다른 프로젝트에서도 재사용 가능합니다.
프로젝트별 의존성 없이 Notion API와의 동기화를 담당합니다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json


class SyncStrategy(Enum):
    """동기화 전략 정의"""
    FULL_SYNC = "full_sync"              # 전체 동기화
    INCREMENTAL = "incremental"          # 증분 동기화 (last_edited_time 기준)
    MANUAL = "manual"                    # 수동 동기화


class ContentFormat(Enum):
    """출력 형식 정의"""
    MARKDOWN = "markdown"
    JSON = "json"
    PLAIN_TEXT = "plain_text"
    CUSTOM = "custom"


class RelationDiscoveryMode(Enum):
    """관계 발견 모드"""
    DISABLED = "disabled"               # 관계 발견 비활성화
    SHALLOW = "shallow"                 # 1단계 관계만 발견
    DEEP = "deep"                      # 다단계 관계 발견
    CUSTOM = "custom"                  # 사용자 정의 관계 규칙


@dataclass
class NotionCredentials:
    """Notion API 인증 정보"""
    token: str
    version: str = "2022-06-28"


@dataclass
class NotionBlock:
    """Notion 블록 데이터"""
    id: str
    type: str
    content: Dict[str, Any]
    children: List['NotionBlock'] = field(default_factory=list)
    has_children: bool = False
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    
    def to_markdown(self) -> str:
        """블록을 마크다운으로 변환"""
        if self.type == "paragraph":
            return self._rich_text_to_markdown(self.content.get("rich_text", []))
        elif self.type == "heading_1":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"# {text}"
        elif self.type == "heading_2":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"## {text}"
        elif self.type == "heading_3":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"### {text}"
        elif self.type == "bulleted_list_item":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"- {text}"
        elif self.type == "numbered_list_item":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"1. {text}"
        elif self.type == "code":
            language = self.content.get("language", "")
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"```{language}\n{text}\n```"
        elif self.type == "quote":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"> {text}"
        elif self.type == "table":
            return self._table_to_markdown()
        elif self.type == "table_row":
            return self._table_row_to_markdown()
        elif self.type == "divider":
            return "---"
        elif self.type == "callout":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            icon = self.content.get("icon", {})
            emoji = icon.get("emoji", "💡") if icon.get("type") == "emoji" else "💡"
            return f"{emoji} **{text}**"
        elif self.type == "toggle":
            text = self._rich_text_to_markdown(self.content.get("rich_text", []))
            return f"<details><summary>{text}</summary>\n\n</details>"
        else:
            # 기타 블록 타입은 텍스트로 처리
            if "rich_text" in self.content:
                return self._rich_text_to_markdown(self.content["rich_text"])
            return ""
    
    def _rich_text_to_markdown(self, rich_text: List[Dict]) -> str:
        """Notion rich text를 마크다운으로 변환"""
        result = ""
        for text_obj in rich_text:
            if text_obj.get("type") == "text":
                content = text_obj.get("text", {}).get("content", "")
                annotations = text_obj.get("annotations", {})
                
                if annotations.get("bold"):
                    content = f"**{content}**"
                if annotations.get("italic"):
                    content = f"*{content}*"
                if annotations.get("code"):
                    content = f"`{content}`"
                
                link = text_obj.get("text", {}).get("link")
                if link:
                    content = f"[{content}]({link.get('url', '')})"
                
                result += content
        return result
    
    def _table_to_markdown(self) -> str:
        """테이블 블록을 마크다운으로 변환"""
        if not self.children:
            return ""
        
        # 첫 번째 행을 헤더로 처리
        header_row = self.children[0] if self.children else None
        if not header_row or header_row.type != "table_row":
            return ""
        
        # 헤더 생성
        header_cells = self._extract_table_row_cells(header_row)
        if not header_cells:
            return ""
        
        table_lines = []
        
        # 헤더 라인
        table_lines.append("| " + " | ".join(header_cells) + " |")
        
        # 구분자 라인
        separator = "| " + " | ".join(["---"] * len(header_cells)) + " |"
        table_lines.append(separator)
        
        # 데이터 행들
        for row in self.children[1:]:
            if row.type == "table_row":
                row_cells = self._extract_table_row_cells(row)
                # 헤더와 셀 개수 맞추기
                while len(row_cells) < len(header_cells):
                    row_cells.append("")
                row_cells = row_cells[:len(header_cells)]  # 초과 셀 제거
                table_lines.append("| " + " | ".join(row_cells) + " |")
        
        return "\n".join(table_lines)
    
    def _table_row_to_markdown(self) -> str:
        """테이블 행을 마크다운으로 변환 (단독 사용시)"""
        cells = self._extract_table_row_cells(self)
        return "| " + " | ".join(cells) + " |"
    
    def _extract_table_row_cells(self, row_block: 'NotionBlock') -> List[str]:
        """테이블 행에서 셀 내용 추출"""
        cells = []
        table_row_content = row_block.content.get("cells", [])  # table_row는 이미 content에 포함됨
        
        for cell_data in table_row_content:
            # 각 셀은 rich_text 배열
            cell_text = self._rich_text_to_markdown(cell_data)
            # 마크다운 테이블에서 파이프 문자 이스케이프
            cell_text = cell_text.replace("|", "\\|")
            cells.append(cell_text)
        
        return cells


@dataclass
class NotionPage:
    """Notion 페이지 데이터"""
    id: str
    title: str
    url: str
    created_time: datetime
    last_edited_time: datetime
    properties: Dict[str, Any] = field(default_factory=dict)
    blocks: List[NotionBlock] = field(default_factory=list)
    parent_id: Optional[str] = None
    parent_type: Optional[str] = None  # "database_id", "page_id", etc.
    archived: bool = False
    
    def to_markdown(self) -> str:
        """페이지를 마크다운으로 변환"""
        content = [f"# {self.title}\n"]
        
        # 메타데이터 추가
        content.append("---")
        content.append(f"**Page ID**: {self.id}")
        content.append(f"**Created**: {self.created_time.isoformat()}")
        content.append(f"**Last Edited**: {self.last_edited_time.isoformat()}")
        content.append(f"**URL**: {self.url}")
        content.append("---\n")
        
        # 블록 내용 추가
        for block in self.blocks:
            markdown_content = block.to_markdown()
            if markdown_content.strip():
                content.append(markdown_content)
        
        return "\n".join(content)


@dataclass
class NotionDatabase:
    """Notion 데이터베이스 정보"""
    id: str
    title: str
    url: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_time: Optional[datetime] = None
    last_edited_time: Optional[datetime] = None
    parent_id: Optional[str] = None
    description: str = ""
    pages: List[NotionPage] = field(default_factory=list)  # 데이터베이스 내 페이지들
    
    def to_markdown(self) -> str:
        """데이터베이스를 마크다운으로 변환"""
        content = [f"# {self.title}\n"]
        
        # 메타데이터 추가
        content.append("---")
        content.append(f"**Database ID**: {self.id}")
        if self.created_time:
            content.append(f"**Created**: {self.created_time.isoformat()}")
        if self.last_edited_time:
            content.append(f"**Last Edited**: {self.last_edited_time.isoformat()}")
        content.append(f"**URL**: {self.url}")
        content.append("---\n")
        
        # 설명 추가
        if self.description:
            content.append(f"## 설명\n{self.description}\n")
        
        # 속성 정보 추가
        if self.properties:
            content.append("## 데이터베이스 스키마\n")
            for prop_name, prop_data in self.properties.items():
                prop_type = prop_data.get("type", "unknown")
                content.append(f"- **{prop_name}**: {prop_type}")
                
                # 관계 속성인 경우 추가 정보
                if prop_type == "relation":
                    relation_info = prop_data.get("relation", {})
                    target_db = relation_info.get("database_id", "")
                    if target_db:
                        content.append(f"  - 연결 대상: `{target_db}`")
                
                # 선택 속성인 경우 옵션 정보
                elif prop_type == "select":
                    options = prop_data.get("select", {}).get("options", [])
                    if options:
                        option_names = [opt.get("name", "") for opt in options]
                        content.append(f"  - 옵션: {', '.join(option_names)}")
        
        # 데이터베이스 내 페이지들 추가
        if self.pages:
            content.append(f"\n## 데이터베이스 내용 ({len(self.pages)}개 항목)\n")
            
            for i, page in enumerate(self.pages, 1):
                content.append(f"### {i}. {page.title}")
                
                # 페이지 속성 정보 표시
                if page.properties:
                    for prop_name, prop_value in page.properties.items():
                        if prop_name in self.properties:
                            prop_type = self.properties[prop_name].get("type", "unknown")
                            formatted_value = self._format_property_value(prop_value, prop_type)
                            if formatted_value:
                                content.append(f"- **{prop_name}**: {formatted_value}")
                
                # 페이지 URL 추가
                content.append(f"- **링크**: [{page.title}]({page.url})")
                
                # 페이지 본문 내용 추가
                if page.blocks:
                    content.append("\n**📄 페이지 내용:**")
                    for block in page.blocks:
                        block_content = block.to_markdown()
                        if block_content.strip():
                            # 들여쓰기를 추가하여 구분
                            indented_content = "\n".join(f"  {line}" if line else "" for line in block_content.split("\n"))
                            content.append(indented_content)
                
                content.append("")  # 빈 줄 추가
        
        return "\n".join(content)
    
    def _format_property_value(self, prop_value: Dict[str, Any], prop_type: str) -> str:
        """속성 값을 사람이 읽기 쉬운 형태로 포맷"""
        try:
            if prop_type == "title":
                title_array = prop_value.get("title", [])
                return "".join([t.get("text", {}).get("content", "") for t in title_array])
            elif prop_type == "rich_text":
                rich_text_array = prop_value.get("rich_text", [])
                return "".join([t.get("text", {}).get("content", "") for t in rich_text_array])
            elif prop_type == "select":
                select_obj = prop_value.get("select")
                return select_obj.get("name", "") if select_obj else ""
            elif prop_type == "multi_select":
                multi_select_array = prop_value.get("multi_select", [])
                return ", ".join([opt.get("name", "") for opt in multi_select_array])
            elif prop_type == "date":
                date_obj = prop_value.get("date")
                if date_obj:
                    start = date_obj.get("start", "")
                    end = date_obj.get("end", "")
                    return f"{start} ~ {end}" if end else start
                return ""
            elif prop_type == "number":
                return str(prop_value.get("number", ""))
            elif prop_type == "checkbox":
                return "✅" if prop_value.get("checkbox") else "❌"
            elif prop_type == "url":
                return prop_value.get("url", "")
            elif prop_type == "email":
                return prop_value.get("email", "")
            elif prop_type == "phone_number":
                return prop_value.get("phone_number", "")
            elif prop_type == "relation":
                relations = prop_value.get("relation", [])
                return f"{len(relations)}개 연결" if relations else "연결 없음"
            elif prop_type == "people":
                people = prop_value.get("people", [])
                names = [person.get("name", "") for person in people]
                return ", ".join(names)
            elif prop_type == "files":
                files = prop_value.get("files", [])
                return f"{len(files)}개 파일" if files else "파일 없음"
            else:
                return str(prop_value)
        except Exception:
            return ""


@dataclass
class RelationMapping:
    """데이터베이스 간 관계 매핑"""
    source_db_id: str
    source_property: str
    target_db_id: str
    target_property: str
    relation_type: str = "dual_property"  # "dual_property", "single_property"


@dataclass
class SyncTarget:
    """동기화 대상 정의"""
    id: str                             # 페이지 또는 데이터베이스 ID
    type: str                           # "page", "database"
    name: str                           # 식별용 이름
    output_path: str                    # 출력 파일 경로
    format: ContentFormat = ContentFormat.MARKDOWN
    strategy: SyncStrategy = SyncStrategy.INCREMENTAL
    last_sync: Optional[datetime] = None
    custom_transformer: Optional[str] = None  # 사용자 정의 변환 함수명
    metadata: Dict[str, Any] = field(default_factory=dict)
    relation_filter: Optional[Dict[str, str]] = None  # 관계 기반 필터링 (속성명: 페이지ID)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (JSON 저장용)"""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "output_path": self.output_path,
            "format": self.format.value,
            "strategy": self.strategy.value,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "custom_transformer": self.custom_transformer,
            "metadata": self.metadata,
            "relation_filter": self.relation_filter
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncTarget':
        """딕셔너리에서 생성"""
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            output_path=data["output_path"],
            format=ContentFormat(data.get("format", "markdown")),
            strategy=SyncStrategy(data.get("strategy", "incremental")),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            custom_transformer=data.get("custom_transformer"),
            metadata=data.get("metadata", {}),
            relation_filter=data.get("relation_filter")
        )


@dataclass
class SyncConfiguration:
    """동기화 설정"""
    credentials: NotionCredentials
    targets: List[SyncTarget] = field(default_factory=list)
    relation_discovery: RelationDiscoveryMode = RelationDiscoveryMode.DISABLED
    relation_mappings: List[RelationMapping] = field(default_factory=list)
    auto_discover_hierarchy: bool = False
    max_hierarchy_depth: int = 3
    sync_interval_minutes: int = 30
    batch_size: int = 100
    output_base_path: str = "./"
    custom_transformers: Dict[str, Any] = field(default_factory=dict)
    
    def add_target(self, target: SyncTarget):
        """동기화 대상 추가"""
        # 중복 제거
        self.targets = [t for t in self.targets if t.id != target.id]
        self.targets.append(target)
    
    def remove_target(self, target_id: str):
        """동기화 대상 제거"""
        self.targets = [t for t in self.targets if t.id != target_id]
    
    def get_target(self, target_id: str) -> Optional[SyncTarget]:
        """특정 대상 조회"""
        for target in self.targets:
            if target.id == target_id:
                return target
        return None


@dataclass
class SyncResult:
    """동기화 결과"""
    target_id: str
    target_name: str
    success: bool
    start_time: datetime
    end_time: datetime
    changes_detected: bool = False
    output_file: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> float:
        """동기화 소요 시간 (초)"""
        return (self.end_time - self.start_time).total_seconds()


@dataclass
class BatchSyncResult:
    """배치 동기화 결과"""
    batch_id: str
    start_time: datetime
    end_time: datetime
    total_targets: int
    successful_syncs: int
    failed_syncs: int
    results: List[SyncResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """성공률"""
        if self.total_targets == 0:
            return 0.0
        return self.successful_syncs / self.total_targets
    
    @property
    def duration_seconds(self) -> float:
        """전체 소요 시간 (초)"""
        return (self.end_time - self.start_time).total_seconds() 