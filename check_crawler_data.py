#!/usr/bin/env python3
"""
检查爬虫结果数据格式的脚本
"""
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.common.db import db_query

def check_crawler_data():
    """检查爬虫结果数据格式"""
    print("=== 检查爬虫结果数据格式 ===")
    
    # 查询所有爬虫结果
    sql = "SELECT seed_url, questions, answers FROM crawler_results"
    results = db_query(sql)
    
    print(f"总记录数: {len(results)}")
    print()
    
    valid_records = 0
    for i, result in enumerate(results):
        seed_url = result[0]
        questions_json = result[1]
        answers_json = result[2]
        
        print(f"记录 {i+1}:")
        print(f"  URL: {seed_url}")
        print(f"  Questions 类型: {type(questions_json)}, 长度: {len(questions_json) if questions_json else 0}")
        print(f"  Answers 类型: {type(answers_json)}, 长度: {len(answers_json) if answers_json else 0}")
        
        # 尝试解析JSON
        try:
            if questions_json and answers_json:
                questions = json.loads(questions_json)
                answers = json.loads(answers_json)
                print(f"  JSON解析成功: Q={len(questions)}, A={len(answers)}")
                valid_records += 1
            else:
                print(f"  数据为空")
        except json.JSONDecodeError as e:
            print(f"  JSON解析失败: {e}")
            # 显示前100个字符
            if questions_json:
                print(f"  Questions 前100字符: {repr(questions_json[:100])}")
            if answers_json:
                print(f"  Answers 前100字符: {repr(answers_json[:100])}")
        except Exception as e:
            print(f"  其他错误: {e}")
        
        print()
    
    print(f"有效记录数: {valid_records}/{len(results)}")

if __name__ == "__main__":
    check_crawler_data()
