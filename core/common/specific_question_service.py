from core.common.db import db_query, db_execute


class SpecificQuestionService:
    """特殊问题流程服务类，用于管理特殊问题流程的查询和处理"""
    
    @staticmethod
    def get_enabled_specific_questions():
        """
        获取所有启用状态的特殊问题流程
        
        Returns:
            list: 包含启用的特殊问题流程字典的列表，每个字典包含key和desc字段
        """
        try:
            sql = "SELECT key, desc FROM specific_question_flows WHERE status = 'active'"
            results = db_query(sql)
            return [{"key": result[0], "desc": result[1]} for result in results]
        except Exception as e:
            # 如果查询失败，返回空列表而不是抛出异常
            print(f"Error querying enabled specific questions: {e}")
            return []
    
    @staticmethod
    def format_specific_questions_for_prompt(specific_questions):
        """
        将特殊问题列表格式化为prompt中使用的字符串格式
        
        Args:
            specific_questions (list): 特殊问题列表，每个元素包含key和desc字段
            
        Returns:
            str: 格式化后的字符串，格式为 '-"key":desc'，每行一个，前面加上适当的缩进
        """
        if not specific_questions:
            return ""
        
        formatted_lines = []
        for item in specific_questions:
            key = item.get("key", "")
            desc = item.get("desc", "")
            formatted_line = f'- "{key}": {desc}'
            formatted_lines.append(formatted_line)
        
        # 添加前缀说明和换行
        result = "\n            Specific Questions (enabled):\n            " + "\n            ".join(formatted_lines)
        return result
    
    @staticmethod
    def get_specific_question_flow(key):
        """
        获取指定key的特殊问题流程配置
        
        Args:
            key (str): 特殊问题流程的key
            
        Returns:
            dict: 包含prompt和flow字段的字典，如果未找到则返回None
        """
        try:
            sql = "SELECT prompt, flow FROM specific_question_flows WHERE key = ? AND status = 'active'"
            results = db_query(sql, (key,))
            if results:
                return {
                    "prompt": results[0][0],
                    "flow": results[0][1]
                }
            return None
        except Exception as e:
            print(f"Error querying specific question flow for key '{key}': {e}")
            return None
    
    @staticmethod
    def create_special_question_flow(key: str, desc: str, flow: str, status: str = "active") -> bool:
        """
        创建特殊问题流程
        
        Args:
            key (str): 流程唯一标识
            desc (str): 流程描述
            flow (str): 流程定义
            status (str): 状态，默认为"active"
            
        Returns:
            bool: 创建是否成功
        """
        try:
            db_execute(
                "INSERT INTO specific_question_flows (key, desc, flow, status, prompt) VALUES (?, ?, ?, ?, ?)",
                (key, desc, flow, status, None)
            )
            return True
        except Exception as e:
            raise Exception(f"创建特殊问题流程失败: {str(e)}")
    
    @staticmethod
    def update_special_question_flow(key: str, desc: str, flow: str, status: str = "active") -> bool:
        """
        更新特殊问题流程
        
        Args:
            key (str): 流程唯一标识
            desc (str): 流程描述
            flow (str): 流程定义
            status (str): 状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            db_execute(
                "UPDATE specific_question_flows SET desc = ?, flow = ?, status = ? WHERE key = ?",
                (desc, flow, status, key)
            )
            return True
        except Exception as e:
            raise Exception(f"更新特殊问题流程失败: {str(e)}")
    
    @staticmethod
    def delete_special_question_flow(key: str) -> bool:
        """
        删除特殊问题流程
        
        Args:
            key (str): 流程唯一标识
            
        Returns:
            bool: 删除是否成功
        """
        try:
            db_execute("DELETE FROM specific_question_flows WHERE key = ?", (key,))
            return True
        except Exception as e:
            raise Exception(f"删除特殊问题流程失败: {str(e)}")
    
    @staticmethod
    def get_all_special_question_flows():
        """
        获取所有特殊问题流程（包括禁用的）
        
        Returns:
            list: 所有特殊问题流程的列表
        """
        try:
            sql = "SELECT key, desc, flow, status, prompt FROM specific_question_flows"
            results = db_query(sql)
            flows = []
            for result in results:
                flow = {
                    "key": result[0],
                    "desc": result[1],
                    "flow": result[2],
                    "status": result[3],
                    "prompt": result[4] or ""
                }
                flows.append(flow)
            return flows
        except Exception as e:
            raise Exception(f"获取所有特殊问题流程失败: {str(e)}")