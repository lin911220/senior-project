from pynput.mouse import Controller, Button
import ctypes

def get_screen_resolution():
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    return screen_width, screen_height

def handle_mouse_control(message):
    mouse = Controller()
    screen_width, screen_height = get_screen_resolution()

    if message.startswith("move"):
        try:
            _, x, y = message.split()
            x = int(x)
            y = int(y)
            # 直接使用接收到的坐标作为绝对坐标
            if 0 <= x < screen_width and 0 <= y < screen_height:
                mouse.position = (x, y)
                print(f"Mouse moved to {x}, {y}")
            else:
                print(f"Received coordinates out of bounds: {x}, {y}")
        except Exception as e:
            print(f"Error moving mouse: {e}")
    elif message.lower() == 'press right':
        mouse.click(Button.right)
        print("Right mouse button pressed")
    elif message.lower() == 'press left':
        mouse.click(Button.left)
        print("Left mouse button pressed")
    elif message.lower() == 'roller up':
        mouse.scroll(0, 5)  # 滚动一个单位向上
        print("Mouse wheel scrolled up")
    elif message.lower() == 'roller down':
        mouse.scroll(0, -5)  # 滚动一个单位向下
        print("Mouse wheel scrolled down")
    elif message.lower() == 'double click left':
        mouse.click(Button.left, 2)
        print("Left mouse button double clicked")
    elif message.lower() == 'double click right':
        mouse.click(Button.right, 2)
        print("Left mouse button double clicked")
