import streamlit as st
import time
import ast
from dbManager import getHistory,storeHistory,deleteChatWindow,insertNewChatWindow,getVectorDb,getAllHistoryNames,getUserDb
from langchain_core.documents import Document
from langchain_chroma import Chroma
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from models import SiliconFlowLLM,SiliconFlowEmbeddings
from llama_index.core import PropertyGraphIndex, Settings
from llama_index.graph_stores.neo4j import Neo4jPropertyGraphStore
from langchain.chains.router import MultiRouteChain
from langchain.chains.router import MultiRouteChain, RouterChain
from langchain.chains.llm import LLMChain





# 导入环境变量!!
load_dotenv()


# 知识图谱的配置
# Settings.llm = SiliconFlowLLM()
# Settings.embed_model = SiliconFlowEmbeddings()
# graph_store = Neo4jPropertyGraphStore(
#     username="neo4j",
#     password="123456abc",
#     url="neo4j://localhost:7474",
#     database="neo4j",
# )
# index_query = PropertyGraphIndex.from_existing(
#     property_graph_store=graph_store,
# )





def search(vector_db,query, k):
    ans = []
    docs = vector_db.similarity_search(query,k=k)
    for doc in docs:
        ans.append(doc.page_content)
    return ans



## 这一部分是生成回答
def generateNewQuery(history,query_content,docs):
    # query_engine = index_query.as_query_engine(
    #     include_text=True,
    #     similarity_top_k=15,
    # )
    # nodes = query_engine.retrieve(query_content)
    # nodes_info = ""
    # for node in nodes:
    #     nodes_info += node.text + "\n"

    prompt_template = """
        你是一个航天器测试领域的专家，擅长有关航天器测试的代码生成和问题解答。你需要根据提供的文档的解析信息(documents)(可能会包含有关航天器测试的示例代码、历史故障信息等)、知识图谱的推理信息(Graph_content)，上下文信息以及问题(query)综合考虑后回复最佳结果，需要使用中文回答问题。
        如果知识图谱的信息和问题无关，你需要忽略知识图谱的信息，这需要你自己分辨。

        Query: {query}
        Documents: {documents}
        Graph Content: {graph_content}

        1. 使用流式文档的解析信息(Documents)和知识图谱的推理信息(Graph_content)以及上下文信息来回答用户的问题。如果你不知道答案，就说你不知道，不要试图编造答案。
        2. 对于流式文档的解析信息(Documents)和知识图谱的推理信息(Graph_content),不需要全部使用，你需要根据问题的需要选择合适的信息。不相关的信息可能会降低回答的质量。
        3. 回复应该使用便于阅读的格式输出。输出格式应该有段落，数字小标，标点符号和适当的换行。
        """

    prompt_template = prompt_template.format(graph_content="暂时没有关联图谱",query=query_content,documents = docs)


    # 调整回答样式
    history_openai_format = []
    for human, assistant in history:
        if isinstance(human, str) and isinstance(assistant, str):
            history_openai_format.append({"role": "user", "content": human})
            history_openai_format.append({"role": "assistant", "content": assistant})
        else:
            continue
    history_openai_format.append({"role": "user", "content": prompt_template})

    return history_openai_format

# 这个是调用我的仆人
client = SiliconFlowLLM()

def initHistory():
    st.session_state.history = [{"role": "assistant", "content": "您好，我是您的科研助手。"}]

def main(is_admin, username):
    # 设置背景图片并添加模糊和淡化效果
    st.markdown(
        """
        <style>
        .stApp {
            background: url('buaa.jpg') no-repeat center center fixed;
            background-size: cover;
        }
        .stApp::before {
            content: "";
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: inherit;
            filter: blur(8px) brightness(0.85) grayscale(0.1);
            opacity: 0.5;
            z-index: -1;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title(f"航天测试对话助手")
    with st.sidebar:
        col1, col2 = st.columns([0.6, 0.6])
        with col1:
            st.image("buaa.jpg", use_container_width=True)
        st.caption(
            f"""<p align="left">欢迎您，{'管理员' if is_admin else '用户'}！当前版本：{1.0}</p>""",
            unsafe_allow_html=True,
        )

        # 初始的时候是一个新开始对话的页面
        # 这里默认为0比较用户不友好
        window_options = getAllHistoryNames(username)
        if "active_window_index" not in st.session_state:
            st.session_state.active_window_index = 0 
        if "history" not in st.session_state:
            initHistory()
        if "windowNum" not in st.session_state:
            st.session_state.windowNum = len(window_options)
        if 'vector_db' not in st.session_state:
            st.session_state.vector_db = getVectorDb(username, "demo")
        if 'vector_name' not in st.session_state:
            st.session_state.vector_name = "demo"
        



        # 新建
        if st.button('新建对话窗口'):
            insertNewChatWindow(username,st.session_state.windowNum + 1)
            st.session_state.windowNum += 1
            window_options = getAllHistoryNames(username)

        # 选择
        selected_window = st.selectbox('请选择对话窗口:', [option[0] for option in window_options])
        if st.button("切换对话窗口"):
            for option in window_options:
                if option[0] == selected_window:
                    st.session_state.active_window_index = option[1]
                    break
            history = getHistory(username, st.session_state.active_window_index)
            st.session_state.history = ast.literal_eval(history)

        # 仅当 active_window_index 不为 0 时显示清空聊天记录按钮
        if st.session_state.active_window_index != 0:
            if st.button("清空聊天记录"):
                msg = [{"role": "assistant", "content": "您好，我是您的科研助手。"}]
                storeHistory(username,str(msg),st.session_state.active_window_index,"")
                initHistory()
            if st.button("删除当前对话"):
                deleteChatWindow(username,st.session_state.active_window_index)
                st.session_state.windowNum -= 1
                window_options = getAllHistoryNames(username)
                if len(window_options) > 0:
                    st.session_state.active_window_index = window_options[0][1]
                    history = getHistory(username, st.session_state.active_window_index)
                    st.session_state.history = ast.literal_eval(history)
                else:
                    st.session_state.active_window_index = 0
                    initHistory()
                

        # 添加空白区域以增加间距
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # 查询该用户的知识库
        if st.button("管理知识库"):
            st.session_state.manage_knowledge = True
            st.rerun()
        if st.button("查看知识图谱"):
            st.session_state.manage_graph = True
            st.rerun()

        db_options = getUserDb(username)
        selected_db = st.selectbox('请选择知识库:', db_options)
        if st.button("切换知识库"):
            if selected_db:
                st.session_state.vector_db = getVectorDb(username,selected_db)
                st.session_state.vector_name = selected_db

        if st.button("返回登录"):
            st.session_state.logged_in = False
            st.session_state.admin = False
            # 防止不同用户信息冲突
            del st.session_state.history
            del st.session_state.windowNum
            del st.session_state.active_window_index
            del st.session_state.vector_db
            del st.session_statd.vector_name
            st.rerun()

    for message in st.session_state.history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


    if query := st.chat_input("Ask me anything!"):
        # 如果为0的话默认就是新建了一个对话窗口!!!!!
        if st.session_state.active_window_index == 0:
            insertNewChatWindow(username,st.session_state.windowNum + 1)
            st.session_state.windowNum += 1
            window_options = getAllHistoryNames(username)
            st.session_state.active_window_index = st.session_state.windowNum


        st.session_state.history.append({"role": "user", "content": query})
        with st.chat_message("user"):
            st.markdown(query)
        # 生成问题
        docs = search(st.session_state.vector_db, query, 3)
        newQuery = generateNewQuery(st.session_state.history, query, docs)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            assistant_response = client._call(str(query))
            for chunk in assistant_response.split():
                full_response += chunk + " "
                time.sleep(0.05)
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown("")
            # 添加显示知识图谱信息和知识库信息部分
        # with st.expander("显示知识图谱信息"):
        #         st.markdown("测试系统 → 包含 → {测试建模与管理, 任务编排与执行, 数据采集与分析, 可视化系统, 知识服务中心}")
        # with st.expander("显示知识库信息"):
        #         if docs:
        #             for idx, doc in enumerate(docs, start=1):
        #                 st.markdown(f"**文档 {idx}:**")
        #                 st.write(doc)
        #                 st.markdown("---")  # 添加分隔线
        #         else:
        #             st.markdown("系统共分为五大模块：1）测试建模与管理，支持任务模型设计；2）任务编排与执行，负责任务流管理与调度；3）数据采集与分析，实现多源异构数据处理；4）可视化系统，提供状态监控与展示；5）知识服务中心，支持本体构建与知识推理。")

        st.session_state.history.append({"role": "assistant", "content": full_response})
        storeHistory(username, str(st.session_state.history),st.session_state.active_window_index,query)










