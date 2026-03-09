import sqlite3
from datetime import datetime
from core.common.config import DB_PATH

# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 1. 客户会话记录表
    c.execute('''CREATE TABLE IF NOT EXISTS customer_sessions
                 (session_id TEXT PRIMARY KEY, user_id TEXT, create_time TEXT, 
                  last_msg_time TEXT, context TEXT, feedback_status TEXT)''')
    # 2. 错误反馈表
    c.execute('''CREATE TABLE IF NOT EXISTS error_feedback
                 (feedback_id TEXT PRIMARY KEY, session_id TEXT, question TEXT, 
                  robot_reply TEXT, error_type TEXT, error_desc TEXT, 
                  create_time TEXT, fix_status TEXT, fix_time TEXT)''')
    # 3. 元智能体生成记录表
    c.execute('''CREATE TABLE IF NOT EXISTS agent_generations
                 (gen_id TEXT PRIMARY KEY, manager_id TEXT, create_time TEXT, 
                  robot_template TEXT, robot_config TEXT, robot_status TEXT)''')
    # 4. 管理者操作日志表
    c.execute('''CREATE TABLE IF NOT EXISTS manager_oper_logs
                 (log_id TEXT PRIMARY KEY, manager_id TEXT, role TEXT, 
                  oper_time TEXT, oper_content TEXT)''')
    # 5. 特定问题执行流程表
    c.execute('''CREATE TABLE IF NOT EXISTS specific_question_flows
                 (key TEXT PRIMARY KEY, desc TEXT, flow TEXT, status TEXT, prompt TEXT)''')
    # 6. 爬虫结果表 - NEW
    c.execute('''CREATE TABLE IF NOT EXISTS crawler_results
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  seed_url TEXT NOT NULL,
                  current_url TEXT NOT NULL,
                  raw_content TEXT,
                  questions TEXT,
                  answers TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# 通用数据库操作函数
def db_query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    res = c.fetchall()
    conn.close()
    return res

def db_execute(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(sql, params)
    conn.commit()
    conn.close()
    return c.lastrowid

# 初始化数据库
init_db()