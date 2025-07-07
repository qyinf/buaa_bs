import streamlit as st
from dbManager import checkRepeatName,get_password_hash,checkPassword,addNewUser,checkAdmin
from Chat import main
from Vector import vectorPreview
from Neo4j import graphPreview

# 初始化会话状态
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'admin' not in st.session_state:
    st.session_state.admin = False
if 'usname' not in st.session_state:
    st.session_state.usname = ""
if 'manage_knowledge' not in st.session_state:
    st.session_state.manage_knowledge = False
if 'manage_graph' not in st.session_state:
    st.session_state.manage_graph = False

st.markdown("""
    <style>
        .sidebar .sidebar-content {
            background-color: #e8f1f8; /* 浅蓝色背景 */
        }
        .stButton>button {
            background-color: #4a90e2; /* 浅蓝色按钮 */
            color: white;
            font-size: 18px;
            border-radius: 5px;
            padding: 10px 20px;
            border: none;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #357ABD; /* 按钮悬停时更深的蓝色 */
        }
        .stTextInput>div>div>input {
            border-radius: 5px;
            padding: 10px;
            border: 1px solid #4a90e2; /* 输入框边框颜色 */
        }
        .stForm>form {
            background-color: #ffffff; /* 表单背景白色 */
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* 添加阴影 */
        }
        h1, h2 {
            color: #2c3e50; /* 深蓝色标题 */
        }
        .stAlert {
            background-color: #f4f8fb; /* 提示框背景颜色 */
            border-left: 4px solid #4a90e2; /* 提示框左侧边框颜色 */
        }
    </style>
""", unsafe_allow_html=True)


def login_page():
    with st.form("login_form"):
        st.title("登录")
        username = st.text_input("用户名", value="")
        password = st.text_input("密码", value="", type="password")
        submit = st.form_submit_button("登录")

        if submit:
            user_cred = checkRepeatName(username)
            if not user_cred:
                st.error("用户名不存在")
            elif user_cred and checkPassword(username,password):
                st.success("登录成功！")
                st.session_state.logged_in = True
                st.session_state.admin = checkAdmin(username)
                st.session_state.usname = username
                st.rerun()
            else:
                st.error("密码错误，请重新输入。")


def register_page():
    with st.form("register_form"):
        st.title("注册")
        new_username = st.text_input("设置用户名", value="")
        new_password = st.text_input("设置密码", value="", type="password")
        register_submit = st.form_submit_button("注册")

        if register_submit:
            # if new_username in credentials:
            # TODO
            if checkRepeatName(new_username):
                st.error("用户名已存在，请使用其他用户名。")
            else:
                addNewUser(username=new_username,password=new_password)
                st.success(f"用户 {new_username} 注册成功！请登录。")
                st.rerun()


if __name__ == "__main__":
    if st.session_state.manage_knowledge:
        vectorPreview(st.session_state.usname)
    elif st.session_state.manage_graph:
        graphPreview(st.session_state.usname)
    elif not st.session_state.logged_in:
        # 显示注册和登录选项
        st.sidebar.title("导航")
        app_mode = st.sidebar.selectbox("选择操作", ["登录", "注册"])
        if app_mode == "登录":
            login_page()
        elif app_mode == "注册":
            register_page()
    else:
        main(st.session_state.admin, st.session_state.usname)
