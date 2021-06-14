import cv2
from ffpyplayer.player import MediaPlayer

filename = 'D:/github/OpenParty/app/server/vids/parrot.mp4'
play = MediaPlayer(filename)
video = cv2.VideoCapture(filename)

while True:
    grabbed, frame = video.read()
    audio_frame, val = play.get_frame()
    if not grabbed:
        print("End of video")
        break
    if cv2.waitKey(28) & 0xFF == ord("q"):
        break
    cv2.imshow("Video", frame)
    if val != 'eof' and audio_frame is not None:
        # audio
        img, t = audio_frame
    video.release()
    cv2.destroyAllWindows()
