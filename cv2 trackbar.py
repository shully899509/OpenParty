import cv2
import numpy as np

# function called by trackbar, sets the next frame to be read
def getFrame(frame_nr):
    global video
    video.set(cv2.CAP_PROP_POS_FRAMES, frame_nr)

#  function called by trackbar, sets the speed of playback
def setSpeed(val):
    global playSpeed
    playSpeed = max(val,1)

# open video
video = cv2.VideoCapture("vids\\test.avi")
# get total number of frames
nr_of_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
# create display window
cv2.namedWindow("Video")
# set wait for each frame, determines playbackspeed
playSpeed = 50
# add trackbar
cv2.createTrackbar("Frame", "Video", 0,nr_of_frames,getFrame)
cv2.createTrackbar("Speed", "Video", playSpeed,100,setSpeed)

# main loop
while 1:
    # Get the next videoframe
    ret, frame = video.read()

    # show frame, break the loop if no frame is found
    if ret:
        cv2.imshow("Video", frame)
        # update slider position on trackbar
        # NOTE: this is an expensive operation, remove to greatly increase max playback speed
        cv2.setTrackbarPos("Frame","Video", int(video.get(cv2.CAP_PROP_POS_FRAMES)))
    else:
        break

    # display frame for 'playSpeed' ms, detect key input
    key = cv2.waitKey(playSpeed)

    # stop playback when q is pressed
    if key == ord('q'):
        break

# release resources
video.release()
cv2.destroyAllWindows()