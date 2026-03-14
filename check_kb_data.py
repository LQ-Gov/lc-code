"""
检查知识库数据格式的脚本
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.common.db import db_query

def check_kb_data_format():
    """检查知识库数据格式"""
    print("=== 检查知识库数据格式 ===")
    
    # 查询所有爬虫结果
    sql = """
        SELECT seed_url, questions, answers 
        FROM crawler_results 
        WHERE questions IS NOT NULL AND answers IS NOT NULL
        LIMIT 5
    """
    results = db_query(sql)
    
    if not results:
        print("⚠️ 没有找到任何知识库数据")
        return
    
    for i, result in enumerate(results):
        seed_url = result[0]
        questions = result[1]
        answers = result[2]
        
        print(f"\n--- 记录 {i+1} ---")
        print(f"URL: {seed_url}")
        print(f"Questions类型: {type(questions)}")
        print(f"Questions长度: {len(questions) if questions else 0}")
        print(f"Questions预览: {questions[:200] if questions else 'None'}...")
        print(f"Answers类型: {type(answers)}")
        print(f"Answers长度: {len(answers) if answers else 0}")
        print(f"Answers预览: {answers[:200] if answers else 'None'}...")

if __name__ == "__main__":
    check_kb_data_format()