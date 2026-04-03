#!/usr/bin/env python3
"""测试结果审查器 CLI"""
import sys
import json
from pathlib import Path
from rodski.reviewers import LLMReviewer


def main():
    if len(sys.argv) < 2:
        print("用法: python -m rodski.reviewers.cli <result_dir> [case_xml]")
        sys.exit(1)

    result_dir = sys.argv[1]
    case_xml = sys.argv[2] if len(sys.argv) > 2 else None

    reviewer = LLMReviewer()
    print(f"正在审查: {result_dir}")

    result = reviewer.review_result(result_dir, case_xml)

    print("\n" + "="*60)
    print(f"审查结果: {result['verdict']}")
    print(f"置信度: {result['confidence']:.2%}")
    print(f"理由: {result['reason']}")

    if result.get('issues'):
        print("\n发现的问题:")
        for issue in result['issues']:
            print(f"  - {issue}")
    print("="*60)


if __name__ == '__main__':
    main()
