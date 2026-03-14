"""
基于Chroma DB的向量库存储模块
用于将知识库中的QA对存储为向量，并提供相似性搜索功能
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from core.common.db import db_query
from core.common.config import CHROMA_PATH

# 确保Chroma路径存在
os.makedirs(CHROMA_PATH, exist_ok=True)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: chromadb not installed. Vector store functionality will be disabled.")

class KnowledgeBaseVectorStore:
    """知识库向量存储类"""
    
    def __init__(self, collection_name: str = "knowledge_base_qa"):
        """
        初始化向量存储
        
        Args:
            collection_name: Chroma集合名称
        """
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is not installed. Please install it with: pip install chromadb")
            
        self.collection_name = collection_name
        # 使用默认的嵌入函数（sentence-transformers/all-MiniLM-L6-v2）
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        
        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
    
    def load_knowledge_base_data(self) -> List[Dict]:
        """
        从数据库加载知识库数据
        
        Returns:
            包含所有QA对的列表，每个元素为{"question": str, "answer": str, "url": str}
        """
        qa_pairs = []
        
        # 查询所有爬虫结果
        sql = """
            SELECT seed_url, questions, answers 
            FROM crawler_results 
            WHERE questions IS NOT NULL AND answers IS NOT NULL
        """
        results = db_query(sql)
        
        for result in results:
            seed_url = result[0]
            questions_data = result[1]
            answers_data = result[2]
            
            try:
                # 尝试解析为JSON格式（新格式）
                questions = json.loads(questions_data) if questions_data else []
                answers = json.loads(answers_data) if answers_data else []
                
                # 检查是否为数组格式
                if isinstance(questions, list) and isinstance(answers, list):
                    # 确保两个数组长度一致
                    min_len = min(len(questions), len(answers))
                    for i in range(min_len):
                        question = questions[i].get('question', '') if isinstance(questions[i], dict) else str(questions[i])
                        answer = answers[i].get('answer', '') if isinstance(answers[i], dict) else str(answers[i])
                        
                        if question and answer:  # 只添加非空的QA对
                            qa_pairs.append({
                                "question": question,
                                "answer": answer,
                                "url": seed_url
                            })
                else:
                    # 处理纯文本格式（旧格式）
                    # 在这种情况下，questions_data和answers_data本身就是单个QA对
                    question = str(questions_data).strip()
                    answer = str(answers_data).strip()
                    
                    if question and answer:  # 只添加非空的QA对
                        qa_pairs.append({
                            "question": question,
                            "answer": answer,
                            "url": seed_url
                        })
                        
            except (json.JSONDecodeError, AttributeError, IndexError) as e:
                # JSON解析失败，尝试作为纯文本处理
                try:
                    question = str(questions_data).strip() if questions_data else ''
                    answer = str(answers_data).strip() if answers_data else ''
                    
                    if question and answer:  # 只添加非空的QA对
                        qa_pairs.append({
                            "question": question,
                            "answer": answer,
                            "url": seed_url
                        })
                except Exception as text_error:
                    print(f"Warning: Failed to parse QA data for URL {seed_url}: {e}, {text_error}")
                    continue
        
        return qa_pairs
    
    def build_vector_store(self, force_rebuild: bool = False) -> int:
        """
        构建向量库，将知识库数据导入Chroma
        
        Args:
            force_rebuild: 是否强制重建（删除现有数据）
            
        Returns:
            导入的文档数量
        """
        if force_rebuild:
            # 删除现有集合并重新创建
            try:
                self.client.delete_collection(self.collection_name)
            except ValueError:
                # 集合不存在，忽略错误
                pass
            
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_function
            )
        
        # 加载知识库数据
        qa_pairs = self.load_knowledge_base_data()
        
        if not qa_pairs:
            print("No QA pairs found in knowledge base")
            return 0
        
        # 准备批量插入的数据
        documents = []
        metadatas = []
        ids = []
        
        for i, qa_pair in enumerate(qa_pairs):
            documents.append(qa_pair["question"])
            metadatas.append({
                "answer": qa_pair["answer"],
                "url": qa_pair["url"]
            })
            ids.append(f"qa_{i}")
        
        # 批量添加到向量库
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Successfully imported {len(documents)} QA pairs into vector store")
        return len(documents)
    
    def search_similar_questions(self, query: str, n_results: int = 5) -> List[Dict]:
        """
        搜索与查询最相似的问题
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            相似问题列表，每个元素包含question, answer, url, distance
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        similar_questions = []
        if results['documents'] and results['metadatas']:
            for i in range(len(results['documents'][0])):
                similar_questions.append({
                    "question": results['documents'][0][i],
                    "answer": results['metadatas'][0][i]['answer'],
                    "url": results['metadatas'][0][i]['url'],
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        return similar_questions
    
    def get_collection_info(self) -> Dict:
        """
        获取集合信息
        
        Returns:
            集合统计信息
        """
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
            "path": CHROMA_PATH
        }