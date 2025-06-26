"""
DiffAnalyzer 모듈 예외 정의

모듈별 구체적인 예외를 정의하여 정확한 오류 처리와 디버깅을 지원합니다.
"""

from typing import Optional, Dict, List, Any


class DiffAnalyzerError(Exception):
    """DiffAnalyzer 모듈의 기본 예외 클래스"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class LanguageNotSupportedError(DiffAnalyzerError):
    """지원하지 않는 프로그래밍 언어 오류"""
    
    def __init__(self, language: str, supported_languages: Optional[List[str]] = None):
        message = f"Language '{language}' is not supported for analysis"
        details = {
            "language": language,
            "supported_languages": supported_languages or []
        }
        super().__init__(message, details)
        self.language = language
        self.supported_languages = supported_languages


class ComplexityAnalysisError(DiffAnalyzerError):
    """코드 복잡도 분석 오류"""
    
    def __init__(self, message: str, file_path: Optional[str] = None, 
                 language: Optional[str] = None, code_size: Optional[int] = None):
        details = {
            "file_path": file_path,
            "language": language,
            "code_size": code_size
        }
        super().__init__(message, details)
        self.file_path = file_path
        self.language = language


class StructuralAnalysisError(DiffAnalyzerError):
    """구조적 변경사항 분석 오류"""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 analysis_type: Optional[str] = None):
        details = {
            "file_path": file_path,
            "analysis_type": analysis_type
        }
        super().__init__(message, details)
        self.file_path = file_path
        self.analysis_type = analysis_type


class ASTParsingError(DiffAnalyzerError):
    """AST 파싱 오류"""
    
    def __init__(self, message: str, file_path: Optional[str] = None,
                 language: Optional[str] = None, syntax_error: Optional[str] = None):
        details = {
            "file_path": file_path,
            "language": language,
            "syntax_error": syntax_error
        }
        super().__init__(message, details)
        self.file_path = file_path
        self.language = language
        self.syntax_error = syntax_error


class BinaryFileAnalysisError(DiffAnalyzerError):
    """바이너리 파일 분석 오류"""
    
    def __init__(self, file_path: str, file_size: Optional[int] = None):
        message = f"Cannot analyze binary file: {file_path}"
        details = {
            "file_path": file_path,
            "file_size": file_size,
            "file_type": "binary"
        }
        super().__init__(message, details)
        self.file_path = file_path


class LargeFileAnalysisError(DiffAnalyzerError):
    """대용량 파일 분석 제한 오류"""
    
    def __init__(self, file_path: str, file_size: int, max_size: int):
        message = f"File too large for analysis: {file_path} ({file_size} bytes, max: {max_size})"
        details = {
            "file_path": file_path,
            "file_size": file_size,
            "max_size": max_size
        }
        super().__init__(message, details)
        self.file_path = file_path
        self.file_size = file_size
        self.max_size = max_size


class DependencyAnalysisError(DiffAnalyzerError):
    """의존성 분석 오류"""
    
    def __init__(self, message: str, dependency_type: Optional[str] = None,
                 missing_dependencies: Optional[List[str]] = None):
        details = {
            "dependency_type": dependency_type,
            "missing_dependencies": missing_dependencies or []
        }
        super().__init__(message, details)
        self.dependency_type = dependency_type
        self.missing_dependencies = missing_dependencies 