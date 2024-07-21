import os
import platform

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

# if __name__ == '__main__':
#     shutdown()
