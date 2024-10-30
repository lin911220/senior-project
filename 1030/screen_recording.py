import cv2
import numpy as np
import pyautogui
import time
import os
import struct

def record_screen(duration, fps=10, client_socket=None):
    # 獲取螢幕大小
    screen_size = pyautogui.size()

    # 生成時間戳以用於文件名
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_filename = f"screen_recording.mp4"

    # 定義編解碼器並創建 VideoWriter 對象
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # 使用 'mp4v' 格式為 MP4
    out = cv2.VideoWriter(output_filename, fourcc, fps, screen_size)

    start_time = time.time()
    while True:
        # 捕獲螢幕
        img = pyautogui.screenshot()

        # 將圖像轉換為 numpy 數組
        frame = np.array(img)

        # 將其從 RGB（pyautogui）轉換為 BGR（OpenCV）
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        # 寫入幀
        out.write(frame)

        # 檢查是否超過指定的持續時間
        if time.time() - start_time > duration:
            break

    # 釋放 VideoWriter 對象
    out.release()
    print(f"螢幕錄影已保存至 {output_filename}")

    # 可選地發送文件
    if client_socket:
        send_file(output_filename, client_socket)

def send_file(filename, client_socket):
    """
    通過網絡將文件發送到指定的客戶端套接字。

    參數：
        filename (str): 要發送的文件名。
        client_socket (socket.socket): 用於通信的套接字對象。
    """
    # 獲取文件大小並準備文件信息標頭
    file_size = os.path.getsize(filename)
    # 填充文件名到128字节
    filename_padded = bytes(os.path.basename(filename).encode('utf-8')).ljust(128, b'\x00')
    # 打包文件信息
    fileinfo = struct.pack("128sl", filename_padded, file_size)

    client_socket.send(fileinfo)
    # 分塊發送文件
    with open(filename, "rb") as file:
        while True:
            data = file.read(1024)  # 每次讀取 1024 字節
            if not data:
                break
            client_socket.sendall(data)
    client_socket.send(b"END")
    print(f"{filename} 已成功發送")

    os.remove(filename)