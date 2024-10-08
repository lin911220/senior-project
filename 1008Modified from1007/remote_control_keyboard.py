from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController

def type_key_at_mouse_position(event_type, key):
    mouse = MouseController()
    keyboard = KeyboardController()
    
    # Get current mouse position
    mouse_position = mouse.position
    
    # Move mouse to current position
    mouse.position = mouse_position

    try:
        # Check and handle special keys
        if hasattr(Key, key):
            key_attr = getattr(Key, key)
        else:
            key_attr = key

        if event_type == "press":
            keyboard.press(key_attr)
        elif event_type == "release":
            keyboard.release(key_attr)
    except (AttributeError, Exception):
        # Silently handle errors
        pass