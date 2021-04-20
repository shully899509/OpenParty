import cv2


def nothing(emp):
    pass

#dummy check commit author

video = 'vids/test.avi'
cv2.namedWindow('some video')
cap = cv2.VideoCapture(video)
frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
loop_flag = 0
pos = 0
cv2.createTrackbar('time', 'some video', 0, frames, nothing)


while 1:
    if loop_flag == pos:
        loop_flag = loop_flag + 1
        cv2.setTrackbarPos('time', 'some video', loop_flag)
    else:
        pos = cv2.getTrackbarPos('time', 'some video')
        loop_flag = pos
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
    ret, img = cap.read()
    cv2.putText(img, 'No habla espanol', (200, 400), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1.5, (0, 0, 255))
    cv2.imshow('some video', img)

    key = cv2.waitKey(1)
    if key == ord('q') & loop_flag == frames:
        break
    if key == ord('p'):
        cv2.waitKey(-1) #wait until any key is pressed
cap.release()
cv2.destroyAllWindows()