import os
import platform
from pathlib import Path
import shutil
import time

def shutdown():
    system_platform = platform.system()
    if system_platform == 'Windows':
        os.system('shutdown /s /t 1')  # Windows close
    elif system_platform == 'Linux':
        os.system('sudo shutdown now')  # Linux close
    elif system_platform == 'Darwin':
        os.system('sudo shutdown -h now')  # macOS close
    else:
        print("Unsupported OS for shutdown")

if __name__ == '__main__':
    # 取得當前工作目錄
    current_directory = Path.cwd()

    # 刪除當前目錄中的檔案和目錄，保留 close.py
    for item in current_directory.iterdir():
        if item.is_file() and item.name != 'close.py':
            item.unlink()
            print(f"已刪除檔案: {item}")
        elif item.is_dir():
            shutil.rmtree(item)
            print(f"已刪除目錄及其內容: {item}")

    # 等待 8 秒以確保檔案)已刪除
    # 執行關機
    
    time.sleep(2)
    shutdown()
    
    # 刪除 close.py 自己
    close_file = current_directory / 'close.py'
    if close_file.exists():
        close_file.unlink()
        print(f"已刪除檔案: {close_file}")

    
