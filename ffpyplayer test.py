# from ffpyplayer.player import MediaPlayer
# import time
#
# filename = "vids/test.mkv"
# player = MediaPlayer(filename)
# val = ''
# while val != 'eof':
#      frame, val = player.get_frame()
#      if val != 'eof' and frame is not None:
#          img, t = frame
#          # display img


from ffpyplayer.player import MediaPlayer
import numpy as np
import cv2

filename = "vids/test.mkv"

player = MediaPlayer(filename)
val = ''
while val != 'eof':
    frame, val = player.get_frame()
    if val != 'eof' and frame is not None:
        img, t = frame
        w = img.get_size()[0]
        h = img.get_size()[1]
        arr = np.uint8(np.asarray(list(img.to_bytearray()[0])).reshape(h,w,3)) # h - height of frame, w - width of frame, 3 - number of channels in frame
        cv2.imshow('test', arr)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.destroyAllWindows()
            break