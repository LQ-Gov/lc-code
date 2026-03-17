from core.crawl.graph import crawler_graph
from core.crawl.state import CrawlState
from core.common.db import db_query, db_execute, db_fetchone
from core.common.config_manager import ConfigManager
from typing import List, Dict, Any, Optional


class KnowledgeBaseService:
    """知识库服务类，封装所有知识库相关的数据库操作和业务逻辑"""
    
    @staticmethod
    def get_all_knowledge_bases() -> List[Dict[str, Any]]:
        """
        获取所有知识库记录
        
        Returns:
            List[Dict]: 知识库记录列表
        """
        try:
            sql = """
                SELECT 
                    id,
                    seed_url,
                    current_url,
                    raw_content,
                    questions,
                    answers,
                    created_at
                FROM crawler_results
                ORDER BY created_at DESC
            """
            results = db_query(sql)
            knowledge_bases = []
            for result in results:
                kb = {
                    "id": str(result[0]) if result[0] else "",
                    "seed_url": result[1] if result[1] else "",
                    "current_url": result[2] if result[2] else "",
                    "raw_content": result[3] if result[3] else "",
                    "questions": result[4] if result[4] else "",
                    "answers": result[5] if result[5] else "",
                    "created_at": result[6] if result[6] else ""
                }
                knowledge_bases.append(kb)
            return knowledge_bases
        except Exception as e:
            raise Exception(f"获取知识库列表失败: {str(e)}")
    
    @staticmethod
    def create_knowledge_base(seed_url: str) -> Dict[str, Any]:
        """
        创建知识库并启动爬虫
        
        Args:
            seed_url (str): 种子URL
            
        Returns:
            Dict: 爬虫结果
        """
        try:
            # 启动爬虫更新知识库
            crawl_state = CrawlState(seed_url=seed_url)
            result = crawler_graph.invoke(crawl_state)
            
            # 更新知识库URL配置
            ConfigManager.set_knowledge_base_url(seed_url)
            
            return result
        except Exception as e:
            raise Exception(f"创建知识库失败: {str(e)}")
    
    @staticmethod
    def update_knowledge_base(kb_id: str, new_url: str, rebuild: bool = False) -> Dict[str, Any]:
        """
        更新知识库URL
        
        Args:
            kb_id (str): 知识库ID
            new_url (str): 新的URL
            rebuild (bool): 是否重新爬取新URL的内容
            
        Returns:
            Dict: 操作结果
        """
        try:
            # 检查知识库ID是否存在
            existing_record = db_fetchone("SELECT id, seed_url FROM crawler_results WHERE id = ?", (kb_id,))
            if not existing_record:
                raise Exception("知识库不存在")
            
            old_url = existing_record[1]
            
            # 如果URL没有变化，直接返回成功
            if old_url == new_url:
                return {"message": "知识库URL未变化，无需更新"}
            
            # 更新知识库URL配置
            ConfigManager.set_knowledge_base_url(new_url)
            
            # 如果不需要重建，直接更新数据库中的seed_url
            if not rebuild:
                db_execute("UPDATE crawler_results SET seed_url = ? WHERE id = ?", (new_url, kb_id))
                return {"message": "知识库URL已更新，但未重新爬取"}
            
            # 需要重建，重新爬取新URL的内容
            crawl_state = CrawlState(seed_url=new_url)
            result = crawler_graph.invoke(crawl_state)
            
            # 删除旧URL的所有相关记录
            db_execute("DELETE FROM crawler_results WHERE seed_url = ?", (old_url,))
            
            return {"message": "知识库URL已更新并重新爬取完成", "result": result}
        except Exception as e:
            raise Exception(f"更新知识库失败: {str(e)}")
    
    @staticmethod
    def delete_knowledge_base(kb_id: str) -> bool:
        """
        删除知识库
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 删除知识库记录
            db_execute("DELETE FROM crawler_results WHERE id = ?", (kb_id,))
            
            # 清空知识库URL配置
            ConfigManager.set_knowledge_base_url("")
            
            return True
        except Exception as e:
            raise Exception(f"删除知识库失败: {str(e)}")
    
    @staticmethod
    def rebuild_knowledge_base(kb_id: str) -> Dict[str, Any]:
        """
        手动重建指定知识库（重新爬取）
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            Dict: 爬虫结果
        """
        try:
            # 获取知识库的seed_url
            existing_record = db_fetchone("SELECT seed_url FROM crawler_results WHERE id = ?", (kb_id,))
            if not existing_record:
                raise Exception("知识库不存在")
            
            seed_url = existing_record[0]
            
            # 重新爬取
            crawl_state = CrawlState(seed_url=seed_url)
            result = crawler_graph.invoke(crawl_state)
            
            return result
        except Exception as e:
            raise Exception(f"重建知识库失败: {str(e)}")
    
    @staticmethod
    def rebuild_current_knowledge_base() -> Dict[str, Any]:
        """
        重建当前知识库：读取配置表中的知识库URL，然后重新爬取对应的页面
        
        Returns:
            Dict: 爬虫结果
        """
        try:
            # 获取配置中的知识库URL
            url = ConfigManager.get_knowledge_base_url()
            
            if not url:
                raise Exception("没有配置的知识库URL")
            
            # 清空现有的爬虫结果
            db_execute("DELETE FROM crawler_results")
            
            # 重新爬取URL
            crawl_state = CrawlState(seed_url=url)
            result = crawler_graph.invoke(crawl_state)
            
            return result
        except Exception as e:
            raise Exception(f"重建当前知识库失败: {str(e)}")
    
    @staticmethod
    def get_knowledge_base_by_id(kb_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个知识库记录
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            Optional[Dict]: 知识库记录或None
        """
        try:
            sql = """
                SELECT 
                    id,
                    seed_url,
                    current_url,
                    raw_content,
                    questions,
                    answers,
                    created_at
                FROM crawler_results
                WHERE id = ?
            """
            result = db_fetchone(sql, (kb_id,))
            if not result:
                return None
                
            kb = {
                "id": str(result[0]) if result[0] else "",
                "seed_url": result[1] if result[1] else "",
                "current_url": result[2] if result[2] else "",
                "raw_content": result[3] if result[3] else "",
                "questions": result[4] if result[4] else "",
                "answers": result[5] if result[5] else "",
                "created_at": result[6] if result[6] else ""
            }
            return kb
        except Exception as e:
            raise Exception(f"获取知识库详情失败: {str(e)}")
    
    @staticmethod
    def get_current_knowledge_base_url() -> str:
        """
        获取当前配置的知识库URL
        
        Returns:
            str: 当前知识库URL
        """
        return ConfigManager.get_knowledge_base_url()