"""
DiffAnalyzer 모듈 데이터 모델

모듈 간 인터페이스와 내부 데이터 구조를 정의합니다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class ImpactLevel(Enum):
    """복잡도 변화 영향도 수준"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeType(Enum):
    """변경 유형"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class FileType(Enum):
    """파일 타입"""
    SOURCE_CODE = "source_code"
    TEST_FILE = "test_file"
    CONFIG_FILE = "config_file"
    DOCUMENTATION = "documentation"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass
class ComplexityMetrics:
    """복잡도 메트릭"""
    complexity_before: float = 0.0
    complexity_after: float = 0.0
    complexity_delta: float = 0.0
    impact_level: ImpactLevel = ImpactLevel.LOW
    
    # 세부 메트릭
    cyclomatic_complexity: Optional[float] = None
    cognitive_complexity: Optional[float] = None
    maintainability_index: Optional[float] = None
    lines_of_code: Optional[int] = None


@dataclass
class StructuralChanges:
    """구조적 변경사항"""
    functions_added: List[str] = field(default_factory=list)
    functions_modified: List[str] = field(default_factory=list)
    functions_deleted: List[str] = field(default_factory=list)
    classes_added: List[str] = field(default_factory=list)
    classes_modified: List[str] = field(default_factory=list)
    classes_deleted: List[str] = field(default_factory=list)
    imports_added: List[str] = field(default_factory=list)
    imports_removed: List[str] = field(default_factory=list)
    imports_changed: List[str] = field(default_factory=list)
    is_test_file: bool = False
    
    # 추가 구조적 정보
    decorators_changed: List[str] = field(default_factory=list)
    docstrings_changed: List[str] = field(default_factory=list)
    type_annotations_changed: List[str] = field(default_factory=list)


@dataclass
class LanguageStats:
    """언어별 통계"""
    language: str
    file_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    complexity_delta: float = 0.0
    functions_changed: int = 0
    classes_changed: int = 0


class FileAnalysis(BaseModel):
    """파일별 분석 결과"""
    file_path: str
    language: str
    file_type: FileType
    change_type: ChangeType
    
    # 기본 통계
    lines_added: int = 0
    lines_deleted: int = 0
    lines_modified: int = 0
    
    # 복잡도 분석
    complexity_metrics: Optional[ComplexityMetrics] = None
    
    # 구조적 변경
    structural_changes: Optional[StructuralChanges] = None
    
    # 품질 지표
    test_coverage_impact: Optional[float] = None
    code_quality_impact: Optional[float] = None
    
    # 원본 데이터 참조
    patch_content: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class AnalyzedFile(BaseModel):
    """분석된 파일 정보 (간소화된 버전)"""
    file_path: str
    language: str
    file_type: FileType
    change_type: ChangeType
    lines_added: int = 0
    lines_deleted: int = 0
    complexity_delta: float = 0.0
    functions_changed: int = 0
    classes_changed: int = 0
    
    model_config = ConfigDict(from_attributes=True)


class LanguageClassificationResult(BaseModel):
    """언어별 분류 결과"""
    language_groups: Dict[str, List[Any]] = Field(default_factory=dict)
    supported_files: List[Any] = Field(default_factory=list)
    unsupported_files: List[Any] = Field(default_factory=list)
    language_stats: Dict[str, LanguageStats] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class ComplexityAnalysisResult(BaseModel):
    """복잡도 분석 결과"""
    file_path: str
    language: str
    metrics: ComplexityMetrics
    analysis_success: bool = True
    error_message: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class StructuralAnalysisResult(BaseModel):
    """구조적 분석 결과"""
    file_path: str
    language: str
    changes: StructuralChanges
    analysis_success: bool = True
    error_message: Optional[str] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class DiffAnalysisResult(BaseModel):
    """DiffAnalyzer 모듈의 최종 출력 데이터 모델"""
    
    # 메타데이터
    commit_sha: str
    repository_name: str
    author_email: str
    timestamp: datetime
    
    # 파일 변경 통계
    total_files_changed: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    
    # 언어별 분석
    language_breakdown: Dict[str, LanguageStats] = Field(default_factory=dict)
    
    # 구조적 변경사항 요약
    functions_added: List[str] = Field(default_factory=list)
    functions_modified: List[str] = Field(default_factory=list)
    functions_deleted: List[str] = Field(default_factory=list)
    classes_added: List[str] = Field(default_factory=list)
    classes_modified: List[str] = Field(default_factory=list)
    classes_deleted: List[str] = Field(default_factory=list)
    
    # 품질 메트릭
    complexity_delta: float = 0.0
    test_coverage_delta: float = 0.0
    maintainability_impact: Optional[float] = None
    
    # 파일별 상세 분석
    analyzed_files: List[AnalyzedFile] = Field(default_factory=list)
    
    # 바이너리 파일 변경
    binary_files_changed: List[str] = Field(default_factory=list)
    
    # 분석 메타데이터
    analysis_duration_seconds: float = 0.0
    supported_languages: List[str] = Field(default_factory=list)
    unsupported_files_count: int = 0
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )
    
    def get_summary(self) -> Dict[str, Any]:
        """분석 결과 요약 정보 반환"""
        return {
            "commit_info": {
                "sha": self.commit_sha,
                "repository": self.repository_name,
                "author": self.author_email,
                "timestamp": self.timestamp.isoformat()
            },
            "change_summary": {
                "files_changed": self.total_files_changed,
                "lines_added": self.total_additions,
                "lines_deleted": self.total_deletions,
                "net_change": self.total_additions - self.total_deletions
            },
            "structural_summary": {
                "functions_total_changed": len(self.functions_added) + len(self.functions_modified) + len(self.functions_deleted),
                "classes_total_changed": len(self.classes_added) + len(self.classes_modified) + len(self.classes_deleted),
                "complexity_impact": self.complexity_delta
            },
            "language_summary": {
                "languages_affected": list(self.language_breakdown.keys()),
                "primary_language": max(self.language_breakdown.keys(), 
                                      key=lambda k: self.language_breakdown[k].lines_added + self.language_breakdown[k].lines_deleted,
                                      default="unknown") if self.language_breakdown else "unknown"
            },
            "quality_impact": {
                "complexity_delta": self.complexity_delta,
                "test_coverage_delta": self.test_coverage_delta,
                "maintainability_impact": self.maintainability_impact
            }
        }


# Input 데이터 모델 (GitDataParser에서 받는 데이터)
class ParsedDiff(BaseModel):
    """GitDataParser에서 전달받는 파싱된 diff 데이터"""
    repository_name: str
    commit_sha: str
    file_changes: List[Any]  # FileChange 객체들
    diff_stats: Any  # DiffStats 객체
    
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class CommitMetadata(BaseModel):
    """커밋 메타데이터"""
    sha: str
    message: str
    author_name: str
    author_email: str
    timestamp: datetime
    repository_name: str
    branch_name: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class RepositoryContext(BaseModel):
    """저장소 컨텍스트 정보 (선택적)"""
    repository_name: str
    default_branch: str = "main"
    primary_language: Optional[str] = None
    project_type: Optional[str] = None  # web, library, cli, etc.
    frameworks: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True) 