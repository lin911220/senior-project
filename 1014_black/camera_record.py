import cv2
import pyaudio
import wave
import subprocess
import os
import struct
import threading
import time

def record_audio(output_audio, duration=10, format=pyaudio.paInt16, channels=1, rate=44100, chunk=1024):
    audio = pyaudio.PyAudio()
    stream = audio.open(format=format, channels=channels, rate=rate, input=True, frames_per_buffer=chunk)
    frames = []

    for _ in range(0, int(rate / chunk * duration)):
        data = stream.read(chunk)
        frames.append(data)

    stream.stop_stream()
    stream.close()
    audio.terminate()

    with wave.open(output_audio, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(audio.get_sample_size(format))
        wf.setframerate(rate)
        wf.writeframes(b''.join(frames))

def record_video(output_video, duration=10, fps=20, frame_size=(640, 480)):
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_video, fourcc, fps, frame_size)

    for _ in range(int(fps * duration)):  # fps * duration = total frames
        ret, frame = cap.read()
        if ret:
            out.write(frame)
        else:
            break

    cap.release()
    out.release()

def merge_audio_video(video_file, audio_file, output_file):
    command = [
        'ffmpeg',
        '-i', video_file,
        '-i', audio_file,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_file
    ]
    subprocess.run(command, check=True)

def send_file(filename, client_socket):
    file_size = os.path.getsize(filename)
    filename_padded = bytes(os.path.basename(filename).encode('utf-8')).ljust(128, b'\x00')
    fileinfo = struct.pack("128sl", filename_padded, file_size)
    client_socket.send(fileinfo)

    with open(filename, "rb") as file:
        while True:
            data = file.read(1024)
            if not data:
                break
            client_socket.sendall(data)

    client_socket.send(b"END")
    print(f"{filename} 文件发送完毕")

def record_video_with_audio(client, duration=10):
    # Add timestamp to file names to ensure uniqueness
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    audio_file = f'audio_{timestamp}.wav'
    video_file = f'video_{timestamp}.avi'
    output_file = f'camera_vidio.mp4'

    # Create threads for recording audio and video
    audio_thread = threading.Thread(target=record_audio, args=(audio_file, duration))
    video_thread = threading.Thread(target=record_video, args=(video_file, duration))

    audio_thread.start()
    video_thread.start()

    audio_thread.join()
    video_thread.join()

    # Merge audio and video
    merge_audio_video(video_file, audio_file, output_file)

    # Send the final output file
    send_file(output_file, client)

    # Clean up temporary files
    os.remove(video_file)
    os.remove(audio_file)
    os.remove(output_file)  # 删除本地视频文件
