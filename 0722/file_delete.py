from pathlib import Path
import shutil

# 取得當前工作目錄
current_directory = Path.cwd()

for item in current_directory.iterdir():
    print(item)

# !!! 他真的會刪除 我下面的先註解掉防止不小心按到

# 刪除當前目錄中的檔案和目錄
# for item in current_directory.iterdir():
#     if item.is_file():
#         item.unlink()
#         print(f"已刪除檔案: {item}")
#     elif item.is_dir():
#         shutil.rmtree(item)
#         print(f"已刪除目錄及其內容: {item}")
