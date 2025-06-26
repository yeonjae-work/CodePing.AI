#!/usr/bin/env python3
"""
DiffAnalyzer 푸시 테스트 파일

이 파일은 실제 GitHub 푸시 시 DiffAnalyzer가 어떻게 동작하는지 테스트하기 위해 생성되었습니다.
"""

import sys
from datetime import datetime
from typing import List, Dict, Optional


class TestAnalyzer:
    """테스트용 분석기 클래스"""
    
    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.now()
        self.analysis_count = 0
    
    def analyze_data(self, data: Dict) -> Dict:
        """데이터 분석 메서드"""
        self.analysis_count += 1
        
        result = {
            "analyzer": self.name,
            "timestamp": self.created_at.isoformat(),
            "analysis_count": self.analysis_count,
            "data_size": len(str(data)),
            "complexity": self._calculate_complexity(data)
        }
        
        return result
    
    def _calculate_complexity(self, data: Dict) -> float:
        """복잡도 계산 (테스트용)"""
        if not data:
            return 0.0
        
        # 간단한 복잡도 계산
        nested_levels = self._count_nested_levels(data)
        key_count = len(data.keys()) if isinstance(data, dict) else 0
        
        return nested_levels * 0.5 + key_count * 0.1
    
    def _count_nested_levels(self, obj, level=0) -> int:
        """중첩 레벨 계산"""
        if not isinstance(obj, (dict, list)):
            return level
        
        if isinstance(obj, dict):
            max_level = level
            for value in obj.values():
                max_level = max(max_level, self._count_nested_levels(value, level + 1))
            return max_level
        
        elif isinstance(obj, list):
            max_level = level
            for item in obj:
                max_level = max(max_level, self._count_nested_levels(item, level + 1))
            return max_level
        
        return level


def test_analyzer_functionality():
    """분석기 기능 테스트"""
    print("🔬 TestAnalyzer 기능 테스트 시작")
    
    # 분석기 생성
    analyzer = TestAnalyzer("DiffAnalyzer-Push-Test")
    
    # 테스트 데이터
    test_data = {
        "repository": "CodePing.AI",
        "commit": {
            "sha": "test123",
            "message": "feat: Add DiffAnalyzer test",
            "files": [
                {"name": "test_diff_analyzer_push.py", "additions": 50, "deletions": 0},
                {"name": "README.md", "additions": 5, "deletions": 1}
            ]
        },
        "analysis": {
            "languages": ["python", "markdown"],
            "complexity": {
                "total": 2.5,
                "impact": "medium"
            }
        }
    }
    
    # 분석 실행
    result = analyzer.analyze_data(test_data)
    
    print(f"   ✅ 분석기: {result['analyzer']}")
    print(f"   ✅ 분석 횟수: {result['analysis_count']}")
    print(f"   ✅ 데이터 크기: {result['data_size']} bytes")
    print(f"   ✅ 복잡도: {result['complexity']:.2f}")
    
    return result


if __name__ == "__main__":
    print("🚀 DiffAnalyzer 푸시 테스트")
    print("=" * 50)
    
    try:
        result = test_analyzer_functionality()
        
        print("\n🎉 테스트 성공!")
        print(f"분석 결과: {result}")
        
        print("\n💡 이 푸시로 인해 발생할 예상 분석:")
        print("   📁 파일 추가: 1개 (test_diff_analyzer_push.py)")
        print("   🔤 언어: Python")
        print("   📊 복잡도: 클래스 1개, 함수 4개")
        print("   🏗️ 구조: TestAnalyzer 클래스 추가")
        print("   📝 타입: 소스 코드 (테스트 파일)")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        sys.exit(1) 