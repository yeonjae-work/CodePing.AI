"""
DiffAnalyzer 모듈 서비스 레이어

GitDataParser에서 파싱된 diff 데이터를 받아 코드 변경사항을 심층 분석합니다.
"""

from __future__ import annotations

import ast
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    import tree_sitter_python as tspython
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

try:
    import radon.complexity as radon_complexity
    from radon.metrics import mi_visit
    RADON_AVAILABLE = True
except ImportError:
    RADON_AVAILABLE = False

try:
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False

from .models import (
    DiffAnalysisResult, LanguageClassificationResult, ComplexityAnalysisResult,
    StructuralAnalysisResult, AnalyzedFile, LanguageStats, FileAnalysis,
    ComplexityMetrics, StructuralChanges, ParsedDiff, CommitMetadata,
    RepositoryContext, ImpactLevel, ChangeType, FileType
)
from .exceptions import (
    DiffAnalyzerError, LanguageNotSupportedError, ComplexityAnalysisError,
    StructuralAnalysisError, ASTParsingError, BinaryFileAnalysisError,
    LargeFileAnalysisError
)
from shared.utils.logging import ModuleIOLogger

logger = logging.getLogger(__name__)


class LanguageAnalyzer:
    """언어별 분류 및 특화 분석을 담당하는 헬퍼 클래스"""
    
    # 지원 언어 매핑
    LANGUAGE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.cpp': 'cpp',
        '.cc': 'cpp',
        '.cxx': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.sh': 'shell',
        '.bash': 'shell',
        '.zsh': 'shell',
        '.html': 'html',
        '.htm': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.sass': 'sass',
        '.less': 'less',
        '.sql': 'sql',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.toml': 'toml',
        '.md': 'markdown',
        '.rst': 'restructuredtext',
        '.txt': 'text'
    }
    
    # 분석 지원 언어 (복잡도/구조 분석 가능)
    ANALYSIS_SUPPORTED_LANGUAGES = {
        'python', 'javascript', 'typescript', 'java', 'cpp', 'c', 'csharp',
        'go', 'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala'
    }
    
    # 테스트 파일 패턴
    TEST_FILE_PATTERNS = [
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'.*\.test\.js$',
        r'.*\.spec\.js$',
        r'.*Test\.java$',
        r'test/.*',
        r'tests/.*',
        r'__tests__/.*',
        r'spec/.*'
    ]
    
    def __init__(self):
        self.test_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.TEST_FILE_PATTERNS]
    
    def classify_by_language(self, file_changes: List[Any]) -> LanguageClassificationResult:
        """파일 변경사항을 언어별로 분류"""
        language_groups: Dict[str, List[Any]] = {}
        supported_files: List[Any] = []
        unsupported_files: List[Any] = []
        language_stats: Dict[str, LanguageStats] = {}
        
        for file_change in file_changes:
            language = self._detect_language(file_change.filename)
            
            # 언어별 그룹화
            if language not in language_groups:
                language_groups[language] = []
                language_stats[language] = LanguageStats(language=language)
            
            language_groups[language].append(file_change)
            
            # 통계 업데이트
            stats = language_stats[language]
            stats.file_count += 1
            stats.lines_added += getattr(file_change, 'additions', 0)
            stats.lines_deleted += getattr(file_change, 'deletions', 0)
            
            # 지원 여부 분류
            if self._is_supported_language(language):
                supported_files.append(file_change)
            else:
                unsupported_files.append(file_change)
        
        return LanguageClassificationResult(
            language_groups=language_groups,
            supported_files=supported_files,
            unsupported_files=unsupported_files,
            language_stats=language_stats
        )
    
    def _detect_language(self, file_path: str) -> str:
        """파일 경로에서 언어 감지"""
        if not file_path:
            return 'unknown'
        
        path = Path(file_path)
        extension = path.suffix.lower()
        
        # 1차: 확장자 기반 감지
        language = self.LANGUAGE_EXTENSIONS.get(extension)
        if language:
            return language
        
        # 2차: 파일명 패턴 기반 감지
        filename_lower = path.name.lower()
        special_files = {
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            'rakefile': 'ruby',
            'gemfile': 'ruby',
            'package.json': 'json',
            'pyproject.toml': 'toml',
            'cargo.toml': 'toml'
        }
        
        if filename_lower in special_files:
            return special_files[filename_lower]
        
        return 'unknown'
    
    def _determine_file_type(self, file_path: str, language: str) -> FileType:
        """파일 타입 결정"""
        if not file_path:
            return FileType.UNKNOWN
        
        # 테스트 파일 확인
        for pattern in self.test_patterns:
            if pattern.search(file_path):
                return FileType.TEST_FILE
        
        # 설정 파일 확인
        config_files = {
            'json', 'yaml', 'toml', 'xml', 'ini',
            'dockerfile', 'makefile'
        }
        if language in config_files:
            return FileType.CONFIG_FILE
        
        # 문서 파일 확인
        doc_languages = {'markdown', 'restructuredtext', 'text'}
        if language in doc_languages:
            return FileType.DOCUMENTATION
        
        # 바이너리 파일 확인
        if self._is_binary_file(file_path):
            return FileType.BINARY
        
        # 기본적으로 소스 코드
        if language in self.ANALYSIS_SUPPORTED_LANGUAGES:
            return FileType.SOURCE_CODE
        
        return FileType.UNKNOWN
    
    def _is_supported_language(self, language: str) -> bool:
        """분석 지원 언어 여부 확인"""
        return language in self.ANALYSIS_SUPPORTED_LANGUAGES
    
    def _is_binary_file(self, file_path: str) -> bool:
        """바이너리 파일 여부 확인"""
        binary_extensions = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.tar', '.gz', '.bz2', '.rar', '.7z',
            '.exe', '.dll', '.so', '.dylib', '.a', '.lib',
            '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac'
        }
        
        extension = Path(file_path).suffix.lower()
        return extension in binary_extensions


class CodeComplexityAnalyzer:
    """코드 복잡도 분석을 담당하는 헬퍼 클래스"""
    
    def __init__(self):
        self.max_file_size = 1024 * 1024  # 1MB 제한
    
    def analyze_complexity(self, file_change: Any, language: str) -> ComplexityAnalysisResult:
        """파일 변경사항의 복잡도 분석"""
        try:
            # 파일 크기 검사
            patch_content = getattr(file_change, 'patch', '')
            if len(patch_content.encode('utf-8')) > self.max_file_size:
                raise LargeFileAnalysisError(
                    file_change.filename,
                    len(patch_content.encode('utf-8')),
                    self.max_file_size
                )
            
            # 언어별 복잡도 분석
            if language == 'python' and RADON_AVAILABLE:
                metrics = self._analyze_python_complexity(file_change)
            else:
                # 기본 복잡도 분석 (라인 기반)
                metrics = self._analyze_basic_complexity(file_change)
            
            return ComplexityAnalysisResult(
                file_path=file_change.filename,
                language=language,
                metrics=metrics,
                analysis_success=True
            )
            
        except Exception as e:
            logger.warning(f"Complexity analysis failed for {file_change.filename}: {e}")
            return ComplexityAnalysisResult(
                file_path=file_change.filename,
                language=language,
                metrics=ComplexityMetrics(),
                analysis_success=False,
                error_message=str(e)
            )
    
    def _analyze_python_complexity(self, file_change: Any) -> ComplexityMetrics:
        """Python 파일의 상세 복잡도 분석"""
        patch = getattr(file_change, 'patch', '')
        
        # 추가/삭제된 코드 추출
        added_lines = []
        deleted_lines = []
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                deleted_lines.append(line[1:])
        
        added_code = '\n'.join(added_lines)
        deleted_code = '\n'.join(deleted_lines)
        
        # 복잡도 계산
        complexity_before = self._calculate_python_complexity(deleted_code) if deleted_code.strip() else 0.0
        complexity_after = self._calculate_python_complexity(added_code) if added_code.strip() else 0.0
        complexity_delta = complexity_after - complexity_before
        
        # 영향도 계산
        impact_level = self._determine_impact_level(complexity_delta)
        
        return ComplexityMetrics(
            complexity_before=complexity_before,
            complexity_after=complexity_after,
            complexity_delta=complexity_delta,
            impact_level=impact_level,
            lines_of_code=len(added_lines) + len(deleted_lines)
        )
    
    def _calculate_python_complexity(self, code: str) -> float:
        """Python 코드의 복잡도 계산"""
        if not code.strip():
            return 0.0
        
        try:
            # radon을 사용한 복잡도 계산
            if RADON_AVAILABLE:
                complexity_results = radon_complexity.cc_visit(code)
                total_complexity = sum(result.complexity for result in complexity_results)
                
                # 평균 복잡도 계산
                function_count = len(complexity_results) or 1
                return total_complexity / function_count
            
        except Exception as e:
            logger.debug(f"Radon complexity calculation failed: {e}")
        
        # Fallback: AST 기반 간단한 복잡도 계산
        return self._calculate_ast_complexity(code)
    
    def _calculate_ast_complexity(self, code: str) -> float:
        """AST 기반 기본 복잡도 계산"""
        try:
            tree = ast.parse(code)
            complexity = 1  # 기본 복잡도
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, 
                                   ast.With, ast.AsyncWith, ast.AsyncFor)):
                    complexity += 1
                elif isinstance(node, ast.BoolOp):
                    complexity += len(node.values) - 1
                elif isinstance(node, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                    complexity += 1
                    
            return float(complexity)
            
        except SyntaxError:
            # 구문 오류가 있는 코드는 복잡도 1로 처리
            return 1.0
        except Exception:
            return 1.0
    
    def _analyze_basic_complexity(self, file_change: Any) -> ComplexityMetrics:
        """기본 복잡도 분석 (라인 기반)"""
        additions = getattr(file_change, 'additions', 0)
        deletions = getattr(file_change, 'deletions', 0)
        
        # 간단한 휴리스틱 기반 복잡도
        complexity_delta = (additions - deletions) * 0.1
        impact_level = self._determine_impact_level(abs(complexity_delta))
        
        return ComplexityMetrics(
            complexity_before=0.0,
            complexity_after=additions * 0.1,
            complexity_delta=complexity_delta,
            impact_level=impact_level,
            lines_of_code=additions + deletions
        )
    
    def _determine_impact_level(self, complexity_delta: float) -> ImpactLevel:
        """복잡도 변화량에 따른 영향도 결정"""
        abs_delta = abs(complexity_delta)
        
        if abs_delta >= 10:
            return ImpactLevel.CRITICAL
        elif abs_delta >= 5:
            return ImpactLevel.HIGH
        elif abs_delta >= 2:
            return ImpactLevel.MEDIUM
        else:
            return ImpactLevel.LOW


class StructuralChangeAnalyzer:
    """AST 기반 구조적 변경사항 분석을 담당하는 헬퍼 클래스"""
    
    def __init__(self):
        self.max_file_size = 512 * 1024  # 512KB 제한
    
    def analyze_structural_changes(self, file_change: Any, language: str) -> StructuralAnalysisResult:
        """구조적 변경사항 분석"""
        try:
            # 파일 크기 검사
            patch_content = getattr(file_change, 'patch', '')
            if len(patch_content.encode('utf-8')) > self.max_file_size:
                raise LargeFileAnalysisError(
                    file_change.filename,
                    len(patch_content.encode('utf-8')),
                    self.max_file_size
                )
            
            # 언어별 구조 분석
            if language == 'python':
                changes = self._analyze_python_structure(file_change)
            else:
                # 기본 구조 분석 (패턴 기반)
                changes = self._analyze_basic_structure(file_change, language)
            
            return StructuralAnalysisResult(
                file_path=file_change.filename,
                language=language,
                changes=changes,
                analysis_success=True
            )
            
        except Exception as e:
            logger.warning(f"Structural analysis failed for {file_change.filename}: {e}")
            return StructuralAnalysisResult(
                file_path=file_change.filename,
                language=language,
                changes=StructuralChanges(),
                analysis_success=False,
                error_message=str(e)
            )
    
    def _analyze_python_structure(self, file_change: Any) -> StructuralChanges:
        """Python 파일의 구조적 변경사항 분석"""
        patch = getattr(file_change, 'patch', '')
        
        changes = StructuralChanges()
        changes.is_test_file = self._is_test_file(file_change.filename)
        
        # 추가/삭제된 라인 추출
        added_lines = []
        deleted_lines = []
        
        for line in patch.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                added_lines.append(line[1:])
            elif line.startswith('-') and not line.startswith('---'):
                deleted_lines.append(line[1:])
        
        # AST 분석 (가능한 경우)
        if added_lines:
            added_code = '\n'.join(added_lines)
            self._extract_python_elements(added_code, changes, 'added')
        
        if deleted_lines:
            deleted_code = '\n'.join(deleted_lines)
            self._extract_python_elements(deleted_code, changes, 'deleted')
        
        # 패턴 기반 분석 (Fallback)
        all_lines = added_lines + deleted_lines
        self._analyze_python_patterns('\n'.join(all_lines), changes)
        
        return changes
    
    def _extract_python_elements(self, code: str, changes: StructuralChanges, change_type: str):
        """Python 코드에서 함수/클래스 추출"""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    if change_type == 'added':
                        changes.functions_added.append(func_name)
                    elif change_type == 'deleted':
                        changes.functions_deleted.append(func_name)
                
                elif isinstance(node, ast.ClassDef):
                    class_name = node.name
                    if change_type == 'added':
                        changes.classes_added.append(class_name)
                    elif change_type == 'deleted':
                        changes.classes_deleted.append(class_name)
                
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    import_info = self._extract_import_info(node)
                    if change_type == 'added':
                        changes.imports_added.extend(import_info)
                    elif change_type == 'deleted':
                        changes.imports_removed.extend(import_info)
                        
        except SyntaxError:
            # 부분 코드로 인한 구문 오류는 무시
            pass
        except Exception as e:
            logger.debug(f"AST parsing failed: {e}")
    
    def _extract_import_info(self, node: Union[ast.Import, ast.ImportFrom]) -> List[str]:
        """Import 정보 추출"""
        imports = []
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            for alias in node.names:
                imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return imports
    
    def _analyze_python_patterns(self, code: str, changes: StructuralChanges):
        """패턴 기반 Python 분석"""
        # 함수 정의 패턴
        func_pattern = re.compile(r'^\s*def\s+(\w+)\s*\(', re.MULTILINE)
        functions = func_pattern.findall(code)
        changes.functions_modified.extend(functions)
        
        # 클래스 정의 패턴
        class_pattern = re.compile(r'^\s*class\s+(\w+)\s*[\(:]', re.MULTILINE)
        classes = class_pattern.findall(code)
        changes.classes_modified.extend(classes)
        
        # Import 패턴
        import_pattern = re.compile(r'^\s*(import\s+[\w\.]+|from\s+[\w\.]+\s+import\s+[\w\.,\s]+)', re.MULTILINE)
        imports = import_pattern.findall(code)
        changes.imports_changed.extend(imports)
    
    def _analyze_basic_structure(self, file_change: Any, language: str) -> StructuralChanges:
        """기본 구조 분석 (패턴 기반)"""
        patch = getattr(file_change, 'patch', '')
        changes = StructuralChanges()
        changes.is_test_file = self._is_test_file(file_change.filename)
        
        # 언어별 기본 패턴
        patterns = self._get_language_patterns(language)
        
        for pattern_name, pattern in patterns.items():
            matches = pattern.findall(patch)
            if pattern_name == 'functions':
                changes.functions_modified.extend(matches)
            elif pattern_name == 'classes':
                changes.classes_modified.extend(matches)
            elif pattern_name == 'imports':
                changes.imports_changed.extend(matches)
        
        return changes
    
    def _get_language_patterns(self, language: str) -> Dict[str, re.Pattern]:
        """언어별 패턴 반환"""
        patterns = {}
        
        if language == 'javascript' or language == 'typescript':
            patterns['functions'] = re.compile(r'function\s+(\w+)\s*\(')
            patterns['classes'] = re.compile(r'class\s+(\w+)')
            patterns['imports'] = re.compile(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]')
        
        elif language == 'java':
            patterns['functions'] = re.compile(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(')
            patterns['classes'] = re.compile(r'(?:public|private)?\s*class\s+(\w+)')
            patterns['imports'] = re.compile(r'import\s+([\w\.]+);')
        
        elif language == 'cpp' or language == 'c':
            patterns['functions'] = re.compile(r'\w+\s+(\w+)\s*\(.*?\)\s*{')
            patterns['classes'] = re.compile(r'class\s+(\w+)')
            patterns['imports'] = re.compile(r'#include\s*[<"]([^>"]+)[>"]')
        
        return patterns
    
    def _is_test_file(self, file_path: str) -> bool:
        """테스트 파일 여부 확인"""
        test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*\.test\.js$',
            r'.*\.spec\.js$',
            r'.*Test\.java$',
            r'test/.*',
            r'tests/.*',
            r'__tests__/.*',
            r'spec/.*'
        ]
        
        for pattern in test_patterns:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        
        return False


class DiffAnalyzer:
    """메인 DiffAnalyzer 클래스 - 전체 분석 프로세스를 조율"""
    
    def __init__(self):
        self.language_analyzer = LanguageAnalyzer()
        self.complexity_analyzer = CodeComplexityAnalyzer()
        self.structural_analyzer = StructuralChangeAnalyzer()
        
        # 입출력 로거 설정
        self.io_logger = ModuleIOLogger("DiffAnalyzer")
    
    def analyze_webhook_data(self, parsed_data: 'ParsedWebhookData') -> DiffAnalysisResult:
        """
        GitDataParser에서 파싱된 webhook 데이터를 심층 분석
        
        Args:
            parsed_data: GitDataParser에서 파싱된 webhook 데이터
            
        Returns:
            DiffAnalysisResult: 심층 분석 결과
        """
        # 입력 로깅
        self.io_logger.log_input(
            "analyze_webhook_data",
            data=parsed_data,
            metadata={
                "repository": parsed_data.repository,
                "commits_count": len(parsed_data.commits),
                "files_changed": parsed_data.diff_stats.files_changed,
                "total_additions": parsed_data.diff_stats.total_additions,
                "total_deletions": parsed_data.diff_stats.total_deletions,
                "file_types": list(set(fc.file_type for fc in parsed_data.file_changes if hasattr(fc, 'file_type') and fc.file_type))
            }
        )
        
        start_time = time.time()
        
        try:
            logger.info(f"🔍 DiffAnalyzer: Starting analysis for {parsed_data.repository}")
            
            # CommitMetadata 생성 (필수 필드 포함)
            first_commit = parsed_data.commits[0] if parsed_data.commits else None
            commit_metadata = CommitMetadata(
                sha=first_commit.sha if first_commit else "unknown",
                message=first_commit.message if first_commit else "No commit message",
                author_name=first_commit.author.name if first_commit and first_commit.author else "Unknown",
                author_email=first_commit.author.email if first_commit and first_commit.author else "unknown@example.com",
                repository_name=parsed_data.repository,
                timestamp=parsed_data.timestamp
            )
            
            # ParsedDiff 객체 생성
            parsed_diff = ParsedDiff(
                repository_name=parsed_data.repository,
                commit_sha=commit_metadata.sha,
                file_changes=parsed_data.file_changes,
                diff_stats=parsed_data.diff_stats
            )
            
            # 기존 analyze 메서드 호출
            result = self.analyze(parsed_diff, commit_metadata)
            
            # 출력 로깅
            self.io_logger.log_output(
                "analyze_webhook_data",
                data=result,
                metadata={
                    "repository": parsed_data.repository,
                    "analysis_success": True,
                    "files_analyzed": result.total_files_changed,
                    "complexity_delta": result.complexity_delta,
                    "supported_languages": result.supported_languages,
                    "binary_files_count": len(result.binary_files_changed),
                    "analysis_duration_seconds": result.analysis_duration_seconds
                }
            )
            
            # 분석 완료 로그
            logger.info(
                f"✅ DiffAnalyzer: Analysis completed for {parsed_data.repository} "
                f"(files={result.total_files_changed}, complexity_delta={result.complexity_delta:.2f}, "
                f"duration={result.analysis_duration_seconds:.3f}s)"
            )
            
            return result
            
        except Exception as e:
            analysis_duration = time.time() - start_time
            
            # 오류 로깅
            self.io_logger.log_error(
                "analyze_webhook_data",
                e,
                metadata={
                    "repository": parsed_data.repository,
                    "analysis_duration_seconds": analysis_duration,
                    "files_attempted": parsed_data.diff_stats.files_changed
                }
            )
            
            logger.error(f"❌ DiffAnalyzer: Analysis failed for {parsed_data.repository}: {e}")
            
            # 실패 시에도 기본 결과 반환
            first_commit = parsed_data.commits[0] if parsed_data.commits else None
            return DiffAnalysisResult(
                commit_sha=first_commit.sha if first_commit else "unknown",
                repository_name=parsed_data.repository,
                author_email=first_commit.author.email if first_commit and first_commit.author else "unknown@example.com",
                timestamp=parsed_data.timestamp,
                total_files_changed=parsed_data.diff_stats.files_changed,
                total_additions=parsed_data.diff_stats.total_additions,
                total_deletions=parsed_data.diff_stats.total_deletions,
                language_breakdown={},
                complexity_delta=0.0,
                analyzed_files=[],
                binary_files_changed=[],
                analysis_duration_seconds=analysis_duration,
                supported_languages=[],
                unsupported_files_count=0
            )
    
    def analyze(self, parsed_diff: ParsedDiff, commit_metadata: CommitMetadata,
                repository_context: Optional[RepositoryContext] = None) -> DiffAnalysisResult:
        """메인 분석 로직"""
        start_time = time.time()
        
        try:
            # 1. 데이터 검증
            self._validate_input(parsed_diff, commit_metadata)
            
            # 2. 언어별 분류
            classification_result = self.language_analyzer.classify_by_language(parsed_diff.file_changes)
            
            # 3. 파일별 상세 분석
            analyzed_files = []
            binary_files = []
            
            for file_change in classification_result.supported_files:
                try:
                    analysis = self._analyze_single_file(file_change, classification_result)
                    if analysis:
                        analyzed_files.append(analysis)
                except BinaryFileAnalysisError:
                    binary_files.append(file_change.filename)
                except Exception as e:
                    logger.warning(f"Failed to analyze {file_change.filename}: {e}")
            
            # 4. 결과 집계
            result = self._aggregate_results(
                parsed_diff, commit_metadata, classification_result,
                analyzed_files, binary_files, start_time
            )
            
            return result
            
        except Exception as e:
            logger.error(f"DiffAnalyzer failed: {e}")
            raise DiffAnalyzerError(f"Analysis failed: {e}")
    
    def _validate_input(self, parsed_diff: ParsedDiff, commit_metadata: CommitMetadata):
        """입력 데이터 검증"""
        if not parsed_diff.file_changes:
            raise DiffAnalyzerError("No file changes to analyze")
        
        if not commit_metadata.sha:
            raise DiffAnalyzerError("Missing commit SHA")
    
    def _analyze_single_file(self, file_change: Any, classification_result: LanguageClassificationResult) -> Optional[AnalyzedFile]:
        """개별 파일 분석"""
        filename = file_change.filename
        language = self.language_analyzer._detect_language(filename)
        file_type = self.language_analyzer._determine_file_type(filename, language)
        
        # 바이너리 파일 검사
        if file_type == FileType.BINARY:
            raise BinaryFileAnalysisError(filename)
        
        # 변경 타입 결정
        status = getattr(file_change, 'status', 'modified')
        change_type = ChangeType.ADDED if status == 'added' else \
                     ChangeType.DELETED if status == 'removed' else \
                     ChangeType.MODIFIED
        
        # 기본 정보
        lines_added = getattr(file_change, 'additions', 0)
        lines_deleted = getattr(file_change, 'deletions', 0)
        
        # 복잡도 분석
        complexity_delta = 0.0
        if language in self.language_analyzer.ANALYSIS_SUPPORTED_LANGUAGES:
            try:
                complexity_result = self.complexity_analyzer.analyze_complexity(file_change, language)
                if complexity_result.analysis_success:
                    complexity_delta = complexity_result.metrics.complexity_delta
            except Exception as e:
                logger.debug(f"Complexity analysis skipped for {filename}: {e}")
        
        # 구조적 변경 분석
        functions_changed = 0
        classes_changed = 0
        if language in self.language_analyzer.ANALYSIS_SUPPORTED_LANGUAGES:
            try:
                structural_result = self.structural_analyzer.analyze_structural_changes(file_change, language)
                if structural_result.analysis_success:
                    changes = structural_result.changes
                    functions_changed = (len(changes.functions_added) + 
                                       len(changes.functions_modified) + 
                                       len(changes.functions_deleted))
                    classes_changed = (len(changes.classes_added) + 
                                     len(changes.classes_modified) + 
                                     len(changes.classes_deleted))
            except Exception as e:
                logger.debug(f"Structural analysis skipped for {filename}: {e}")
        
        return AnalyzedFile(
            file_path=filename,
            language=language,
            file_type=file_type,
            change_type=change_type,
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            complexity_delta=complexity_delta,
            functions_changed=functions_changed,
            classes_changed=classes_changed
        )
    
    def _aggregate_results(self, parsed_diff: ParsedDiff, commit_metadata: CommitMetadata,
                          classification_result: LanguageClassificationResult,
                          analyzed_files: List[AnalyzedFile], binary_files: List[str],
                          start_time: float) -> DiffAnalysisResult:
        """분석 결과 집계"""
        
        # 기본 통계
        total_files_changed = len(parsed_diff.file_changes)
        total_additions = sum(getattr(fc, 'additions', 0) for fc in parsed_diff.file_changes)
        total_deletions = sum(getattr(fc, 'deletions', 0) for fc in parsed_diff.file_changes)
        
        # 복잡도 집계
        complexity_delta = sum(af.complexity_delta for af in analyzed_files)
        
        # 분석 메타데이터
        analysis_duration = time.time() - start_time
        supported_languages = list(classification_result.language_stats.keys())
        unsupported_files_count = len(classification_result.unsupported_files)
        
        return DiffAnalysisResult(
            commit_sha=commit_metadata.sha,
            repository_name=commit_metadata.repository_name,
            author_email=commit_metadata.author_email,
            timestamp=commit_metadata.timestamp,
            total_files_changed=total_files_changed,
            total_additions=total_additions,
            total_deletions=total_deletions,
            language_breakdown=classification_result.language_stats,
            complexity_delta=complexity_delta,
            analyzed_files=analyzed_files,
            binary_files_changed=binary_files,
            analysis_duration_seconds=analysis_duration,
            supported_languages=supported_languages,
            unsupported_files_count=unsupported_files_count
        ) 