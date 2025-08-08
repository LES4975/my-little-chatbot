import cv2
import numpy as np
import subprocess
import shlex
import time
import pigpio

# pigpio 초기화
pi = pigpio.pi()
if not pi.connected:
    raise Exception("pigpio 데몬이 실행 중이 아닙니다. 'sudo pigpiod'를 먼저 실행하세요.")

# 서보 핀 설정 (GPIO 18: 좌우, GPIO 19: 상하)
SERVO_X_PIN = 18
SERVO_Y_PIN = 19

def move_servo(pin, offset):
    # offset은 -1.0 ~ 1.0 범위, 1500us를 기준으로 ±400us 조정
    pulse = int(1500 + offset * 400)
    pulse = max(1100, min(1900, pulse))  # 안전한 범위 제한
    pi.set_servo_pulsewidth(pin, pulse)

# 얼굴 검출기 로드
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# libcamera-vid MJPEG 스트림 실행
cmd = 'libcamera-vid --inline --nopreview -t 0 --codec mjpeg --width 640 --height 480 --framerate 30 -o -'
process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

buffer = b""
frame_width = 640
frame_height = 480

# 초기값 설정
smooth_face_x = frame_width // 2
smooth_face_y = frame_height // 2
prev_offset_x = 0.0
prev_offset_y = 0.0
DEADZONE = 0.1 # 0.2
THRESHOLD = 0.05 # 0.07
move_interval = 0.1  # 100ms 주기
last_move_time = time.time()

try:
    while True:
        buffer += process.stdout.read(4096)
        start = buffer.find(b'\xff\xd8')
        end = buffer.find(b'\xff\xd9')

        if start != -1 and end != -1:
            jpg = buffer[start:end+2]
            buffer = buffer[end+2:]

            frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
            if frame is not None:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3, minSize=(20, 20))

                for (x, y, w, h) in faces:
                    print(x, y, w, h)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

                    # 얼굴 중심 좌표 계산 및 smoothing
                    face_center_x = x + w // 2
                    face_center_y = y + h // 2
                    smooth_face_x = smooth_face_x * 0.8 + face_center_x * 0.2
                    smooth_face_y = smooth_face_y * 0.8 + face_center_y * 0.2

                    # 오프셋 계산 (-1.0 ~ 1.0)
                    offset_x = (smooth_face_x - (frame_width / 2)) / (frame_width / 2)
                    offset_y = (smooth_face_y - (frame_height / 2)) / (frame_height / 2)

                    # 범위 제한
                    offset_x = max(min(offset_x, 1.0), -1.0)
                    offset_y = max(min(offset_y, 1.0), -1.0)

                    now = time.time()
                    if now - last_move_time > move_interval:
                        if abs(offset_x - prev_offset_x) > THRESHOLD and abs(offset_x) > DEADZONE:
                            move_servo(SERVO_X_PIN, -offset_x)
                            prev_offset_x = offset_x

                        if abs(offset_y - prev_offset_y) > THRESHOLD and abs(offset_y) > DEADZONE:
                            move_servo(SERVO_Y_PIN, -offset_y)
                            prev_offset_y = offset_y

                        last_move_time = now

                    break  # 가장 큰 얼굴 하나만 추적

                cv2.imshow('Live Camera (libcamera)', frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
finally:
    process.terminate()
    cv2.destroyAllWindows()
    pi.set_servo_pulsewidth(SERVO_X_PIN, 0)
    pi.set_servo_pulsewidth(SERVO_Y_PIN, 0)
    pi.stop()