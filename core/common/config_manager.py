"""
配置管理模块，用于管理数据库中的配置项
"""
import json
from core.common.db import db_query, db_execute, db_fetchone


class ConfigManager:
    """配置管理器"""
    
    @staticmethod
    def get_config(key: str, default=None):
        """
        获取配置项的值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值，如果不存在则返回默认值
        """
        result = db_fetchone("SELECT value FROM configurations WHERE key = ?", (key,))
        if result and len(result) > 0:
            return result[0]
        return default
    
    @staticmethod
    def set_config(key: str, value: str):
        """
        设置配置项的值
        
        Args:
            key: 配置键名
            value: 配置值
        """
        # 使用SQLite的INSERT OR REPLACE INTO实现原子化的UPSERT操作
        # 这样可以避免并发环境下的唯一约束冲突
        db_execute(
            "INSERT OR REPLACE INTO configurations (key, value) VALUES (?, ?)",
            (key, value)
        )
    
    @staticmethod
    def get_knowledge_base_url():
        """
        获取知识库URL
        
        Returns:
            URL字符串，如果不存在则返回空字符串
        """
        url = ConfigManager.get_config('knowledge_base_url', '')
        return url if url else ''
    
    @staticmethod
    def set_knowledge_base_url(url: str):
        """
        设置知识库URL
        
        Args:
            url: URL字符串
        """
        ConfigManager.set_config('knowledge_base_url', url)