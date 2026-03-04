import uuid
from datetime import datetime
import requests
from PyPDF2 import PdfReader
from docx import Document
from bs4 import BeautifulSoup

# 生成唯一ID
def generate_id(prefix=""):
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

# 格式化时间
def format_time():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 解析文档（PDF/Word/TXT）
def parse_document(file_path):
    content = ""
    if file_path.endswith(".pdf"):
        reader = PdfReader(file_path)
        for page in reader.pages:
            content += page.extract_text() or ""
    elif file_path.endswith(".docx"):
        doc = Document(file_path)
        for para in doc.paragraphs:
            content += para.text + "\n"
    elif file_path.endswith(".txt"):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    return content.strip()

# 爬取远程知识库内容
def crawl_knowledge_base(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # 提取文本内容，过滤标签
        return soup.get_text(strip=True, separator="\n")
    except Exception as e:
        print(f"知识库爬取失败：{e}")
        return ""

# 机器人回复风格格式化
def format_reply(reply_content, style="正式"):
    if style == "亲切":
        return f"您好呀～{reply_content} 如果还有其他问题，随时问我哦！"
    elif style == "简洁":
        return reply_content.strip()
    else: # 正式
        return f"您好，{reply_content} 如有其他疑问，请继续咨询。"