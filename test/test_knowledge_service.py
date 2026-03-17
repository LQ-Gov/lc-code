"""
测试KnowledgeBaseService的基本功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.common.knowledge_service import KnowledgeBaseService


def test_knowledge_service():
    """测试知识库服务的基本功能"""
    print("=== 测试KnowledgeBaseService ===")
    
    try:
        # 测试获取所有知识库
        print("1. 测试获取所有知识库...")
        knowledge_bases = KnowledgeBaseService.get_all_knowledge_bases()
        print(f"   获取到 {len(knowledge_bases)} 个知识库记录")
        
        # 测试获取当前知识库URL
        print("2. 测试获取当前知识库URL...")
        current_url = KnowledgeBaseService.get_current_knowledge_base_url()
        print(f"   当前知识库URL: {current_url}")
        
        # 测试获取单个知识库（如果存在）
        if knowledge_bases:
            kb_id = knowledge_bases[0]["id"]
            print(f"3. 测试获取单个知识库 (ID: {kb_id})...")
            kb = KnowledgeBaseService.get_knowledge_base_by_id(kb_id)
            if kb:
                print(f"   成功获取知识库: {kb['seed_url'][:50]}...")
            else:
                print("   未找到指定的知识库")
        else:
            print("3. 跳过单个知识库测试（无数据）")
        
        print("\n✅ 所有基本测试通过！")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_knowledge_service()