"""Celery tasks for webhook async processing."""

from __future__ import annotations

import logging
import json
from typing import Any, Dict
from datetime import datetime
from types import MappingProxyType

from celery import shared_task

from modules.git_data_parser.service import GitDataParserService
from modules.http_api_client.client import HTTPAPIClient
from modules.http_api_client.models import Platform
from modules.diff_analyzer.service import DiffAnalyzer
from modules.data_storage.service import LegacyDataStorageService
from shared.config.settings import get_settings
from shared.utils.logging import (
    log_module_io, log_processing_chain_start, log_processing_chain_end,
    default_json_serializer, simplify_data
)

logger = logging.getLogger(__name__)

# 모듈별 데이터 흐름 추적을 위한 전용 로거 (호환성 유지)
flow_logger = logging.getLogger("module_flow")
flow_logger.setLevel(logging.INFO)


def default_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return obj.__dict__
    elif isinstance(obj, set):
        return list(obj)
    elif isinstance(obj, MappingProxyType):
        return dict(obj)
    elif isinstance(obj, (type(lambda: None), type(len))):  # Handle function or method
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def remove_circular_references(data, seen=None):
    if seen is None:
        seen = set()

    if id(data) in seen:
        return "<Circular Reference>"

    seen.add(id(data))

    if isinstance(data, dict):
        return {key: remove_circular_references(value, seen) for key, value in data.items()}
    elif isinstance(data, list):
        return [remove_circular_references(item, seen) for item in data]
    elif isinstance(data, tuple):
        return tuple(remove_circular_references(item, seen) for item in data)
    elif isinstance(data, set):
        return {remove_circular_references(item, seen) for item in data}

    return data


def simplify_data(data):
    if isinstance(data, dict):
        return {key: simplify_data(value) for key, value in data.items() if isinstance(value, (str, int, float, bool, type(None)))}
    elif isinstance(data, list):
        return [simplify_data(item) for item in data if isinstance(item, (str, int, float, bool, type(None)))]
    elif isinstance(data, tuple):
        return tuple(simplify_data(item) for item in data if isinstance(item, (str, int, float, bool, type(None))))
    elif isinstance(data, set):
        return {simplify_data(item) for item in data if isinstance(item, (str, int, float, bool, type(None)))}
    return data


def log_module_io(module_name: str, operation: str, input_data: Any = None, output_data: Any = None, metadata: Dict = None):
    """모듈별 입력/출력 데이터 로깅"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "module": module_name,
        "operation": operation,
        "input": input_data,
        "output": output_data,
        "metadata": metadata or {}
    }
    log_entry = simplify_data(log_entry)
    flow_logger.info("MODULE_FLOW: %s", json.dumps(log_entry, ensure_ascii=False, indent=2, default=default_json_serializer))


@shared_task(name="webhook_receiver.process_webhook_async")
def process_webhook_async(payload: Dict[str, Any], headers: Dict[str, str]) -> None:
    """
    Background task for processing webhook data following specification architecture.
    
    Processing Flow (기획서 준수):
    1. WebhookReceiver: webhook payload 수신 및 검증 (완료)
    2. HTTPAPIClient: 필요시 diff 내용 추가 수집 (API 호출 전담)
    3. GitDataParser: webhook payload 파싱 및 구조화
    4. DiffAnalyzer: 심층 코드 분석 
    5. DataStorage: DB/S3 저장 결과
    """
    
    processing_start = datetime.now()
    
    try:
        logger.info("🚀 Starting specification-compliant module processing chain")
        
        # 📊 전체 처리 시작 로깅 (새로운 시스템)
        log_processing_chain_start(payload, headers)
        
        # 2️⃣ HTTPAPIClient: diff 내용 추가 수집 (API 호출 전담)
        logger.info("🌐 HTTPAPIClient: Starting diff content collection via API")
        
        github_token = get_settings().github_token
        diff_data = None
        
        if github_token:
            log_module_io("HTTPAPIClient", "INPUT", input_data=payload, metadata={
                "operation": "get_commit_diff",
                "repository": payload.get("repository", {}).get("full_name", "unknown"),
                "commits_count": len(payload.get("commits", [])),
                "has_token": bool(github_token)
            })
            
            try:
                # HTTPAPIClient 직접 사용
                http_client = HTTPAPIClient(Platform.GITHUB, github_token)
                
                repository = payload.get("repository", {}).get("full_name", "")
                commits = payload.get("commits", [])
                
                if repository and commits:
                    # 첫 번째 커밋의 diff 정보 가져오기
                    commit_sha = commits[0].get("id", "")
                    if commit_sha:
                        # GitHub API로 커밋 정보 조회
                        commit_response = http_client.get_commit(repository, commit_sha)
                        
                        if commit_response.success and commit_response.data:
                            commit_data = commit_response.data
                            
                            # diff 데이터 구성
                            from modules.git_data_parser.models import DiffData
                            diff_data = DiffData(
                                commit_sha=commit_sha,
                                repository=repository,
                                diff_content=b"",  # GitHub API에서는 patch 형태로 제공
                                added_lines=commit_data.get("stats", {}).get("additions", 0),
                                deleted_lines=commit_data.get("stats", {}).get("deletions", 0),
                                files_changed=len(commit_data.get("files", []))
                            )
                            
                            # patch 내용이 있으면 추가
                            files = commit_data.get("files", [])
                            if files:
                                patch_content = ""
                                for file_info in files:
                                    if file_info.get("patch"):
                                        patch_content += f"--- a/{file_info.get('filename', '')}\n"
                                        patch_content += f"+++ b/{file_info.get('filename', '')}\n"
                                        patch_content += file_info.get("patch", "") + "\n"
                                
                                if patch_content:
                                    diff_data.diff_content = patch_content.encode('utf-8')
                
                http_client.close()
                
                log_module_io("HTTPAPIClient", "OUTPUT", output_data=diff_data, metadata={
                    "diff_content_size": len(diff_data.diff_content) if diff_data and diff_data.diff_content else 0,
                    "files_changed": diff_data.files_changed if diff_data else 0,
                    "added_lines": diff_data.added_lines if diff_data else 0,
                    "deleted_lines": diff_data.deleted_lines if diff_data else 0,
                    "api_call_success": True
                })
                
                logger.info(
                    "✅ HTTPAPIClient: Completed diff collection - %d bytes, %d lines (+%d/-%d)",
                    len(diff_data.diff_content) if diff_data and diff_data.diff_content else 0,
                    diff_data.files_changed if diff_data else 0,
                    diff_data.added_lines if diff_data else 0,
                    diff_data.deleted_lines if diff_data else 0
                )
                
            except Exception as exc:
                log_module_io("HTTPAPIClient", "ERROR", metadata={
                    "error": str(exc),
                    "operation": "get_commit_diff"
                })
                logger.warning("⚠️ HTTPAPIClient: API call failed, continuing with basic data: %s", exc)
                diff_data = None
        else:
            logger.info("⏭️ HTTPAPIClient: Skipped (no GitHub token)")
            log_module_io("HTTPAPIClient", "SKIPPED", metadata={
                "reason": "no_github_token",
                "has_token": bool(github_token)
            })
        
        # 3️⃣ GitDataParser: webhook payload 파싱 및 구조화
        logger.info("📊 GitDataParser: Starting webhook payload parsing")
        
        log_module_io("GitDataParser", "INPUT", input_data=payload, metadata={
            "operation": "parse_webhook_data",
            "payload_size": len(json.dumps(payload).encode()),
            "headers_count": len(headers),
            "has_diff_data": diff_data is not None
        })
        
        git_parser = GitDataParserService()
        parsed_data = git_parser.parse_webhook_data(payload, headers)
        
        # HTTPAPIClient에서 가져온 실제 라인 수 정보로 업데이트
        if diff_data and (diff_data.added_lines or diff_data.deleted_lines):
            parsed_data.diff_stats.total_additions = diff_data.added_lines or 0
            parsed_data.diff_stats.total_deletions = diff_data.deleted_lines or 0
            parsed_data.diff_stats.files_changed = diff_data.files_changed or parsed_data.diff_stats.files_changed
        
        log_module_io("GitDataParser", "OUTPUT", output_data=parsed_data, metadata={
            "commits_parsed": len(parsed_data.commits),
            "files_changed": parsed_data.diff_stats.files_changed,
            "total_additions": parsed_data.diff_stats.total_additions,
            "total_deletions": parsed_data.diff_stats.total_deletions,
            "repository": parsed_data.repository,
            "enhanced_with_api_data": diff_data is not None
        })
        
        logger.info(
            "✅ GitDataParser: Completed parsing - repo=%s, commits=%d, files=%d (+%d/-%d)",
            parsed_data.repository,
            len(parsed_data.commits),
            parsed_data.diff_stats.files_changed,
            parsed_data.diff_stats.total_additions,
            parsed_data.diff_stats.total_deletions
        )
        
        # 4️⃣ DiffAnalyzer: 심층 코드 분석
        logger.info("🧮 DiffAnalyzer: Starting deep code analysis")
        
        log_module_io("DiffAnalyzer", "INPUT", input_data=parsed_data, metadata={
            "operation": "analyze_webhook_data",
            "file_changes_count": len(parsed_data.file_changes),
            "commits_count": len(parsed_data.commits)
        })
        
        diff_analyzer = DiffAnalyzer()
        analysis_result = diff_analyzer.analyze_webhook_data(parsed_data)
        
        log_module_io("DiffAnalyzer", "OUTPUT", output_data=analysis_result, metadata={
            "complexity_delta": analysis_result.complexity_delta,
            "supported_languages": list(analysis_result.supported_languages),
            "total_files_changed": analysis_result.total_files_changed,
            "analysis_duration": analysis_result.analysis_duration_seconds,
            "language_breakdown": dict(analysis_result.language_breakdown)
        })
        
        logger.info(
            "✅ DiffAnalyzer: Completed analysis - complexity_delta=%+.2f, languages=%s, duration=%.3fs",
            analysis_result.complexity_delta,
            list(analysis_result.language_breakdown.keys()),
            analysis_result.analysis_duration_seconds
        )
        
        # Check if we're in test mode (WebhookReceiver only)
        settings = get_settings()
        if getattr(settings, 'webhook_test_mode', False):
            log_module_io("PROCESSING_CHAIN", "TEST_MODE_END", metadata={
                "total_duration": (datetime.now() - processing_start).total_seconds(),
                "modules_completed": ["HTTPAPIClient", "GitDataParser", "DiffAnalyzer"],
                "specification_compliant": True
            })
            
            logger.info(
                "🧪 TEST MODE: Specification-compliant module processing completed without storage"
            )
            logger.info(
                "📈 Analysis Summary: repo=%s, files=%d, complexity=%+.2f, languages=%d",
                parsed_data.repository,
                analysis_result.total_files_changed,
                analysis_result.complexity_delta,
                len(analysis_result.supported_languages)
            )
            return
        
        # 5️⃣ DataStorage: DB/S3 저장 결과
        logger.info("💾 DataStorage: Starting storage operations")
        
        # 저장용 데이터 준비: HTTPAPIClient 결과 우선 사용
        storage_diff_data = diff_data
        if not storage_diff_data:
            # diff_data 없이도 기본 정보는 저장 가능
            logger.info("💾 DataStorage: Storing basic webhook data without detailed diff")
            
            # 기본 DiffData 객체 생성
            from modules.git_data_parser.models import DiffData
            storage_diff_data = DiffData(
                commit_sha=payload.get("after", "unknown"),
                repository=parsed_data.repository,
                diff_content=b"",
                added_lines=parsed_data.diff_stats.total_additions,
                deleted_lines=parsed_data.diff_stats.total_deletions,
                files_changed=parsed_data.diff_stats.files_changed
            )
        
        log_module_io("DataStorage", "INPUT", input_data=storage_diff_data, metadata={
            "operation": "store_event_with_diff",
            "storage_type": "with_api_diff" if diff_data else "basic_webhook_data",
            "diff_size": len(storage_diff_data.diff_content) if storage_diff_data.diff_content else 0
        })
        
        storage_service = LegacyDataStorageService()
        storage_service.store_event_with_diff(payload, headers, storage_diff_data)
        
        log_module_io("DataStorage", "OUTPUT", metadata={
            "operation": "store_event_with_diff",
            "storage_completed": True
        })
        
        logger.info(
            "✅ DataStorage: Storage completed"
        )
        
        # 전체 처리 완료 (새로운 시스템)
        total_duration = (datetime.now() - processing_start).total_seconds()
        
        log_processing_chain_end(True, metadata={
            "total_duration_seconds": total_duration,
            "modules_executed": ["HTTPAPIClient", "GitDataParser", "DiffAnalyzer", "DataStorage"],
            "repository": parsed_data.repository,
            "files_changed": analysis_result.total_files_changed,
            "complexity_delta": analysis_result.complexity_delta,
            "languages": list(analysis_result.language_breakdown.keys()),
            "specification_compliant": True
        })
        
        logger.info(
            "🎉 Specification-compliant module processing chain completed successfully: "
            "repo=%s, files=%d (+%d/-%d), complexity=%+.2f, analysis_time=%.3fs",
            parsed_data.repository,
            analysis_result.total_files_changed,
            parsed_data.diff_stats.total_additions,
            parsed_data.diff_stats.total_deletions,
            analysis_result.complexity_delta,
            analysis_result.analysis_duration_seconds
        )
        
    except Exception as exc:
        log_module_io("PROCESSING_CHAIN", "ERROR", metadata={
            "error": str(exc),
            "error_type": type(exc).__name__,
            "total_duration": (datetime.now() - processing_start).total_seconds(),
            "specification_compliant": True
        })
        
        logger.exception("❌ Specification-compliant module processing chain failed: %s", exc) 