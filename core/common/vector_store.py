"""
基于Chroma DB的向量库存储模块
用于将知识库中的QA对存储为向量，并提供相似性搜索功能
"""
import os
import json
from typing import List, Dict, Optional, Tuple
from core.common.db import db_query
from core.common.config import CHROMA_PATH
from core.common.utils import parse_document

# 确保Chroma路径存在
os.makedirs(CHROMA_PATH, exist_ok=True)

try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("Warning: chromadb not installed. Vector store functionality will be disabled.")

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    TEXT_SPLITTER_AVAILABLE = True
except ImportError:
    TEXT_SPLITTER_AVAILABLE = False
    print("Warning: langchain_text_splitters not installed. Document processing functionality will be limited.")

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
            包含所有QA对的列表，每个元素为{"id": int, "question": str, "answer": str, "url": str}
        """
        qa_pairs = []
        
        # 查询所有爬虫结果，包含id字段
        sql = """
            SELECT id, current_url, questions, answers 
            FROM crawler_results 
            WHERE questions IS NOT NULL AND answers IS NOT NULL
        """
        results = db_query(sql)
        
        for result in results:
            record_id = result[0]
            current_url = result[1]
            questions_data = result[2]
            answers_data = result[3]
            
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
                                "id": record_id,
                                "question": question,
                                "answer": answer,
                                "url": current_url
                            })
                else:
                    # 处理纯文本格式（旧格式）
                    # 在这种情况下，questions_data和answers_data本身就是单个QA对
                    question = str(questions_data).strip()
                    answer = str(answers_data).strip()
                    
                    if question and answer:  # 只添加非空的QA对
                        qa_pairs.append({
                            "id": record_id,
                            "question": question,
                            "answer": answer,
                            "url": current_url
                        })
                        
            except (json.JSONDecodeError, AttributeError, IndexError) as e:
                # JSON解析失败，尝试作为纯文本处理
                try:
                    question = str(questions_data).strip() if questions_data else ''
                    answer = str(answers_data).strip() if answers_data else ''
                    
                    if question and answer:  # 只添加非空的QA对
                        qa_pairs.append({
                            "id": record_id,
                            "question": question,
                            "answer": answer,
                            "url": current_url
                        })
                except Exception as text_error:
                    print(f"Warning: Failed to parse QA data for URL {current_url}: {e}, {text_error}")
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
        
        for qa_pair in qa_pairs:
            documents.append(qa_pair["question"])
            metadatas.append({
                "answer": qa_pair["answer"],
                "url": qa_pair["url"],
                "db_id": qa_pair["id"]  # 添加数据库ID到metadata
            })
            ids.append(f"kb_{qa_pair['id']}")  # 使用数据库ID作为向量库文档ID
        
        # 批量添加到向量库
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"Successfully imported {len(documents)} QA pairs into vector store")
        return len(documents)
    
    def update_vector_by_db_id(self, db_id: int, question: str, answer: str, url: str) -> bool:
        """
        根据数据库ID更新向量库中的数据
        
        Args:
            db_id: 数据库记录ID
            question: 问题文本
            answer: 答案文本
            url: URL
            
        Returns:
            更新是否成功
        """
        try:
            vector_id = f"kb_{db_id}"
            
            # 检查是否存在该ID的向量
            existing = self.collection.get(ids=[vector_id])
            if not existing['ids']:
                # 如果不存在，添加新的向量
                self.collection.add(
                    documents=[question],
                    metadatas=[{
                        "answer": answer,
                        "url": url,
                        "db_id": db_id
                    }],
                    ids=[vector_id]
                )
            else:
                # 如果存在，更新向量
                self.collection.update(
                    ids=[vector_id],
                    documents=[question],
                    metadatas=[{
                        "answer": answer,
                        "url": url,
                        "db_id": db_id
                    }]
                )
            
            return True
        except Exception as e:
            print(f"Error updating vector for db_id {db_id}: {str(e)}")
            return False
    
    def delete_vector_by_db_id(self, db_id: int) -> bool:
        """
        根据数据库ID删除向量库中的数据
        
        Args:
            db_id: 数据库记录ID
            
        Returns:
            删除是否成功
        """
        try:
            vector_id = f"kb_{db_id}"
            
            # 检查是否存在该ID的向量
            existing = self.collection.get(ids=[vector_id])
            if existing['ids']:
                self.collection.delete(ids=[vector_id])
                return True
            else:
                # 如果不存在，返回True（视为已删除）
                return True
        except Exception as e:
            print(f"Error deleting vector for db_id {db_id}: {str(e)}")
            return False
    
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
    
class DocumentVectorStore:
    """文档向量存储类，用于处理上传文档的向量存储"""
    
    def __init__(self):
        if not CHROMA_AVAILABLE:
            raise ImportError("chromadb is not installed. Please install it with: pip install chromadb")
        if not TEXT_SPLITTER_AVAILABLE:
            raise ImportError("langchain_text_splitters is not installed. Please install it with: pip install langchain-text-splitters")
            
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()
        self.client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    def process_and_store_document(self, file_path: str, collection_name: str = None) -> Dict:
        """
        处理并存储文档到向量库
        
        Args:
            file_path: 文件路径
            collection_name: 集合名称，如果为None则使用文件名（不含扩展名）
            
        Returns:
            处理结果信息
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # 如果没有指定collection_name，使用文件名（不含扩展名）
        if collection_name is None:
            collection_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # 读取文档内容
        content = parse_document(file_path)
        if not content.strip():
            raise ValueError("Document content is empty")
        
        # 使用RecursiveCharacterTextSplitter进行文本切片
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "！", "？", ". ", "! ", "? ", " ", ""]
        )
        
        chunks = text_splitter.split_text(content)
        
        if not chunks:
            raise ValueError("No text chunks generated from document")
        
        # 创建或获取集合
        collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        
        # 准备批量插入的数据
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # 只添加非空的chunk
                documents.append(chunk)
                metadatas.append({
                    "source": file_path,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
                ids.append(f"doc_{i}")
        
        if not documents:
            raise ValueError("No valid documents to store")
        
        # 批量添加到向量库
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return {
            "collection_name": collection_name,
            "total_chunks": len(documents),
            "file_path": file_path,
            "status": "success"
        }
    
    def search_in_document_collection(self, collection_name: str, query: str, n_results: int = 5) -> List[Dict]:
        """
        在指定文档集合中搜索
        
        Args:
            collection_name: 集合名称
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        try:
            collection = self.client.get_collection(name=collection_name)
        except ValueError:
            raise ValueError(f"Collection not found: {collection_name}")
        
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        search_results = []
        if results['documents'] and results['metadatas']:
            for i in range(len(results['documents'][0])):
                search_results.append({
                    "content": results['documents'][0][i],
                    "source": results['metadatas'][0][i]['source'],
                    "chunk_index": results['metadatas'][0][i]['chunk_index'],
                    "total_chunks": results['metadatas'][0][i]['total_chunks'],
                    "distance": results['distances'][0][i] if results['distances'] else None
                })
        
        return search_results