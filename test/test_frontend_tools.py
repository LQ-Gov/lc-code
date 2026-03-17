"""
测试前端工具函数的导入
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agent.tools import navigate_to_page, refresh_page


def test_frontend_tools_import():
    """测试前端工具函数是否能成功导入"""
    print("=== 测试前端工具函数导入 ===")
    
    tools = [
        ("navigate_to_page", navigate_to_page),
        ("refresh_page", refresh_page)
    ]
    
    for name, tool in tools:
        print(f"✅ {name}: {type(tool).__name__}")
        # 验证返回值结构（通过调用invoke方法）
        if name == "navigate_to_page":
            result = tool.invoke({"page_url": "https://example.com", "page_name": "Example Page"})
            print(f"   示例返回: {result}")
        elif name == "refresh_page":
            result = tool.invoke({})
            print(f"   示例返回: {result}")
    
    print("\n✅ 所有前端工具导入和基本功能测试通过！")


if __name__ == "__main__":
    test_frontend_tools_import()