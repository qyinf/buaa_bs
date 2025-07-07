import streamlit as st
import tempfile
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader,TextLoader
from langchain_unstructured import UnstructuredLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata
from dbManager import getVectorDb, getUserDb, addKnowledgeBase,deleteKnowledgaBase
from models import SiliconFlowEmbeddings, SiliconFlowLLM


# 导入环境变量
load_dotenv()

# 向量化工具
embedding = SiliconFlowEmbeddings()

# 调用大模型进行清洗
client = SiliconFlowLLM()


def add_file(vector_db,uploaded_file,chunk_size,chunk_overlap):
    text = ""
    file_ext = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    try:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext == ".txt":
            text += uploaded_file.getvalue().decode("utf-8")
        else:
            loader = UnstructuredLoader(tmp_file_path)
            text = loader.load()
        # documents = loader.load()
    except Exception as e:
        st.error(f"文件加载失败: {str(e)}")
        os.remove(tmp_file_path)
        st.stop()
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
    # TODO
    # 这里需要设置可以让用户自己调节
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    if file_ext == ".txt":
        texts = text_splitter.split_text(text)
        vector_db.add_texts(texts)
        st.success("文本添加成功")
    else:
        # 清洗数据
        texts = text_splitter.split_documents(text)
        filtered_texts = filter_complex_metadata(texts)
        vector_db.add_documents(filtered_texts)
        st.success("文本添加成功")


def previewFile(uploaded_file):
    text = ""
    file_ext = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.name) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name
    try:
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext == ".txt":
            text += uploaded_file.getvalue().decode("utf-8")
        else:
            loader = UnstructuredLoader(tmp_file_path)
            text = loader.load()
        # documents = loader.load()
    except Exception as e:
        st.error(f"文件加载失败: {str(e)}")
        os.remove(tmp_file_path)
        st.stop()
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)
    return text


def washFile(content):
    with open('washprompt.md', 'r', encoding='utf-8') as f:
        prompt_content = f.read()
        combined_content = f"{prompt_content}\n\现在按照要求处理下列文字：\n{content}"
        response = client._call(str(combined_content))
        return response


def vectorPreview(username):
    st.title("知识库管理")

    # 首先导入本次使用的向量数据库
    # 默认是第一个

    with st.sidebar:
        # 新增选择知识库的功能
        db_options = getUserDb(username)
        selected_db = st.selectbox('请选择知识库:', db_options)
        if st.button("切换知识库"):
            if selected_db:
                st.session_state.vector_db = getVectorDb(username,selected_db)
                st.session_state.vector_name = selected_db

        new_db_name = st.text_input("输入新知识库名称")
        if st.button("新增知识库"):
            if new_db_name:
                addKnowledgeBase(username, new_db_name)
                st.success(f"知识库 {new_db_name} 创建成功")
                db_options = getUserDb(username)

        uploaded_file = st.file_uploader("上传文件新建知识库", type=["pdf", "txt", "docx", "md"])

        chunk_size = 0
        chunk_overlap = 0
        if uploaded_file:
            chunk_size = st.number_input("请输入分块大小", min_value=1, max_value=1000, value=50)
            chunk_overlap = st.number_input("请输入重叠大小", min_value=0, max_value=1000, value=5)

        if st.button("新增文件到知识库"):
            if uploaded_file:
                add_file(st.session_state.vector_db, uploaded_file,chunk_size,chunk_overlap)
        
        if st.button("删除当前知识库"):
            if (st.session_state.vector_name != "demo"):
                deleteKnowledgaBase(username,st.session_state.vector_name)
            else:
                st.warning("默认知识库不能删除")

        if st.button("返回对话窗口"):
            st.session_state.manage_knowledge = False
            st.session_state.logged_in = True
            # 防止不同用户信息冲突
            st.rerun()

        # 添加输入框

    st.markdown("文件处理与上传")
    # 显示上传的文件内容
    if uploaded_file is not None:
        content = previewFile(uploaded_file)
        cleaned_content = st.text_area("预览文本", content, height=300)
        if st.button("清洗文档"):
            cleaned_content = washFile(content)
            st.success("清洗已完成")
            st.text_area("预览文本", cleaned_content, height=300)




# TODO
# 可以创新的部分
def search_knowledge_base(vector_db,question,k):
    # 检索知识库的逻辑
    return vector_db.similarity_search(question,int(k))
