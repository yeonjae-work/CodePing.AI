#!/usr/bin/env python3
"""
DataStorage MVP 데이터베이스 마이그레이션 스크립트

이 스크립트는 설계서를 바탕으로 구현된 MVP 버전의 DataStorage 모듈을 위한
데이터베이스 테이블들을 생성합니다.
"""

import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config.database import create_tables_sync, get_sync_engine
from modules.data_storage.models import Base, CommitRecord, DiffRecord, Event


def main():
    """메인 마이그레이션 함수"""

    print("🔄 DataStorage MVP 데이터베이스 마이그레이션 시작...")

    try:
        # 엔진 확인
        engine = get_sync_engine()
        print(f"📊 데이터베이스 연결: {engine.url}")

        # 테이블 생성
        print("🏗️  테이블 생성 중...")
        create_tables_sync()

        # 생성된 테이블 확인
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print("✅ 생성된 테이블:")
        for table in sorted(tables):
            print(f"   - {table}")

            # 컬럼 정보 출력
            columns = inspector.get_columns(table)
            for col in columns:
                col_info = f"     • {col['name']}: {col['type']}"
                if col.get("nullable", True) is False:
                    col_info += " NOT NULL"
                if col.get("primary_key", False):
                    col_info += " PRIMARY KEY"
                print(col_info)
            print()

        # 인덱스 확인
        print("🔍 인덱스 정보:")
        for table in ["commits", "commit_diffs", "events"]:
            if table in tables:
                indexes = inspector.get_indexes(table)
                if indexes:
                    print(f"   {table}:")
                    for idx in indexes:
                        print(f"     - {idx['name']}: {idx['column_names']}")

        print("\n🎉 DataStorage MVP 데이터베이스 마이그레이션 완료!")
        print("\n📋 생성된 구조:")
        print("   • commits: 커밋 정보 저장")
        print("   • commit_diffs: diff 정보 저장 (압축 지원)")
        print("   • events: 기존 호환성을 위한 이벤트 테이블")

        print("\n💡 사용법:")
        print("   from modules.data_storage.service import DataStorageManager")
        print("   manager = DataStorageManager()")
        print("   result = manager.store_commit(commit_data, diff_data)")

    except Exception as e:
        print(f"❌ 마이그레이션 실패: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
