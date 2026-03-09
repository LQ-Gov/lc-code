class BaseParser:
    """
    解析脚本基类
    所有具体的解析脚本都应该继承此类并实现supports和parse方法
    """
    
    def supports(self, url: str, content: str) -> bool:
        """
        判断是否支持解析传入的网页内容格式
        
        Args:
            url (str): 网页URL
            content (str): 网页内容
            
        Returns:
            bool: 如果支持解析返回True，否则返回False
        """
        raise NotImplementedError("子类必须实现supports方法")
    
    def parse(self, url: str, content: str) -> list:
        """
        解析网页内容，返回其中包含的问题和答案
        
        Args:
            url (str): 网页URL
            content (str): 网页内容
            
        Returns:
            list: 包含QA对的字典列表，格式为 [{'question': '...', 'answer': '...'}, ...]
        """
        raise NotImplementedError("子类必须实现parse方法")