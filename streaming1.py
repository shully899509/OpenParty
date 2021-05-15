import cv2, imutils, time
import queue, os
import threading

q = queue.Queue(maxsize=10)
filename = 'vids\\test.avi'

vid = cv2.VideoCapture(filename)
FPS = vid.get(cv2.CAP_PROP_FPS)
print('FPS:', FPS)
# FPS: 29.97

TS = 1 / FPS
print('TS:', TS)


# generating stream of frames in queue
def video_stream_gen():
    # deposit video frames to a queue
    WIDTH = 400
    while (vid.isOpened()):
        _, frame = vid.read()
        frame = imutils.resize(frame, width=WIDTH)
        q.put(frame)
        print('Queue size:', q.qsize())
    vid.release()


fps, st, frames_to_count, cnt = (0, 0, 1, 0)
t1 = threading.Thread(target=video_stream_gen(), args=())
t1.start()

while (True):
    print('output video frames')
    frame = q.get()
    frame = cv2.putText(frame, 'FPS:' + str(round(fps, 1)), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    if cnt == frames_to_count:
        try:
            fps = (frames_to_count / (time.time() - st))
            st = time.time()
            cnt = 0
        except:
            pass
    cnt += 1
    cv2.imshow('TRANSMITTING VIDEO', frame)
    key = cv2.waitKey(int(1)) & 0xFF
    if key == ord('q'):
        os._exit(1)
