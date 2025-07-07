import shutil
from passlib.context import CryptContext
import pymysql
import json
import os
from models import SiliconFlowLLM,SiliconFlowEmbeddings
from langchain_core.documents import Document
from langchain_chroma import Chroma



pwd_context = CryptContext(schemes='bcrypt',deprecated = "auto")
parent_path = "./chroma_db/"
embeddings = SiliconFlowEmbeddings()
collection_name="my_docs"

def connectDatabase():
    connection = pymysql.connect(
        host="localhost",  # 数据库地址，默认为localhost
        user="root",  # 数据库用户名
        password="",  # 数据库密码
        database="mybs",  # 数据库名称
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = connection.cursor()
    return connection,cursor

def closeDatabase(connect, cursor):
    connect.close()
    cursor.close()


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str,hashed_password: str) -> bool:
    return pwd_context.verify(plain_password,hashed_password)

def checkRepeatName(username) -> bool:
    connect,cursor = connectDatabase()
    try :
        query = "SELECT COUNT(*) FROM users WHERE username = %s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect,cursor)
    if result['COUNT(*)'] == 0 :
        return False
    else:
        return True

def checkPassword(username,password) -> bool:
    connect,cursor = connectDatabase()
    try :
        query = "SELECT password FROM users WHERE username = %s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
        hashed_password = result['password']
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect,cursor)
    return verify_password(password,hashed_password)


# TODO
def addNewUser(username,password) -> bool:
    connect,cursor = connectDatabase()
    try:
        query = "INSERT INTO users (username,password,folderpath) VALUES (%s, %s,%s)"
        hashed_password = get_password_hash(password)
        # 为该用户新建一个知识库文件夹
        user_path = addNewFolder(username)
        cursor.execute(query,(username,hashed_password,user_path))
        connect.commit()
        print(f"用户%s创建成功",username)
        # 新建一个会话窗口
        insertNewChatWindow(username,1)
        # 为该用户添加数据库
        # TODO
        addKnowledgeBase(username,"demo")
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect,cursor)


def addNewFolder(username) -> bool:
    # 先为该用户新建一个文件夹
    persist_path = os.path.join(parent_path,username)
    os.makedirs(persist_path,exist_ok=True)
    return persist_path


def checkAdmin(username) -> bool:
    connect,cursor = connectDatabase()
    try :
        query = "SELECT is_admin FROM users WHERE username = %s"
        cursor.execute(query,(username,))
        result = cursor.fetchone()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect,cursor)
    return result['is_admin']


# ok zyf
def getHistory(username,windownum) -> list:
    connect,cursor = connectDatabase()
    try :
        query = "SELECT messages FROM history WHERE username = %s AND windownum = %s"
        cursor.execute(query,(username,windownum))
        result = cursor.fetchone()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect,cursor)
    return result['messages']


def storeHistory(username, messages, windowNum, question) -> bool:
    connect, cursor = connectDatabase()
    try:
        # 如果是新建的时候
        if question == "":
            update_query = "UPDATE history SET historyname = %s WHERE username = %s AND windownum = %s"
            cursor.execute(update_query, ("新的对话窗口", username, windowNum))
            query = "UPDATE history SET messages = %s WHERE username = %s AND windownum = %s"
            cursor.execute(query, (messages, username, windowNum))
            connect.commit()
            return


        # 查询 historyname
        query = "SELECT historyname FROM history WHERE username = %s AND windownum = %s"
        cursor.execute(query, (username, windowNum))
        result = cursor.fetchone()
        
        # 如果 historyname 是 "新的对话窗口"，更新为 question
        if result['historyname'] == "新的对话窗口":
            update_query = "UPDATE history SET historyname = %s WHERE username = %s AND windownum = %s"
            cursor.execute(update_query, (question, username, windowNum))
        
        # 更新 messages
        query = "UPDATE history SET messages = %s WHERE username = %s AND windownum = %s"
        cursor.execute(query, (messages, username, windowNum))
        connect.commit()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)

def getWindowNum(username) -> list:
    connect, cursor = connectDatabase()
    try:
        query = "SELECT windownum FROM history WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchall()
        window_nums = [row['windownum'] for row in result]
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)
    return window_nums



def insertNewChatWindow(username, windownum) -> bool:
    connect, cursor = connectDatabase()
    try:
        query = "INSERT INTO history (username, windownum, messages,historyname) VALUES (%s, %s, %s,%s)"
        initial_message = '[{"role": "assistant", "content": "您好，我是您的科研助手。"}]'
        cursor.execute(query, (username, windownum, initial_message,"新的对话窗口"))
        connect.commit()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)


# 每新建一个用户的时候，都为其初始化一个向量数据库
# TODO
def create_db(username,userpath,dbname):
    # 在当前数据库下新建一个目录
    # 这里应该不需要parentpath了
    persist_path = os.path.join(userpath,dbname)
    os.makedirs(persist_path,exist_ok=True)
    collection_name = username + "_" + dbname + "_collection"
    vector_db = Chroma(
        persist_directory=persist_path,
        embedding_function=embeddings,
        collection_name=collection_name
    )
    # vector_db.persist()
    return persist_path

# TODO
def addKnowledgeBase(username,dbname):
    connect, cursor = connectDatabase()
    try:
        # 先查询用户的文件夹位置
        query = "SELECT folderpath FROM users WHERE username=%s"
        cursor.execute(query,(username))
        result = cursor.fetchone()
        # 看看文件夹存储的对不对
        # 知识库的默认名字叫demo，后续可以改
        path = create_db(username,result['folderpath'],dbname)
        # 执行插入语句
        query = "INSERT INTO knowledgebase (username, basePos,dbname) VALUES (%s, %s,%s)"
        cursor.execute(query, (username, path,dbname))
        connect.commit()
        print(f"用户%s的知识库创建成功", username)
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)


# ok zyf
def getVectorDb(username,dbname):
    connect, cursor = connectDatabase()
    try:
        query = "SELECT basePos FROM knowledgebase WHERE username = %s AND dbname = %s"
        cursor.execute(query, (username, dbname))
        result = cursor.fetchone()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)
# TODO 暂时不知道result长啥样
    return load_db(result['basePos'],username + "_" + dbname + "_collection")


# ok zyf
def load_db(basePos,collection_name):
    vector_db = Chroma(
        persist_directory=basePos,
        embedding_function=SiliconFlowEmbeddings(),
        collection_name=collection_name
    )
    return vector_db


def getUserDb(username) -> list:
    connect, cursor = connectDatabase()
    try:
        query = "SELECT dbname FROM knowledgebase WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchall()
        dbnames = [row['dbname'] for row in result]
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)
    return dbnames

def getAllHistoryNames(username) -> list:
    connect, cursor = connectDatabase()
    try:
        query = "SELECT historyname, windownum FROM history WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchall()
        history_list = [[row['historyname'], row['windownum']] for row in result]
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)
    return history_list


def deleteKnowledgaBase(username, dbname):
    connect, cursor = connectDatabase()
    if dbname == "demo":
        print("默认知识库不能删除")
        return
    try:
        # 先查询用户的文件夹位置
        # query = "SELECT basePos FROM knowledgebase WHERE username=%s AND dbname=%s"
        # cursor.execute(query,(username, dbname))
        # result = cursor.fetchone()
        # path = result['basePos']
        # 删除数据库
        # TODO 会显示进程无法访问，so先不管了
        # if os.path.exists(path):
        #     shutil.rmtree(path)
        #     print(f"用户%s的知识库删除成功", username)
        # else:
        #     print(f"用户%s的知识库不存在", username)
        # 删除数据库里面的
        query = "DELETE FROM knowledgebase WHERE username=%s AND dbname=%s"
        cursor.execute(query, (username, dbname))
        print("没有删掉吗")
        connect.commit()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)


def deleteChatWindow(username, windownum):
    connect, cursor = connectDatabase()
    try:
        query = "DELETE FROM history WHERE username = %s AND windownum = %s"
        cursor.execute(query, (username, windownum))
        connect.commit()
    except Exception as e:
        connect.rollback()
        raise e
    finally:
        closeDatabase(connect, cursor)