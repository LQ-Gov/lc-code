"""
测试Agent Tools的基本功能
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agent.tools import (
    get_all_knowledge_bases,
    get_current_knowledge_base_url,
    get_enabled_special_question_flows,
    get_specific_question_flow,
    create_knowledge_base,
    update_knowledge_base,
    delete_knowledge_base,
    rebuild_knowledge_base,
    rebuild_current_knowledge_base,
    get_knowledge_base_by_id,
    get_all_special_question_flows,
    create_special_question_flow,
    update_special_question_flow,
    delete_special_question_flow,
    format_special_questions_for_prompt,
    navigate_to_page,
    refresh_page
)


def test_agent_tools_import():
    """测试Agent工具是否能成功导入"""
    print("=== 测试Agent Tools导入 ===")
    
    tools = [
        ("get_all_knowledge_bases", get_all_knowledge_bases),
        ("get_current_knowledge_base_url", get_current_knowledge_base_url),
        ("get_knowledge_base_by_id", get_knowledge_base_by_id),
        ("create_knowledge_base", create_knowledge_base),
        ("update_knowledge_base", update_knowledge_base),
        ("delete_knowledge_base", delete_knowledge_base),
        ("rebuild_knowledge_base", rebuild_knowledge_base),
        ("rebuild_current_knowledge_base", rebuild_current_knowledge_base),
        ("get_enabled_special_question_flows", get_enabled_special_question_flows),
        ("get_specific_question_flow", get_specific_question_flow),
        ("get_all_special_question_flows", get_all_special_question_flows),
        ("create_special_question_flow", create_special_question_flow),
        ("update_special_question_flow", update_special_question_flow),
        ("delete_special_question_flow", delete_special_question_flow),
        ("format_special_questions_for_prompt", format_special_questions_for_prompt),
        ("navigate_to_page", navigate_to_page),
        ("refresh_page", refresh_page)
    ]
    
    for name, tool in tools:
        print(f"✅ {name}: {type(tool).__name__}")
    
    print(f"\n✅ 总共 {len(tools)} 个Agent工具导入成功！")


if __name__ == "__main__":
    test_agent_tools_import()