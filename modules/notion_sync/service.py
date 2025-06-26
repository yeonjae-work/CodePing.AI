"""
범용 Notion 동기화 모듈 - 서비스 레이어

이 모듈은 완전히 독립적으로 설계되어 다른 프로젝트에서도 재사용 가능합니다.
프로젝트별 의존성 없이 Notion API와의 동기화를 담당합니다.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Generator, Callable

import httpx
from pydantic import ValidationError

from .models import (
    NotionCredentials, NotionPage, NotionDatabase, NotionBlock,
    SyncTarget, SyncConfiguration, SyncResult, BatchSyncResult,
    SyncStrategy, ContentFormat, RelationDiscoveryMode, RelationMapping
)
from shared.config.settings import get_settings

logger = logging.getLogger(__name__)


class NotionAPIClient:
    """Notion API 클라이언트 - 완전 독립적"""
    
    def __init__(self, credentials: NotionCredentials):
        self.credentials = credentials
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
            "Notion-Version": credentials.version
        }
    
    async def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """페이지 정보 조회"""
        url = f"{self.base_url}/pages/{page_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting page {page_id}: {e}")
            return None
    
    async def get_database(self, database_id: str) -> Optional[Dict[str, Any]]:
        """데이터베이스 정보 조회"""
        url = f"{self.base_url}/databases/{database_id}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error getting database {database_id}: {e}")
            return None
    
    async def query_database(
        self, 
        database_id: str, 
        filter_condition: Optional[Dict] = None,
        sorts: Optional[List[Dict]] = None,
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """데이터베이스 쿼리"""
        url = f"{self.base_url}/databases/{database_id}/query"
        
        body = {
            "page_size": page_size
        }
        if filter_condition:
            body["filter"] = filter_condition
        if sorts:
            body["sorts"] = sorts
        
        all_results = []
        has_more = True
        start_cursor = None
        
        try:
            async with httpx.AsyncClient() as client:
                while has_more:
                    if start_cursor:
                        body["start_cursor"] = start_cursor
                    
                    response = await client.post(url, headers=self.headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    all_results.extend(data.get("results", []))
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")
        except Exception as e:
            logger.error(f"Error querying database {database_id}: {e}")
        
        return all_results
    
    async def get_block_children(self, block_id: str) -> List[Dict[str, Any]]:
        """블록의 자식 요소들 조회"""
        url = f"{self.base_url}/blocks/{block_id}/children"
        
        all_blocks = []
        has_more = True
        start_cursor = None
        
        try:
            async with httpx.AsyncClient() as client:
                while has_more:
                    params = {"page_size": 100}
                    if start_cursor:
                        params["start_cursor"] = start_cursor
                    
                    response = await client.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    all_blocks.extend(data.get("results", []))
                    has_more = data.get("has_more", False)
                    start_cursor = data.get("next_cursor")
        except Exception as e:
            logger.error(f"Error getting blocks for {block_id}: {e}")
        
        return all_blocks


class NotionContentProcessor:
    """Notion 콘텐츠 처리기 - 완전 독립적"""
    
    def __init__(self, api_client: NotionAPIClient):
        self.api_client = api_client
    
    async def process_page(self, page_id: str) -> Optional[NotionPage]:
        """페이지 전체 처리"""
        page_data = await self.api_client.get_page(page_id)
        if not page_data:
            return None
        
        # 기본 페이지 정보 추출
        notion_page = self._extract_page_info(page_data)
        
        # 블록 내용 추가
        blocks = await self._process_page_blocks(page_id)
        notion_page.blocks = blocks
        
        return notion_page
    
    async def process_database(
        self, 
        database_id: str, 
        include_pages: bool = True,
        relation_filter: Optional[Dict[str, str]] = None
    ) -> Optional[NotionDatabase]:
        """데이터베이스 처리 (페이지 포함 가능, 관계 필터링 지원)"""
        db_data = await self.api_client.get_database(database_id)
        if not db_data:
            return None
        
        database = self._extract_database_info(db_data)
        
        # 데이터베이스 내 페이지들도 가져오기
        if include_pages:
            try:
                # 관계 기반 필터 생성
                filter_condition = None
                if relation_filter:
                    filter_condition = self._build_relation_filter(relation_filter, database.properties)
                
                pages_data = await self.api_client.query_database(database_id, filter_condition)
                for page_data in pages_data:
                    page = self._extract_page_info(page_data)
                    # 페이지 본문 블록들도 가져오기
                    blocks = await self._process_page_blocks(page.id)
                    page.blocks = blocks
                    database.pages.append(page)
                    
                if relation_filter:
                    print(f"✅ 데이터베이스 '{database.title}'에서 관계 필터링 후 {len(database.pages)}개 페이지 로드됨")
                else:
                    print(f"✅ 데이터베이스 '{database.title}'에서 {len(database.pages)}개 페이지 로드됨")
            except Exception as e:
                print(f"⚠️ 데이터베이스 페이지 로드 실패: {e}")
        
        return database
    
    def _build_relation_filter(self, relation_filter: Dict[str, str], db_properties: Dict[str, Any]) -> Dict[str, Any]:
        """관계 기반 필터 조건 생성"""
        filters = []
        
        for property_name, target_page_id in relation_filter.items():
            # 해당 속성이 relation 타입인지 확인
            if property_name in db_properties and db_properties[property_name].get("type") == "relation":
                filter_condition = {
                    "property": property_name,
                    "relation": {
                        "contains": target_page_id
                    }
                }
                filters.append(filter_condition)
        
        if not filters:
            return {}
        
        return filters[0] if len(filters) == 1 else {"or": filters}
    
    def _extract_page_info(self, page_data: Dict[str, Any]) -> NotionPage:
        """페이지 기본 정보 추출"""
        title = self._extract_title(page_data)
        
        return NotionPage(
            id=page_data["id"],
            title=title,
            url=page_data["url"],
            created_time=datetime.fromisoformat(page_data["created_time"].replace("Z", "+00:00")),
            last_edited_time=datetime.fromisoformat(page_data["last_edited_time"].replace("Z", "+00:00")),
            properties=page_data.get("properties", {}),
            parent_id=self._extract_parent_id(page_data),
            parent_type=self._extract_parent_type(page_data),
            archived=page_data.get("archived", False)
        )
    
    def _extract_database_info(self, db_data: Dict[str, Any]) -> NotionDatabase:
        """데이터베이스 기본 정보 추출"""
        title = self._extract_title_from_rich_text(db_data.get("title", []))
        description = self._extract_title_from_rich_text(db_data.get("description", []))
        
        return NotionDatabase(
            id=db_data["id"],
            title=title,
            url=db_data["url"],
            properties=db_data.get("properties", {}),
            created_time=datetime.fromisoformat(db_data["created_time"].replace("Z", "+00:00")) if db_data.get("created_time") else None,
            last_edited_time=datetime.fromisoformat(db_data["last_edited_time"].replace("Z", "+00:00")) if db_data.get("last_edited_time") else None,
            parent_id=self._extract_parent_id(db_data),
            description=description
        )
    
    async def _process_page_blocks(self, page_id: str) -> List[NotionBlock]:
        """페이지의 모든 블록 처리"""
        blocks_data = await self.api_client.get_block_children(page_id)
        blocks = []
        
        for block_data in blocks_data:
            block = await self._process_block(block_data)
            if block:
                blocks.append(block)
        
        return blocks
    
    async def _process_block(self, block_data: Dict[str, Any]) -> Optional[NotionBlock]:
        """개별 블록 처리"""
        block_type = block_data.get("type")
        if not block_type:
            return None
        
        block = NotionBlock(
            id=block_data["id"],
            type=block_type,
            content=block_data.get(block_type, {}),
            has_children=block_data.get("has_children", False),
            created_time=datetime.fromisoformat(block_data["created_time"].replace("Z", "+00:00")) if block_data.get("created_time") else None,
            last_edited_time=datetime.fromisoformat(block_data["last_edited_time"].replace("Z", "+00:00")) if block_data.get("last_edited_time") else None
        )
        
        # 자식 블록이 있으면 재귀적으로 처리
        if block.has_children:
            children_data = await self.api_client.get_block_children(block.id)
            children = []
            for child_data in children_data:
                child_block = await self._process_block(child_data)
                if child_block:
                    children.append(child_block)
            block.children = children
        
        return block
    
    def _extract_title(self, page_data: Dict[str, Any]) -> str:
        """페이지 제목 추출"""
        properties = page_data.get("properties", {})
        
        # 제목 속성 찾기
        for prop_name, prop_data in properties.items():
            if prop_data.get("type") == "title":
                title_array = prop_data.get("title", [])
                return self._extract_title_from_rich_text(title_array)
        
        return "Untitled"
    
    def _extract_title_from_rich_text(self, rich_text_array: List[Dict]) -> str:
        """Rich text 배열에서 제목 추출"""
        if not rich_text_array:
            return ""
        
        title_parts = []
        for text_obj in rich_text_array:
            if text_obj.get("type") == "text":
                content = text_obj.get("text", {}).get("content", "")
                title_parts.append(content)
        
        return "".join(title_parts)
    
    def _extract_parent_id(self, data: Dict[str, Any]) -> Optional[str]:
        """부모 ID 추출"""
        parent = data.get("parent", {})
        if parent.get("type") == "database_id":
            return parent.get("database_id")
        elif parent.get("type") == "page_id":
            return parent.get("page_id")
        return None
    
    def _extract_parent_type(self, data: Dict[str, Any]) -> Optional[str]:
        """부모 타입 추출"""
        parent = data.get("parent", {})
        return parent.get("type")


class RelationDiscoveryEngine:
    """관계 발견 엔진 - 완전 독립적"""
    
    def __init__(self, api_client: NotionAPIClient, processor: NotionContentProcessor):
        self.api_client = api_client
        self.processor = processor
    
    async def discover_hierarchy(
        self, 
        root_database_id: str, 
        max_depth: int = 3
    ) -> List[RelationMapping]:
        """계층적 관계 자동 발견"""
        discovered_relations = []
        visited_dbs = set()
        
        await self._discover_relations_recursive(
            root_database_id, 
            discovered_relations, 
            visited_dbs, 
            current_depth=0, 
            max_depth=max_depth
        )
        
        return discovered_relations
    
    async def _discover_relations_recursive(
        self,
        database_id: str,
        discovered_relations: List[RelationMapping],
        visited_dbs: set,
        current_depth: int,
        max_depth: int
    ):
        """재귀적 관계 발견"""
        if current_depth >= max_depth or database_id in visited_dbs:
            return
        
        visited_dbs.add(database_id)
        
        # 데이터베이스 스키마 조회
        db = await self.processor.process_database(database_id)
        if not db:
            return
        
        # 관계 속성 찾기
        for prop_name, prop_data in db.properties.items():
            if prop_data.get("type") == "relation":
                relation_info = prop_data.get("relation", {})
                target_db_id = relation_info.get("database_id")
                
                if target_db_id and target_db_id not in visited_dbs:
                    # 관계 매핑 추가
                    relation_mapping = RelationMapping(
                        source_db_id=database_id,
                        source_property=prop_name,
                        target_db_id=target_db_id,
                        target_property=relation_info.get("dual_property", {}).get("synced_property_name", ""),
                        relation_type=relation_info.get("type", "dual_property")
                    )
                    discovered_relations.append(relation_mapping)
                    
                    # 재귀적으로 대상 데이터베이스 탐색
                    await self._discover_relations_recursive(
                        target_db_id,
                        discovered_relations,
                        visited_dbs,
                        current_depth + 1,
                        max_depth
                    )


class UniversalNotionSyncEngine:
    """범용 Notion 동기화 엔진 - 완전 독립적"""
    
    def __init__(self, config: SyncConfiguration):
        self.config = config
        self.api_client = NotionAPIClient(config.credentials)
        self.processor = NotionContentProcessor(self.api_client)
        self.relation_engine = RelationDiscoveryEngine(self.api_client, self.processor)
        self.custom_transformers: Dict[str, Callable] = {}
    
    def register_transformer(self, name: str, transformer: Callable):
        """사용자 정의 변환 함수 등록"""
        self.custom_transformers[name] = transformer
    
    async def sync_all_targets(self) -> BatchSyncResult:
        """모든 대상 동기화"""
        batch_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        results = []
        
        logger.info(f"Starting batch sync {batch_id} for {len(self.config.targets)} targets")
        
        for target in self.config.targets:
            result = await self.sync_target(target)
            results.append(result)
        
        end_time = datetime.now(timezone.utc)
        successful_syncs = sum(1 for r in results if r.success)
        failed_syncs = len(results) - successful_syncs
        
        batch_result = BatchSyncResult(
            batch_id=batch_id,
            start_time=start_time,
            end_time=end_time,
            total_targets=len(self.config.targets),
            successful_syncs=successful_syncs,
            failed_syncs=failed_syncs,
            results=results
        )
        
        logger.info(f"Batch sync {batch_id} completed: {successful_syncs}/{len(results)} successful")
        return batch_result
    
    async def sync_target(self, target: SyncTarget) -> SyncResult:
        """개별 대상 동기화"""
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"Syncing {target.type} {target.name} ({target.id})")
            
            # 변경 감지 (증분 동기화인 경우)
            if target.strategy == SyncStrategy.INCREMENTAL and target.last_sync:
                changes_detected = await self._check_for_changes(target)
                if not changes_detected:
                    logger.info(f"No changes detected for {target.name}")
                    return SyncResult(
                        target_id=target.id,
                        target_name=target.name,
                        success=True,
                        start_time=start_time,
                        end_time=datetime.now(timezone.utc),
                        changes_detected=False
                    )
            
            # 콘텐츠 처리
            if target.type == "page":
                notion_data = await self.processor.process_page(target.id)
            elif target.type == "database":
                notion_data = await self.processor.process_database(
                    target.id, 
                    include_pages=True,
                    relation_filter=target.relation_filter
                )
            else:
                raise ValueError(f"Unsupported target type: {target.type}")
            
            if not notion_data:
                raise Exception("Failed to fetch Notion data")
            
            # 콘텐츠 변환
            content = await self._transform_content(notion_data, target)
            
            # 파일 저장
            output_path = self._resolve_output_path(target)
            await self._save_content(content, output_path)
            
            # 동기화 시간 업데이트
            target.last_sync = datetime.now(timezone.utc)
            
            end_time = datetime.now(timezone.utc)
            logger.info(f"Successfully synced {target.name} to {output_path}")
            
            return SyncResult(
                target_id=target.id,
                target_name=target.name,
                success=True,
                start_time=start_time,
                end_time=end_time,
                changes_detected=True,
                output_file=str(output_path)
            )
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            logger.error(f"Failed to sync {target.name}: {e}")
            
            return SyncResult(
                target_id=target.id,
                target_name=target.name,
                success=False,
                start_time=start_time,
                end_time=end_time,
                error_message=str(e)
            )
    
    async def discover_and_add_hierarchy(self, root_database_id: str) -> List[SyncTarget]:
        """계층 구조 자동 발견 및 동기화 대상 추가"""
        if self.config.relation_discovery == RelationDiscoveryMode.DISABLED:
            return []
        
        logger.info(f"Discovering hierarchy starting from {root_database_id}")
        
        # 관계 발견
        relations = await self.relation_engine.discover_hierarchy(
            root_database_id, 
            self.config.max_hierarchy_depth
        )
        
        # 관계 매핑 업데이트
        self.config.relation_mappings.extend(relations)
        
        # 발견된 모든 데이터베이스/페이지를 동기화 대상으로 추가
        discovered_targets = []
        unique_ids = set()
        
        for relation in relations:
            for db_id in [relation.source_db_id, relation.target_db_id]:
                if db_id not in unique_ids:
                    unique_ids.add(db_id)
                    
                    # 데이터베이스 정보 조회
                    db = await self.processor.process_database(db_id)
                    if db:
                        target = SyncTarget(
                            id=db_id,
                            type="database",
                            name=db.title or f"Database-{db_id[:8]}",
                            output_path=f"{db.title or db_id}.md",
                            format=ContentFormat.MARKDOWN,
                            strategy=SyncStrategy.INCREMENTAL
                        )
                        discovered_targets.append(target)
                        self.config.add_target(target)
        
        logger.info(f"Discovered {len(discovered_targets)} new targets from hierarchy")
        return discovered_targets
    
    async def _check_for_changes(self, target: SyncTarget) -> bool:
        """변경 감지"""
        try:
            # 출력 파일이 존재하지 않으면 강제 동기화
            output_path = self._resolve_output_path(target)
            if not output_path.exists():
                return True
            
            # last_sync가 None이면 강제 동기화
            if target.last_sync is None:
                return True
            
            if target.type == "page":
                page_data = await self.api_client.get_page(target.id)
                if page_data:
                    last_edited = datetime.fromisoformat(page_data["last_edited_time"].replace("Z", "+00:00"))
                    return last_edited > target.last_sync
            elif target.type == "database":
                db_data = await self.api_client.get_database(target.id)
                if db_data:
                    last_edited = datetime.fromisoformat(db_data["last_edited_time"].replace("Z", "+00:00"))
                    return last_edited > target.last_sync
        except Exception as e:
            logger.warning(f"Error checking changes for {target.name}: {e}")
        
        return True  # 에러가 있으면 동기화 진행
    
    async def _transform_content(self, notion_data: Any, target: SyncTarget) -> str:
        """콘텐츠 변환"""
        # 사용자 정의 변환 함수 사용
        if target.custom_transformer and target.custom_transformer in self.custom_transformers:
            transformer = self.custom_transformers[target.custom_transformer]
            return transformer(notion_data, target)
        
        # 기본 변환
        if target.format == ContentFormat.MARKDOWN:
            return notion_data.to_markdown()
        elif target.format == ContentFormat.JSON:
            if hasattr(notion_data, '__dict__'):
                return json.dumps(notion_data.__dict__, default=str, indent=2)
            else:
                return json.dumps(notion_data, default=str, indent=2)
        elif target.format == ContentFormat.PLAIN_TEXT:
            markdown = notion_data.to_markdown()
            # 간단한 마크다운 제거 (더 정교한 처리 필요시 markdown 라이브러리 사용)
            return markdown.replace("#", "").replace("**", "").replace("*", "")
        else:
            return str(notion_data)
    
    def _resolve_output_path(self, target: SyncTarget) -> Path:
        """출력 경로 해결"""
        base_path = Path(self.config.output_base_path)
        return base_path / target.output_path
    
    async def _save_content(self, content: str, output_path: Path):
        """콘텐츠 저장"""
        # 디렉터리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 파일 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)


class ConfigurationManager:
    """설정 관리자 - 완전 독립적"""
    
    def __init__(self, config_file: str = "notion_sync_config.json"):
        self.config_file = Path(config_file)
    
    def load_configuration(self) -> Optional[SyncConfiguration]:
        """설정 파일 로드"""
        if not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            credentials = NotionCredentials(
                token=data["credentials"]["token"],
                version=data["credentials"].get("version", "2022-06-28")
            )
            
            targets = [SyncTarget.from_dict(target_data) for target_data in data.get("targets", [])]
            
            relation_mappings = [
                RelationMapping(**mapping_data) 
                for mapping_data in data.get("relation_mappings", [])
            ]
            
            config = SyncConfiguration(
                credentials=credentials,
                targets=targets,
                relation_discovery=RelationDiscoveryMode(data.get("relation_discovery", "disabled")),
                relation_mappings=relation_mappings,
                auto_discover_hierarchy=data.get("auto_discover_hierarchy", False),
                max_hierarchy_depth=data.get("max_hierarchy_depth", 3),
                sync_interval_minutes=data.get("sync_interval_minutes", 30),
                batch_size=data.get("batch_size", 100),
                output_base_path=data.get("output_base_path", "./"),
                custom_transformers=data.get("custom_transformers", {})
            )
            
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return None
    
    def save_configuration(self, config: SyncConfiguration):
        """설정 파일 저장"""
        try:
            data = {
                "credentials": {
                    "token": config.credentials.token,
                    "version": config.credentials.version
                },
                "targets": [target.to_dict() for target in config.targets],
                "relation_discovery": config.relation_discovery.value,
                "relation_mappings": [
                    {
                        "source_db_id": rm.source_db_id,
                        "source_property": rm.source_property,
                        "target_db_id": rm.target_db_id,
                        "target_property": rm.target_property,
                        "relation_type": rm.relation_type
                    }
                    for rm in config.relation_mappings
                ],
                "auto_discover_hierarchy": config.auto_discover_hierarchy,
                "max_hierarchy_depth": config.max_hierarchy_depth,
                "sync_interval_minutes": config.sync_interval_minutes,
                "batch_size": config.batch_size,
                "output_base_path": config.output_base_path,
                "custom_transformers": config.custom_transformers
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")


# 편의 함수들
async def create_notion_sync_engine(
    notion_token: str,
    output_base_path: str = "./",
    config_file: str = "notion_sync_config.json"
) -> UniversalNotionSyncEngine:
    """간편한 동기화 엔진 생성"""
    config_manager = ConfigurationManager(config_file)
    
    # 기존 설정 로드 시도
    config = config_manager.load_configuration()
    
    if not config:
        # 새 설정 생성
        credentials = NotionCredentials(token=notion_token)
        config = SyncConfiguration(
            credentials=credentials,
            output_base_path=output_base_path
        )
    else:
        # 토큰 및 경로 업데이트
        config.credentials.token = notion_token
        config.output_base_path = output_base_path
    
    return UniversalNotionSyncEngine(config)


async def quick_sync_page(
    notion_token: str,
    page_id: str,
    output_file: str,
    format: ContentFormat = ContentFormat.MARKDOWN
) -> bool:
    """빠른 페이지 동기화"""
    try:
        engine = await create_notion_sync_engine(notion_token)
        
        target = SyncTarget(
            id=page_id,
            type="page",
            name=f"Page-{page_id[:8]}",
            output_path=output_file,
            format=format,
            strategy=SyncStrategy.FULL_SYNC
        )
        
        result = await engine.sync_target(target)
        return result.success
        
    except Exception as e:
        logger.error(f"Quick sync failed: {e}")
        return False


async def quick_sync_database(
    notion_token: str,
    database_id: str,
    output_file: str,
    format: ContentFormat = ContentFormat.MARKDOWN
) -> bool:
    """빠른 데이터베이스 동기화"""
    try:
        engine = await create_notion_sync_engine(notion_token)
        
        target = SyncTarget(
            id=database_id,
            type="database",
            name=f"Database-{database_id[:8]}",
            output_path=output_file,
            format=format,
            strategy=SyncStrategy.FULL_SYNC
        )
        
        result = await engine.sync_target(target)
        return result.success
        
    except Exception as e:
        logger.error(f"Quick sync failed: {e}")
        return False 