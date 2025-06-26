"""
모듈별 입출력 로깅 유틸리티

각 모듈의 입력/출력 데이터를 상세하게 로깅하여 
전체 흐름을 추적할 수 있도록 합니다.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union
from types import MappingProxyType

# 모듈 흐름 추적을 위한 전용 로거
flow_logger = logging.getLogger("module_flow")
flow_logger.setLevel(logging.INFO)

# 각 모듈별 로거
module_loggers = {
    "WebhookReceiver": logging.getLogger("modules.webhook_receiver"),
    "HTTPAPIClient": logging.getLogger("modules.http_api_client"),
    "GitDataParser": logging.getLogger("modules.git_data_parser"),
    "DiffAnalyzer": logging.getLogger("modules.diff_analyzer"),
    "DataStorage": logging.getLogger("modules.data_storage"),
    "NotionSync": logging.getLogger("modules.notion_sync"),
}


def setup_detailed_logging():
    """상세한 로깅 설정"""
    
    # 전체 로깅 포맷 설정
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Flow 로거 설정 (모듈 흐름 추적용)
    flow_formatter = logging.Formatter(
        '🔄 %(asctime)s - FLOW - %(message)s',
        datefmt='%H:%M:%S'
    )
    flow_handler = logging.StreamHandler()
    flow_handler.setFormatter(flow_formatter)
    flow_logger.addHandler(flow_handler)
    flow_logger.propagate = False
    
    # 각 모듈 로거 설정
    for module_name, logger in module_loggers.items():
        logger.setLevel(logging.INFO)
        module_formatter = logging.Formatter(
            f'📦 %(asctime)s - {module_name} - %(levelname)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        module_handler = logging.StreamHandler()
        module_handler.setFormatter(module_formatter)
        logger.addHandler(module_handler)
        logger.propagate = False


class ModuleIOLogger:
    """모듈별 입출력 로깅 클래스"""
    
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.logger = module_loggers.get(module_name, logging.getLogger(f"modules.{module_name.lower()}"))
        self.start_time = None
        
    def log_input(self, operation: str, data: Any = None, metadata: Dict = None):
        """모듈 입력 데이터 로깅"""
        self.start_time = time.time()
        
        # 입력 데이터 요약
        input_summary = self._summarize_data(data, max_items=5)
        
        self.logger.info(f"🔵 INPUT  | {operation}")
        if input_summary:
            self.logger.info(f"📥 Data   | {input_summary}")
        if metadata:
            self.logger.info(f"ℹ️  Meta   | {metadata}")
            
        # Flow 로거에도 기록
        log_module_io(
            self.module_name, 
            f"{operation}_INPUT", 
            input_data=data, 
            metadata=metadata
        )
    
    def log_output(self, operation: str, data: Any = None, metadata: Dict = None):
        """모듈 출력 데이터 로깅"""
        
        # 실행 시간 계산
        duration = time.time() - self.start_time if self.start_time else 0
        
        # 출력 데이터 요약
        output_summary = self._summarize_data(data, max_items=5)
        
        self.logger.info(f"🟢 OUTPUT | {operation} (⏱️ {duration:.3f}s)")
        if output_summary:
            self.logger.info(f"📤 Result | {output_summary}")
        if metadata:
            self.logger.info(f"ℹ️  Meta   | {metadata}")
            
        # Flow 로거에도 기록
        log_module_io(
            self.module_name, 
            f"{operation}_OUTPUT", 
            output_data=data, 
            metadata={**(metadata or {}), "duration_seconds": duration}
        )
    
    def log_error(self, operation: str, error: Exception, metadata: Dict = None):
        """모듈 오류 로깅"""
        duration = time.time() - self.start_time if self.start_time else 0
        
        self.logger.error(f"🔴 ERROR  | {operation} (⏱️ {duration:.3f}s)")
        self.logger.error(f"❌ Error  | {type(error).__name__}: {str(error)}")
        if metadata:
            self.logger.error(f"ℹ️  Meta   | {metadata}")
            
        # Flow 로거에도 기록
        log_module_io(
            self.module_name, 
            f"{operation}_ERROR", 
            metadata={
                **(metadata or {}), 
                "error_type": type(error).__name__,
                "error_message": str(error),
                "duration_seconds": duration
            }
        )
    
    def _summarize_data(self, data: Any, max_items: int = 5) -> str:
        """데이터 요약 생성"""
        if data is None:
            return "None"
        
        try:
            if isinstance(data, dict):
                keys = list(data.keys())[:max_items]
                more = f" (+{len(data) - max_items} more)" if len(data) > max_items else ""
                return f"Dict[{', '.join(keys)}{more}]"
            
            elif isinstance(data, list):
                length = len(data)
                if length == 0:
                    return "List[empty]"
                elif length <= max_items:
                    return f"List[{length} items]"
                else:
                    return f"List[{length} items: {max_items} shown + {length - max_items} more]"
            
            elif hasattr(data, '__dict__'):
                # Pydantic 모델이나 dataclass
                attrs = list(data.__dict__.keys())[:max_items]
                more = f" (+{len(data.__dict__) - max_items} more)" if len(data.__dict__) > max_items else ""
                return f"{type(data).__name__}[{', '.join(attrs)}{more}]"
            
            elif isinstance(data, str):
                return f"String[{len(data)} chars]" if len(data) > 50 else f"'{data[:50]}...'"
            
            elif isinstance(data, bytes):
                return f"Bytes[{len(data)} bytes]"
            
            else:
                return f"{type(data).__name__}[{str(data)[:100]}...]"
                
        except Exception:
            return f"{type(data).__name__}[summary failed]"


def default_json_serializer(obj):
    """JSON 직렬화를 위한 기본 시리얼라이저"""
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


def simplify_data(data: Any, max_depth: int = 3, current_depth: int = 0) -> Any:
    """
    복잡한 데이터 구조를 로깅하기 쉽게 단순화
    """
    try:
        if current_depth >= max_depth:
            return f"<depth_limit_reached: {type(data).__name__}>"
        
        if isinstance(data, dict):
            simplified = {}
            for key, value in data.items():
                try:
                    if isinstance(key, str) and len(key) > 50:
                        key = key[:47] + "..."
                    simplified[key] = simplify_data(value, max_depth, current_depth + 1)
                except Exception as e:
                    simplified[key] = f"<simplify_error: {type(e).__name__}>"
            return simplified
        
        elif isinstance(data, list):
            try:
                if len(data) > 10:  # 리스트가 너무 길면 처음 10개만 표시
                    return [simplify_data(item, max_depth, current_depth + 1) for item in data[:10]] + [f"... (+{len(data) - 10} more items)"]
                return [simplify_data(item, max_depth, current_depth + 1) for item in data]
            except Exception:
                return f"<list_simplify_error: {len(data)} items>"
        
        elif isinstance(data, str):
            if len(data) > 200:
                return data[:197] + "..."
            return data
        
        elif isinstance(data, bytes):
            if len(data) > 1000:
                return f"<bytes: {len(data)} bytes>"
            return data
        
        elif hasattr(data, '__dict__'):
            try:
                obj_dict = data.__dict__
                if isinstance(obj_dict, dict):
                    simplified_dict = simplify_data(obj_dict, max_depth, current_depth + 1)
                    if isinstance(simplified_dict, dict):
                        return {
                            "__type": type(data).__name__,
                            **simplified_dict
                        }
                    else:
                        return {
                            "__type": type(data).__name__,
                            "__dict_error": str(simplified_dict)
                        }
                else:
                    return {
                        "__type": type(data).__name__,
                        "__dict_not_dict": str(type(obj_dict).__name__)
                    }
            except Exception as e:
                return {
                    "__type": type(data).__name__,
                    "__dict_access_error": str(e)
                }
        
        # 기본 타입들은 그대로 반환
        elif isinstance(data, (int, float, bool, type(None))):
            return data
        
        # 기타 타입들은 문자열로 변환
        else:
            try:
                str_repr = str(data)
                if len(str_repr) > 200:
                    return str_repr[:197] + "..."
                return str_repr
            except Exception:
                return f"<{type(data).__name__}: repr_error>"
                
    except Exception as e:
        return f"<simplify_error: {type(e).__name__}: {str(e)}>"


def log_module_io(
    module_name: str, 
    operation: str, 
    input_data: Any = None, 
    output_data: Any = None, 
    metadata: Dict = None
):
    """모듈별 입력/출력 데이터 로깅 (기존 함수 호환성 유지)"""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "module": module_name,
        "operation": operation,
        "input": simplify_data(input_data) if input_data is not None else None,
        "output": simplify_data(output_data) if output_data is not None else None,
        "metadata": metadata or {}
    }
    
    flow_logger.info(
        "MODULE_FLOW: %s", 
        json.dumps(log_entry, ensure_ascii=False, indent=2, default=default_json_serializer)
    )


def log_processing_chain_start(payload: Dict, headers: Dict):
    """전체 처리 체인 시작 로깅"""
    flow_logger.info("=" * 80)
    flow_logger.info("🚀 PROCESSING CHAIN STARTED")
    flow_logger.info("=" * 80)
    
    log_module_io(
        "PROCESSING_CHAIN", 
        "START",
        input_data={
            "payload_keys": list(payload.keys()), 
            "headers": list(headers.keys())
        },
        metadata={
            "repository": payload.get("repository", {}).get("full_name", "unknown"),
            "commits_count": len(payload.get("commits", [])),
            "ref": payload.get("ref", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    )


def log_processing_chain_end(success: bool, metadata: Dict = None):
    """전체 처리 체인 완료 로깅"""
    status = "COMPLETED" if success else "FAILED"
    icon = "🎉" if success else "❌"
    
    flow_logger.info(f"{icon} PROCESSING CHAIN {status}")
    flow_logger.info("=" * 80)
    
    log_module_io(
        "PROCESSING_CHAIN", 
        status,
        metadata=metadata or {}
    ) 