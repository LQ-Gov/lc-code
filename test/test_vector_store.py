"""
测试向量库功能的脚本
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.common.vector_store import KnowledgeBaseVectorStore

def test_vector_store():
    """测试向量库功能"""
    print("=== 测试向量库功能 ===")
    
    try:
        # 初始化向量存储
        vector_store = KnowledgeBaseVectorStore()
        print("✓ 向量存储初始化成功")
        
        # 构建向量库
        print("\n正在构建向量库...")
        count = vector_store.build_vector_store(force_rebuild=True)
        print(f"✓ 向量库构建完成，共导入 {count} 个QA对")
        
        if count > 0:
            # 获取向量库信息
            info = vector_store.get_collection_info()
            print(f"\n向量库信息: {info}")
            
            # 测试搜索功能
            print("\n测试搜索功能...")
            query = "如何重置密码？"
            results = vector_store.search_similar_questions(query, n_results=3)
            print(f"查询: '{query}'")
            print(f"找到 {len(results)} 个相似结果:")
            
            for i, result in enumerate(results, 1):
                print(f"\n{i}. 相似度距离: {result['distance']:.4f}")
                print(f"   问题: {result['question'][:100]}...")
                print(f"   答案: {result['answer'][:100]}...")
                print(f"   URL: {result['url']}")
        else:
            print("⚠️ 没有找到任何QA对，请确保知识库中有数据")
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_vector_store()