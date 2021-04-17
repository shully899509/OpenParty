import numpy as np
import cv2
import sys
import time

# cap = cv2.VideoCapture(0)
#dummy commit

filename = "vids/test.avi"

# info
print("Python:", sys.version)
print("CV2:   ", cv2.__version__)
print("File:    ", filename)

global cap

try:
    cap = cv2.VideoCapture(filename)
    if not cap.isOpened():
        raise NameError('Could not find file')
except cv2.error as e:
    print("Error opening video: ", e)
    exit()
except Exception as e:
    print("Other error: ", e)
    exit()
else:
    print("everything ok I guess")


def make_720p():
    cap.set(3, 1366)
    cap.set(4, 768)


def web(cap):
    make_720p()

    while (True):
        # Capture frame-by-frame
        ret, frame = cap.read()

        # Our operations on the frame come here
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Display the resulting frame
        cv2.imshow('original', frame)
        cv2.imshow('original but gray', gray)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # When everything done, release the capture
    cap.release()
    cv2.destroyAllWindows()


def vid_info(cap):
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')

    if int(major_ver) < 3:
        fps = cap.get(cv2.cv.CV_CAP_PROP_FPS)
        print("Frames per second using video.get(cv2.cv.CV_CAP_PROP_FPS): {0}".format(fps))
        waitTime = (int)(1000.0 / cap.get(cv2.cv.CV_CAP_PROP_FPS))
    else:
        fps = cap.get(cv2.CAP_PROP_FPS)
        print("Frames per second using video.get(cv2.CAP_PROP_FPS) : {0}".format(fps))
        waitTime = (int)(1000.0 / cap.get(cv2.CAP_PROP_FPS))

    print("waitTime: ", waitTime)
    return fps


fps = vid_info(cap)
delay = int(1000 / fps)
make_720p()

def vid(cap):
    while cap.isOpened():
        ret, frame = cap.read()
        cv2.imshow('original', frame)
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


vid(cap)
