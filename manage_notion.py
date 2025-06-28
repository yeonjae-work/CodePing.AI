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

import sys
import os
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any
import click

# 모듈 경로 추가 (독립 실행을 위해)
sys.path.insert(0, str(Path(__file__).parent))

from modules.notion_sync.service import (
    UniversalNotionSyncEngine,
    ConfigurationManager,
    create_notion_sync_engine,
    quick_sync_page,
    quick_sync_database,
)
from modules.notion_sync.models import (
    NotionCredentials,
    SyncTarget,
    SyncConfiguration,
    ContentFormat,
    SyncStrategy,
    RelationDiscoveryMode,
)


def get_notion_token() -> str:
    """환경변수에서 Notion 토큰 가져오기"""
    token = os.getenv("NOTION_TOKEN")
    if not token:
        click.echo("❌ NOTION_TOKEN 환경변수가 설정되지 않았습니다.")
        click.echo("다음 중 하나의 방법으로 설정하세요:")
        click.echo("1. export NOTION_TOKEN=your_token_here")
        click.echo("2. .env 파일에 NOTION_TOKEN=your_token_here 추가")
        sys.exit(1)
    return token


@click.group()
@click.option("--config", default="notion_sync_config.json", help="설정 파일 경로")
@click.pass_context
def cli(ctx, config):
    """범용 Notion 동기화 관리 도구"""
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config


@cli.command()
def test_simple():
    """간단한 동기화 테스트"""
    click.echo("🧪 간단한 동기화 테스트 시작...")

    try:
        # 테스트용 페이지 ID (실제 존재하는 페이지로 교체 필요)
        test_page_id = "21c18a4c52a1804ba78ddbcc2ba649d4"

        # 간단한 동기화 실행
        result = asyncio.run(_test_simple_sync(test_page_id))

        if result:
            click.echo("✅ 간단한 동기화 테스트 성공!")
        else:
            click.echo("❌ 간단한 동기화 테스트 실패")

    except Exception as e:
        click.echo(f"❌ 테스트 중 오류 발생: {e}")


async def _test_simple_sync(page_id: str):
    """간단한 동기화 테스트 실행"""
    try:
        token = get_notion_token()

        # 간단한 페이지 동기화 테스트
        result = await quick_sync_page(
            page_id=page_id, token=token, output_file="test_output.md"
        )

        return result is not None

    except Exception as e:
        click.echo(f"동기화 오류: {e}")
        return False


if __name__ == "__main__":
    cli()
