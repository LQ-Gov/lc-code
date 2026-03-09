from langgraph.graph import StateGraph, START, END
from core.agent.state import MetaAgentState
from core.agent.nodes import (
    parse_uploaded_docs, parse_demand, select_robot_template,
    generate_robot_config, verify_robot, is_demand_understood_cond,
    is_robot_generated_cond
)
from core.common.utils import generate_id

# 构建元智能体StateGraph
def build_meta_agent_graph():
    graph = StateGraph(MetaAgentState)

    # 添加节点
    graph.add_node("parse_uploaded_docs", parse_uploaded_docs)
    graph.add_node("parse_demand", parse_demand)
    graph.add_node("select_template", select_robot_template)
    graph.add_node("generate_robot_config", generate_robot_config)
    graph.add_node("verify_robot", verify_robot)

    # 定义节点流转
    graph.add_edge(START, "parse_uploaded_docs")
    graph.add_edge("parse_uploaded_docs", "parse_demand")
    # 条件边：是否理解需求
    graph.add_conditional_edges("parse_demand", is_demand_understood_cond, {
        "select_template": "select_template",
        "end": END
    })
    graph.add_edge("select_template", "generate_robot_config")
    # 条件边：是否生成机器人成功
    graph.add_conditional_edges("generate_robot_config", is_robot_generated_cond, {
        "verify_robot": "verify_robot",
        "end": END
    })
    graph.add_edge("verify_robot", END)

    # 编译图
    return graph.compile()

# 初始化元智能体图
meta_agent_graph = build_meta_agent_graph()

# 元智能体调用入口
def meta_agent_invoke(manager_id: str, user_query: str, uploaded_docs: list[str] = None):
    # 初始化生成ID
    gen_id = generate_id("gen")
    # 初始化状态
    initial_state = {
        "manager_id": manager_id,
        "gen_id": gen_id,
        "user_query": user_query,
        "uploaded_docs": uploaded_docs or [],
        "doc_contents": [],
        "demand_parse_result": "",
        "robot_template": "",
        "robot_config": {},
        "is_demand_understood": False,
        "is_robot_generated": False,
        "verify_result": None,
        "error": None
    }
    # 运行图
    result = meta_agent_graph.invoke(initial_state)
    return result