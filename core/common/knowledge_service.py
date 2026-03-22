from core.crawl.crawl import QACrawler, CrawlCallback
from core.common.db import db_query, db_execute, db_fetchone
from core.common.config_manager import ConfigManager
from core.common.vector_store import KnowledgeBaseVectorStore
from typing import List, Dict, Any, Optional
import threading
import asyncio
import json,traceback
import os
import tempfile



class KnowledgeBaseCrawlCallback(CrawlCallback):
    """知识库爬虫回调类，用于处理爬取完成后的数据库保存操作"""
    
    def __init__(self, seed_url: str):
        self.seed_url = seed_url
    
    async def finished(self, data: List[Dict], stats: Dict[str, Any] = None):
        """爬取完成时调用，执行数据库保存和向量库重建"""
        try:
            # 验证爬取结果有数据
            if not data:
                raise Exception("爬取失败：未提取到任何Q&A数据")
            
            # 现在安全地清空当前知识库的所有相关记录
            db_execute("DELETE FROM crawler_results")
            
            # 将新数据导入数据库
            for item in data:
                db_execute(
                    "INSERT INTO crawler_results (seed_url, current_url, questions, answers) VALUES (?, ?, ?, ?)",
                    (self.seed_url, item['url'], json.dumps(item['question']), json.dumps(item['answer']))
                )
            
            # 重建向量库
            vector_store = KnowledgeBaseVectorStore()
            vector_store.build_vector_store(force_rebuild=True)
            
            # 设置构建状态为finished
            ConfigManager.set_config("build_kb_status", "finished")

            print("Knowledge base rebuild completed successfully.")
            
        except Exception as e:
            # 如果发生错误，设置状态为error
            ConfigManager.set_config("build_kb_status", "error")
            print(f"Error in rebuild knowledge base callback: {str(e)}")
            traceback.print_stack()
    
    async def error(self, error: Exception, url: str = None):
        """爬取发生错误时调用"""
        ConfigManager.set_config("build_kb_status", "error")
        print(f"Error in crawl: {str(error)}, URL: {url}")


class RebuildKnowledgeBaseCallback(CrawlCallback):
    """单个知识库重建的专用回调类"""
    
    def __init__(self, kb_id: str, seed_url: str):
        self.kb_id = kb_id
        self.seed_url = seed_url
    
    async def finished(self, data: List[Dict], stats: Dict[str, Any] = None):
        """爬取完成时调用，更新指定知识库的数据"""
        try:
            if not data:
                raise Exception("爬取失败：未提取到任何Q&A数据")
            
            # 仅取第一条数据进行更新
            first_item = data[0]
            KnowledgeBaseService.update_knowledge_base_data(self.kb_id, self.seed_url, first_item)
                
        except Exception as e:
            print(f"Error in rebuild knowledge base callback: {str(e)}")
            raise e
    
    async def error(self, error: Exception, url: str = None):
        """爬取发生错误时调用"""
        print(f"Error in rebuild knowledge base crawl: {str(error)}, URL: {url}")
        raise error


class KnowledgeBaseService:
    """知识库服务类，封装所有知识库相关的数据库操作和业务逻辑"""
    CURRENT_CRAWLER = None

    
    
    @staticmethod
    def update_knowledge_base_data(kb_id: str, seed_url: str, data: Dict):
        """更新指定知识库的数据，使用单条数据"""
        if not data:
            raise Exception("爬取失败：未提取到任何Q&A数据")
        
        # 更新该知识库ID的记录，而不是删除后重新插入
        db_execute(
            "UPDATE crawler_results SET current_url = ?, questions = ?, answers = ? WHERE id = ?",
            (data['url'], json.dumps(data['question']), json.dumps(data['answer']), kb_id)
        )
        
        # 更新向量库数据
        vector_store = KnowledgeBaseVectorStore()
        vector_store.update_vector_by_db_id(
            int(kb_id),
            data['question'],
            data['answer'],
            data['url']
        )
    
    @staticmethod
    def get_knowledge_base_by_id(kb_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个知识库记录
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            Dict: 知识库记录，如果不存在则返回None
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
            raise Exception(f"获取知识库记录失败: {str(e)}")
    
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
                ORDER BY id DESC
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
    def _delete_knowledge_by_id(kb_id: str) -> bool:
        """
        删除指定ID的知识库记录和对应的向量库数据
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 删除知识库记录
            db_execute("DELETE FROM crawler_results WHERE id = ?", (kb_id,))
            
            # 删除向量库中的对应记录
            vector_store = KnowledgeBaseVectorStore()
            vector_store.delete_vector_by_db_id(int(kb_id))
            
            return True
        except Exception as e:
            raise Exception(f"删除知识库失败: {str(e)}")
    
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
            # 调用独立的删除函数
            success = KnowledgeBaseService._delete_knowledge_by_id(kb_id)
            
            return success
        except Exception as e:
            raise Exception(f"删除知识库失败: {str(e)}")
    
    @staticmethod
    def rebuild_knowledge_base(kb_id: str) -> Dict[str, Any]:
        """
        重建指定的知识库：针对单条知识库的重新建立，调用爬虫脚本进行重新爬取，
        下钻深度设为0，只爬取对应的url即可，同时爬虫同步执行，用爬取到的结果更新该条知识，
        并更新该条知识对应的向量库数据
        
        Args:
            kb_id (str): 知识库ID
            
        Returns:
            Dict: 操作结果
        """
        try:
            # 检查知识库ID是否存在
            existing_record = db_fetchone("SELECT id, seed_url, current_url FROM crawler_results WHERE id = ?", (kb_id,))
            if not existing_record:
                raise Exception("知识库不存在")
            
            seed_url = existing_record[1]
            current_url = existing_record[2]
            
            if not current_url:
                raise Exception("知识库当前URL为空")
            
            # 创建专用回调实例
            callback = RebuildKnowledgeBaseCallback(kb_id, seed_url)
            
            # 创建爬虫实例，下钻深度设为0，只爬取对应的URL，不指定output_file
            crawler = QACrawler(max_depth=0, concurrency=1, callback=callback)
            
            # 同步执行爬虫
            asyncio.run(crawler.run([current_url]))
            
            return {"message": f"知识库ID {kb_id} 重建完成", "kb_id": kb_id, "url": current_url}
            
        except Exception as e:
            raise Exception(f"重建知识库失败: {str(e)}")
    
    @staticmethod
    def _rebuild_knowledge_base_task(seed_url: str):
        """实际执行知识库重建任务的内部方法"""
        ConfigManager.set_config("build_kb_status", "running")
        try:
            # 创建回调实例
            callback = KnowledgeBaseCrawlCallback(seed_url)
            
            # 重新爬取，不保存到文件（通过回调处理数据）
            KnowledgeBaseService.CURRENT_CRAWLER = QACrawler(max_depth=3, concurrency=10, callback=callback)
            asyncio.run(KnowledgeBaseService.CURRENT_CRAWLER.run([seed_url]))
            
        except Exception as e:
            # 如果发生错误，设置状态为error
            
            ConfigManager.set_config("build_kb_status", "error")
            print(f"Error in rebuild knowledge base task: {str(e)}")
            raise e
    
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
            
            if KnowledgeBaseService.CURRENT_CRAWLER:
                KnowledgeBaseService.CURRENT_CRAWLER.close()
            
            thread = threading.Thread(
                target=KnowledgeBaseService._rebuild_knowledge_base_task,
                args=(url,)
            )
            thread.daemon = True
            thread.start()

            return {"message": f"当前知识库重建任务已启动，URL: {url}", "url": url}
            
        except Exception as e:
            raise Exception(f"重建当前知识库失败: {str(e)}")
    
    @staticmethod
    def get_current_knowledge_base_url() -> str:
        """
        获取当前配置的知识库URL
        
        Returns:
            str: 当前知识库URL
        """
        return ConfigManager.get_knowledge_base_url()