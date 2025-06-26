"""
DiffAnalyzer 모듈 - 코드 변경사항 심층 분석

이 모듈은 GitDataParser에서 파싱된 diff 데이터를 받아 의미적 분석을 수행합니다.
코드 복잡도, 품질 메트릭, 구조적 변경사항을 분석하여 LLMService에서 활용할 수 있는
고품질 분석 데이터를 생성합니다.

주요 구성:
- DiffAnalyzer: 메인 분석 엔진
- LanguageAnalyzer: 언어별 분류 및 특화 분석
- CodeComplexityAnalyzer: 복잡도 분석
- StructuralChangeAnalyzer: AST 기반 구조적 변경 분석
"""

from .service import (
    DiffAnalyzer,
    LanguageAnalyzer, 
    CodeComplexityAnalyzer,
    StructuralChangeAnalyzer
)
from .models import (
    DiffAnalysisResult,
    LanguageClassificationResult,
    ComplexityAnalysisResult,
    StructuralAnalysisResult,
    AnalyzedFile,
    LanguageStats,
    FileAnalysis,
    ComplexityMetrics,
    StructuralChanges
)
from .exceptions import (
    DiffAnalyzerError,
    LanguageNotSupportedError,
    ComplexityAnalysisError,
    StructuralAnalysisError,
    ASTParsingError
)

__version__ = "1.0.0"
__author__ = "CodePing.AI Team"

__all__ = [
    # Services
    "DiffAnalyzer",
    "LanguageAnalyzer",
    "CodeComplexityAnalyzer", 
    "StructuralChangeAnalyzer",
    
    # Models
    "DiffAnalysisResult",
    "LanguageClassificationResult",
    "ComplexityAnalysisResult", 
    "StructuralAnalysisResult",
    "AnalyzedFile",
    "LanguageStats",
    "FileAnalysis",
    "ComplexityMetrics",
    "StructuralChanges",
    
    # Exceptions
    "DiffAnalyzerError",
    "LanguageNotSupportedError",
    "ComplexityAnalysisError",
    "StructuralAnalysisError",
    "ASTParsingError"
] 