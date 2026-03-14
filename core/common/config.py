import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 知识库配置
DEFAULT_KNOWLEDGE_BASE_URL = os.getenv("DEFAULT_KNOWLEDGE_BASE_URL")
# 数据库配置
DB_PATH = os.getenv("DB_PATH")
# 向量库存储路径配置
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")
# 机器人配置
DEFAULT_REPLY_STYLE = os.getenv("DEFAULT_REPLY_STYLE", "正式")
AUTO_FIX_TIMEOUT = int(os.getenv("AUTO_FIX_TIMEOUT", 600))
# 元智能体配置
SUPPORTED_DOC_FORMATS = ["pdf", "docx", "txt"]
ROBOT_TEMPLATES = ["金融类", "电商类", "服务类"]

# 错误类型枚举
ERROR_TYPES = [
    "知识库未匹配到正确答案",
    "特定问题操作步骤错误",
    "回复内容不准确",
    "工具调用失败",
    "系统故障"
]
# 角色枚举
ROLES = ["普通管理者", "超级管理员"]