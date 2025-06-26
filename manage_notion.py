#!/usr/bin/env python3
"""
범용 Notion 동기화 CLI 도구

이 도구는 완전히 독립적으로 설계되어 다른 프로젝트에서도 재사용 가능합니다.
프로젝트별 의존성 없이 Notion API와의 동기화를 관리합니다.

사용법:
    python manage_notion.py --help
    python manage_notion.py add-page <page_id> --name "Document Name" --output "output.md"
    python manage_notion.py sync-all
    python manage_notion.py discover-hierarchy <database_id>
"""

import asyncio
import json
import sys
import os
from pathlib import Path
from typing import Optional, List
import uuid

import click

# 모듈 경로 추가 (독립 실행을 위해)
sys.path.insert(0, str(Path(__file__).parent))

from modules.notion_sync.service import (
    UniversalNotionSyncEngine, 
    ConfigurationManager,
    create_notion_sync_engine,
    quick_sync_page,
    quick_sync_database
)
from modules.notion_sync.models import (
    NotionCredentials, SyncTarget, SyncConfiguration, 
    ContentFormat, SyncStrategy, RelationDiscoveryMode
)


def get_notion_token() -> str:
    """환경변수에서 Notion 토큰 가져오기"""
    token = os.getenv('NOTION_TOKEN')
    if not token:
        click.echo("❌ NOTION_TOKEN 환경변수가 설정되지 않았습니다.")
        click.echo("다음 중 하나의 방법으로 설정하세요:")
        click.echo("1. export NOTION_TOKEN=your_token_here")
        click.echo("2. .env 파일에 NOTION_TOKEN=your_token_here 추가")
        sys.exit(1)
    return token


@click.group()
@click.option('--config', default='notion_sync_config.json', help='설정 파일 경로')
@click.pass_context
def cli(ctx, config):
    """범용 Notion 동기화 관리 도구"""
    ctx.ensure_object(dict)
    ctx.obj['config_file'] = config


@cli.command()
@click.argument('page_id')
@click.option('--name', required=True, help='페이지 식별 이름')
@click.option('--output', required=True, help='출력 파일 경로')
@click.option('--format', type=click.Choice(['markdown', 'json', 'plain_text']), 
              default='markdown', help='출력 형식')
@click.option('--strategy', type=click.Choice(['full_sync', 'incremental']), 
              default='incremental', help='동기화 전략')
@click.option('--transformer', help='사용자 정의 변환 함수명')
@click.pass_context
def add_page(ctx, page_id, name, output, format, strategy, transformer):
    """페이지를 동기화 대상에 추가"""
    asyncio.run(_add_page(ctx.obj['config_file'], page_id, name, output, format, strategy, transformer))


async def _add_page(config_file, page_id, name, output, format, strategy, transformer):
    token = get_notion_token()
    config_manager = ConfigurationManager(config_file)
    
    # 기존 설정 로드 또는 새 설정 생성
    config = config_manager.load_configuration()
    if not config:
        credentials = NotionCredentials(token=token)
        config = SyncConfiguration(credentials=credentials)
    else:
        config.credentials.token = token
    
    # 새 동기화 대상 생성
    target = SyncTarget(
        id=page_id,
        type="page",
        name=name,
        output_path=output,
        format=ContentFormat(format),
        strategy=SyncStrategy(strategy),
        custom_transformer=transformer
    )
    
    # 페이지 유효성 검사
    engine = UniversalNotionSyncEngine(config)
    page_data = await engine.api_client.get_page(page_id)
    
    if not page_data:
        click.echo(f"❌ 페이지 {page_id}를 찾을 수 없습니다.")
        return
    
    # 페이지 정보 출력
    page = await engine.processor.process_page(page_id)
    if page:
        click.echo(f"✅ 페이지 발견: {page.title}")
        click.echo(f"   URL: {page.url}")
        click.echo(f"   최종 수정: {page.last_edited_time}")
    
    # 설정에 추가
    config.add_target(target)
    config_manager.save_configuration(config)
    
    click.echo(f"✅ 페이지 '{name}'가 동기화 대상에 추가되었습니다.")
    click.echo(f"   출력 파일: {output}")
    click.echo(f"   형식: {format}")


@cli.command()
@click.argument('database_id')
@click.option('--name', required=True, help='데이터베이스 식별 이름')
@click.option('--output', required=True, help='출력 파일 경로')
@click.option('--format', type=click.Choice(['markdown', 'json', 'plain_text']), 
              default='markdown', help='출력 형식')
@click.option('--strategy', type=click.Choice(['full_sync', 'incremental']), 
              default='incremental', help='동기화 전략')
@click.option('--transformer', help='사용자 정의 변환 함수명')
@click.option('--filter-by', help='관계 필터링 (속성명:페이지ID 형식, 예: "프로젝트 마스터:21c18a4c52a1804ba78ddbcc2ba649d4")')
@click.pass_context
def add_database(ctx, database_id, name, output, format, strategy, transformer, filter_by):
    """데이터베이스를 동기화 대상에 추가"""
    asyncio.run(_add_database(ctx.obj['config_file'], database_id, name, output, format, strategy, transformer, filter_by))


async def _add_database(config_file, database_id, name, output, format, strategy, transformer, filter_by):
    token = get_notion_token()
    config_manager = ConfigurationManager(config_file)
    
    # 기존 설정 로드 또는 새 설정 생성
    config = config_manager.load_configuration()
    if not config:
        credentials = NotionCredentials(token=token)
        config = SyncConfiguration(credentials=credentials)
    else:
        config.credentials.token = token
    
    # 관계 필터 파싱
    relation_filter = None
    if filter_by:
        try:
            # "속성명:페이지ID" 형식 파싱
            property_name, page_id = filter_by.split(':', 1)
            relation_filter = {property_name.strip(): page_id.strip()}
            click.echo(f"🔍 관계 필터 설정: {property_name.strip()} → {page_id.strip()}")
        except ValueError:
            click.echo("❌ 잘못된 필터 형식입니다. '속성명:페이지ID' 형식으로 입력하세요.")
            return
    
    # 새 동기화 대상 생성
    target = SyncTarget(
        id=database_id,
        type="database",
        name=name,
        output_path=output,
        format=ContentFormat(format),
        strategy=SyncStrategy(strategy),
        custom_transformer=transformer,
        relation_filter=relation_filter
    )
    
    # 데이터베이스 유효성 검사
    engine = UniversalNotionSyncEngine(config)
    db_data = await engine.api_client.get_database(database_id)
    
    if not db_data:
        click.echo(f"❌ 데이터베이스 {database_id}를 찾을 수 없습니다.")
        return
    
    # 데이터베이스 정보 출력
    db = await engine.processor.process_database(database_id)
    if db:
        click.echo(f"✅ 데이터베이스 발견: {db.title}")
        click.echo(f"   URL: {db.url}")
        click.echo(f"   속성 수: {len(db.properties)}")
        click.echo(f"   최종 수정: {db.last_edited_time}")
    
    # 설정에 추가
    config.add_target(target)
    config_manager.save_configuration(config)
    
    click.echo(f"✅ 데이터베이스 '{name}'가 동기화 대상에 추가되었습니다.")
    click.echo(f"   출력 파일: {output}")
    click.echo(f"   형식: {format}")


@cli.command()
@click.argument('target_id')
@click.pass_context
def remove(ctx, target_id):
    """동기화 대상 제거"""
    config_manager = ConfigurationManager(ctx.obj['config_file'])
    config = config_manager.load_configuration()
    
    if not config:
        click.echo("❌ 설정 파일이 없습니다.")
        return
    
    # 대상 찾기
    target = config.get_target(target_id)
    if not target:
        click.echo(f"❌ 대상 {target_id}를 찾을 수 없습니다.")
        return
    
    # 제거 확인
    if click.confirm(f"'{target.name}' 대상을 제거하시겠습니까?"):
        config.remove_target(target_id)
        config_manager.save_configuration(config)
        click.echo(f"✅ '{target.name}' 대상이 제거되었습니다.")


@cli.command()
@click.pass_context
def list_targets(ctx):
    """동기화 대상 목록 조회"""
    config_manager = ConfigurationManager(ctx.obj['config_file'])
    config = config_manager.load_configuration()
    
    if not config or not config.targets:
        click.echo("📝 등록된 동기화 대상이 없습니다.")
        return
    
    click.echo(f"📋 등록된 동기화 대상 ({len(config.targets)}개):")
    click.echo()
    
    for i, target in enumerate(config.targets, 1):
        click.echo(f"{i}. {target.name}")
        click.echo(f"   ID: {target.id}")
        click.echo(f"   타입: {target.type}")
        click.echo(f"   출력: {target.output_path}")
        click.echo(f"   형식: {target.format.value}")
        click.echo(f"   전략: {target.strategy.value}")
        if target.last_sync:
            click.echo(f"   최종 동기화: {target.last_sync}")
        click.echo()


@cli.command()
@click.option('--target', help='특정 대상만 동기화 (ID 또는 이름)')
@click.pass_context
def sync(ctx, target):
    """동기화 실행"""
    asyncio.run(_sync(ctx.obj['config_file'], target))


async def _sync(config_file, target_filter):
    token = get_notion_token()
    config_manager = ConfigurationManager(config_file)
    config = config_manager.load_configuration()
    
    if not config:
        click.echo("❌ 설정 파일이 없습니다. 먼저 대상을 추가하세요.")
        return
    
    config.credentials.token = token
    engine = UniversalNotionSyncEngine(config)
    
    # 동기화할 대상 필터링
    targets_to_sync = config.targets
    if target_filter:
        targets_to_sync = [
            t for t in config.targets 
            if target_filter in [t.id, t.name]
        ]
        if not targets_to_sync:
            click.echo(f"❌ 대상 '{target_filter}'를 찾을 수 없습니다.")
            return
    
    if not targets_to_sync:
        click.echo("📝 동기화할 대상이 없습니다.")
        return
    
    click.echo(f"🔄 {len(targets_to_sync)}개 대상 동기화 시작...")
    
    # 개별 동기화 실행
    for target in targets_to_sync:
        click.echo(f"\n📄 {target.name} 동기화 중...")
        result = await engine.sync_target(target)
        
        if result.success:
            if result.changes_detected:
                click.echo(f"✅ {target.name} 동기화 완료: {result.output_file}")
            else:
                click.echo(f"📝 {target.name}: 변경사항 없음")
        else:
            click.echo(f"❌ {target.name} 동기화 실패: {result.error_message}")
    
    # 설정 저장 (last_sync 업데이트)
    config_manager.save_configuration(config)
    click.echo("\n🎉 동기화 완료!")


@cli.command()
@click.argument('database_id')
@click.option('--max-depth', default=3, help='최대 탐색 깊이')
@click.option('--auto-add', is_flag=True, help='발견된 대상을 자동으로 추가')
@click.pass_context
def discover_hierarchy(ctx, database_id, max_depth, auto_add):
    """데이터베이스 계층 구조 자동 발견"""
    asyncio.run(_discover_hierarchy(ctx.obj['config_file'], database_id, max_depth, auto_add))


async def _discover_hierarchy(config_file, database_id, max_depth, auto_add):
    token = get_notion_token()
    config_manager = ConfigurationManager(config_file)
    
    # 기존 설정 로드 또는 새 설정 생성
    config = config_manager.load_configuration()
    if not config:
        credentials = NotionCredentials(token=token)
        config = SyncConfiguration(
            credentials=credentials,
            relation_discovery=RelationDiscoveryMode.DEEP,
            max_hierarchy_depth=max_depth
        )
    else:
        config.credentials.token = token
        config.relation_discovery = RelationDiscoveryMode.DEEP
        config.max_hierarchy_depth = max_depth
    
    engine = UniversalNotionSyncEngine(config)
    
    click.echo(f"🔍 데이터베이스 {database_id}에서 계층 구조 탐색 중...")
    click.echo(f"   최대 깊이: {max_depth}")
    
    # 관계 발견
    relations = await engine.relation_engine.discover_hierarchy(database_id, max_depth)
    
    if not relations:
        click.echo("📝 발견된 관계가 없습니다.")
        return
    
    click.echo(f"\n🔗 발견된 관계 ({len(relations)}개):")
    
    unique_dbs = set()
    for i, relation in enumerate(relations, 1):
        click.echo(f"\n{i}. {relation.source_property} → {relation.target_property}")
        click.echo(f"   소스: {relation.source_db_id}")
        click.echo(f"   대상: {relation.target_db_id}")
        click.echo(f"   타입: {relation.relation_type}")
        
        unique_dbs.add(relation.source_db_id)
        unique_dbs.add(relation.target_db_id)
    
    click.echo(f"\n📊 발견된 고유 데이터베이스: {len(unique_dbs)}개")
    
    if auto_add:
        click.echo("\n🔄 발견된 데이터베이스를 동기화 대상으로 추가 중...")
        
        discovered_targets = await engine.discover_and_add_hierarchy(database_id)
        
        if discovered_targets:
            click.echo(f"✅ {len(discovered_targets)}개 대상이 추가되었습니다:")
            for target in discovered_targets:
                click.echo(f"   - {target.name} ({target.type})")
            
            config_manager.save_configuration(config)
            click.echo("\n💾 설정이 저장되었습니다.")
        else:
            click.echo("📝 새로 추가된 대상이 없습니다.")
    else:
        click.echo(f"\n💡 발견된 데이터베이스를 동기화 대상으로 추가하려면 --auto-add 옵션을 사용하세요.")


@cli.command()
@click.pass_context
def test_connection(ctx):
    """Notion API 연결 테스트"""
    asyncio.run(_test_connection())


async def _test_connection():
    token = get_notion_token()
    
    try:
        # 간단한 API 호출로 연결 테스트
        engine = await create_notion_sync_engine(token)
        
        # 테스트용 더미 페이지 조회 (실패해도 됨)
        test_result = await engine.api_client.get_page("dummy-id")
        
        click.echo("✅ Notion API 연결 성공!")
        click.echo(f"   토큰: {token[:10]}...{token[-4:]}")
        click.echo("   API 버전: 2022-06-28")
        
    except Exception as e:
        click.echo(f"❌ Notion API 연결 실패: {e}")


@cli.command()
@click.argument('page_id')
@click.argument('output_file')
@click.option('--format', type=click.Choice(['markdown', 'json', 'plain_text']), 
              default='markdown', help='출력 형식')
def quick_page(page_id, output_file, format):
    """빠른 페이지 동기화 (설정 파일 없이)"""
    asyncio.run(_quick_page(page_id, output_file, format))


async def _quick_page(page_id, output_file, format):
    token = get_notion_token()
    
    click.echo(f"⚡ 빠른 페이지 동기화: {page_id}")
    
    success = await quick_sync_page(
        token, 
        page_id, 
        output_file, 
        ContentFormat(format)
    )
    
    if success:
        click.echo(f"✅ 동기화 완료: {output_file}")
    else:
        click.echo("❌ 동기화 실패")


@cli.command()
@click.argument('database_id')
@click.argument('output_file')
@click.option('--format', type=click.Choice(['markdown', 'json', 'plain_text']), 
              default='markdown', help='출력 형식')
def quick_database(database_id, output_file, format):
    """빠른 데이터베이스 동기화 (설정 파일 없이)"""
    asyncio.run(_quick_database(database_id, output_file, format))


async def _quick_database(database_id, output_file, format):
    token = get_notion_token()
    
    click.echo(f"⚡ 빠른 데이터베이스 동기화: {database_id}")
    
    success = await quick_sync_database(
        token, 
        database_id, 
        output_file, 
        ContentFormat(format)
    )
    
    if success:
        click.echo(f"✅ 동기화 완료: {output_file}")
    else:
        click.echo("❌ 동기화 실패")


@cli.command()
@click.pass_context
def export_config(ctx):
    """설정 파일을 JSON으로 출력"""
    config_manager = ConfigurationManager(ctx.obj['config_file'])
    config = config_manager.load_configuration()
    
    if not config:
        click.echo("❌ 설정 파일이 없습니다.")
        return
    
    # 토큰 마스킹
    masked_config = {
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
        "settings": {
            "auto_discover_hierarchy": config.auto_discover_hierarchy,
            "max_hierarchy_depth": config.max_hierarchy_depth,
            "sync_interval_minutes": config.sync_interval_minutes,
            "batch_size": config.batch_size,
            "output_base_path": config.output_base_path
        }
    }
    
    click.echo(json.dumps(masked_config, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    # CLI 실행
    cli() 