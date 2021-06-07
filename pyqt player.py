# TODO: (needs sync) send audio packets through UDP socket and sync with video
# TODO: move code into separate .py files for each module
# TODO: replace send frames to hardcoded client addresses with list of addresses from chat TCP connection
# DONE: fix crash when trying to open another video
# TODO: fix TCP chat so it updates all clients when receiving message
import base64
import os
import socket
import sys
from PyQt5 import QtGui, QtCore, QtWidgets
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.uic import loadUi
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QLabel, QGraphicsScene, QGraphicsView
import cv2
from datetime import timedelta
import queue
import time
import logging, random, imutils
import os
import pyaudio, wave, subprocess
import select
import pickle
import threading

from PyQt5.QtCore import QRunnable, Qt, QThreadPool
from pynput import keyboard

BASE_DIR = os.path.dirname(__file__)
path = BASE_DIR.replace('\\'[0], '/')

logging.basicConfig(format="%(message)s", level=logging.INFO)


class VideoGen(QThread):
    # queue for storing multiple frames from video file ready to be processed
    def __init__(self, cap, q):
        super().__init__()
        self.cap = cap
        self.q = q

    def destroy(self):
        self.terminate()
        self.deleteLater()

    def run(self):
        # set how much pixels should be sent using the UDP socket
        # too much will cause lag because of too large packets
        WIDTH = 600

        while self.cap.isOpened():
            try:
                # to be used for updating the slider position
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))

                ret, frame = self.cap.read()
                # frame = imutils.resize(frame, width=WIDTH)
                # print('adding frame to queue')

                frame = imutils.resize(frame, width=WIDTH)
                self.q.put((ret, frame, current_frame))
                # logging.info('{} {}'.format('insert into q ', current_frame))
                # print('sent frame: ', self.q.qsize())
                # frame_no += 1
                # print('after add frame')
            except Exception as e:
                logging.error(e)
                break
                # os._exit(1)
        print('Player closed')
        BREAK = True
        self.cap.release()


class PlayVideo(QThread):
    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()
    is_paused = True

    def destroy(self):
        self.terminate()
        self.deleteLater()

    def __init__(self, cap, q, progresslabel, progressBar, frame, totalFrames, fps,
                 playButton, stopButton, fpsLabel):

        super().__init__()

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.playTimer)
        self.stopSignal.connect(self.stopTimer)

        # ui properties inherited from MainWindow class
        self.cap = cap
        self.playButton = playButton
        self.stopButton = stopButton
        self.fpsLabel = fpsLabel

        self.q = q
        self.progresslabel = progresslabel
        self.progressBar = progressBar
        self.frame = frame
        self.totalFrames = totalFrames
        self.fps = fps
        self.TS = (0.5 / self.fps)

        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(totalFrames)

        # timer to loop the frame displaying function
        self.timer = QTimer()
        self.timer.timeout.connect(self.playVideo)
        # self.timer.start(self.TS * 1000)

        # bind play/pause buttons
        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        # properties for slider functionality
        self.slider_pressed = False
        self.progressBar.sliderPressed.connect(self.when_slider_pressed)
        self.progressBar.sliderReleased.connect(self.moveProgressBar)

        # properties to sync the FPS with how fast the frames are processed
        self.fps2 = 0
        self.st = 0
        self.frames_to_count = 1
        self.cnt = 0

        # properties for UDP socket to send the frames to clients
        self.BUFF_SIZE = 65536
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        host_name = socket.gethostname()
        self.host_ip = socket.gethostbyname(host_name)
        print('udp ip connect: ', self.host_ip)
        port = 9688
        self.socket_address = (self.host_ip, port)
        # self.server_socket.bind(self.socket_address)
        print('Listening at:', self.socket_address)

        self.cnt = 1

        self.fps_mean = 0

    # convert frame number to timestamp
    def frame_to_timestamp(self, frame, fps):
        return str(timedelta(seconds=(frame / fps)))

    # restart the timer when play button is pressed
    def playTimer(self):
        self.timer.start(self.TS * 1000)
        self.is_paused = False

    # stop the timer when pause button is pressed
    def stopTimer(self):
        self.timer.stop()
        self.is_paused = True

    # stop updating the progress bar while slider is clicked
    def when_slider_pressed(self):
        self.slider_pressed = True

    # when slider is released try to empty queue and move to selected frame number
    def moveProgressBar(self):
        try:
            self.timer.stop()
            for i in range(self.q.qsize()): self.q.get()
            time.sleep(0.05)
            if not self.is_paused:
                self.timer.start(self.TS * 1000)
        except Exception as e:
            logging.error(e)
        value = self.progressBar.value()
        self.cap.set(1, value)
        self.slider_pressed = False

    def moveProgressBarClient(self, value):
        for i in range(self.q.qsize()): self.q.get()
        time.sleep(0.05)
        self.cap.set(1, value)

    # function for displaying and sending frames
    # will be ran in a loop using the timer to sync the FPS
    def playVideo(self):
        # read image from queue
        ret, frame, current_frame_no = self.q.get()

        # if self.cnt == 1: print(frame)

        if ret is True:
            progress = self.frame_to_timestamp(current_frame_no, self.fps) + ' / ' \
                       + self.frame_to_timestamp(self.totalFrames, self.fps)
            self.progresslabel.setText(progress)
            # logging.info(current_frame)
            # logging.info(threading.current_thread().ident)

            # stop updating slider in UI while clicked while continuing playback
            if self.slider_pressed is False:
                self.progressBar.setValue(current_frame_no)

            try:
                encoded, buffer = cv2.imencode('.jpeg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                encoded_frame = base64.b64encode(buffer)

                # TODO: send total_frames and fps only once in the TCP connection
                msg_pair = {"frame_nb": current_frame_no,
                            "total_frames": self.totalFrames,
                            "frame": encoded_frame,
                            "fps": self.fps}
                packed_message = pickle.dumps(msg_pair)

                # if self.cnt == 1: print(buffer)
                # self.cnt += 1

                # TODO: send the message to the list of clients stored from the TCP socket
                client_addr_new1 = ('192.168.0.106', 9689)  # client ip
                client_addr_new2 = ('192.168.0.106', 9685)  # others
                client_addr_new = [client_addr_new1, client_addr_new2]
                for client in client_addr_new:
                    self.server_socket.sendto(packed_message, client)
            except Exception as e:
                logging.error(e)

            # convert image to RGB format
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            # get image infos
            height, width, channel = frame.shape
            # print(height, width, channel)
            step = channel * width
            # create QImage from image
            qImg = QImage(frame.data, width, height, step, QImage.Format_RGB888)

            # show image in UI frame label
            self.frame.setPixmap(QPixmap.fromImage(qImg))

            # self.threadAudio.playAudioSignal.emit()

            # because frame processing time if fluctuating
            # we need to sync it to the FPS fetched from the metadata
            self.fpsLabel.setText(str(round(self.fps2, 1)))

            # self.fps_mean += self.fps2
            # self.fps_mean /= 2
            # print(self.fps_mean)

            if self.cnt == self.frames_to_count:
                try:
                    self.fps2 = (self.frames_to_count / (time.time() - self.st))
                    self.st = time.time()
                    self.cnt = 0
                    if self.fps2 > self.fps:
                        self.TS += 0.001
                    elif self.fps2 < self.fps:
                        self.TS -= 0.001
                    else:
                        pass
                except Exception as e:
                    print(e)
            self.cnt += 1

            # restart and update timer with new TS
            self.timer.start(self.TS * 1000)

        else:
            print('return false')
            progress = str(current_frame_no) + ' / ' \
                       + str(self.totalFrames)
            self.progresslabel.setText(progress)
            self.progressBar.setValue(current_frame_no)


class LocalAudio(QThread):
    playAudioSignal = pyqtSignal()

    playSignal = pyqtSignal()
    stopSignal = pyqtSignal()

    def destroy(self):
        self.terminate()
        self.deleteLater()

    def __init__(self, playButton, stopButton, progressBar, audioProgressLabel, video_fps):
        super().__init__()

        self.playAudioSignal.connect(self.playAudio)
        self.audioProgressLabel = audioProgressLabel
        self.video_fps = video_fps

        # signals used by TCP chat thread in order to play/pause the timer from the exterior
        self.playSignal.connect(self.playTimer)
        self.stopSignal.connect(self.stopTimer)

        # seek audio to slider position when released
        self.progressBar = progressBar
        self.progressBar.sliderReleased.connect(self.moveSlider)

        # bind play/pause buttons
        self.playButton = playButton
        self.stopButton = stopButton
        self.playButton.clicked.connect(self.playTimer)
        self.stopButton.clicked.connect(self.stopTimer)

        self.host_name = socket.gethostname()
        self.host_ip = '192.168.0.106'  # server ip
        print('audio host at ', self.host_ip)
        self.port = 9633

        self.BUFF_SIZE = 65536
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)

        # self.audio_socket.bind((self.host_ip, (self.port)))
        self.CHUNK = 1024
        self.wf = wave.open("temp.wav")
        self.p = pyaudio.PyAudio()
        print('server listening at', (self.host_ip, (self.port)), self.wf.getframerate())
        self.stream = self.p.open(format=self.p.get_format_from_width(self.wf.getsampwidth()),
                                  channels=self.wf.getnchannels(),
                                  rate=self.wf.getframerate(),
                                  input=True, output=True,
                                  frames_per_buffer=self.CHUNK)
        print('audio framerate', self.wf.getframerate())
        self.data = None
        self.sample_rate = self.wf.getframerate()

        self.client_addr = ('192.168.0.106', 9634) # client ip

        self.timer = QTimer()
        self.timer.timeout.connect(self.playAudio)

        self.total_frames = self.wf.getnframes()

    # restart the timer when play button is pressed
    def playTimer(self):
        self.timer.start(1000 * 0.8 * self.CHUNK / self.sample_rate)
        self.is_paused = False

    # stop the timer when pause button is pressed
    def stopTimer(self):
        self.timer.stop()
        self.is_paused = True

    def moveSlider(self):
        try:
            self.timer.stop()
            value = self.progressBar.value()
            time.sleep(0.05)
            if not self.is_paused:
                self.timer.start(1000 * 0.8 * self.CHUNK / self.sample_rate)

            self.wf.setpos(int((value / self.video_fps) * self.sample_rate))
            # print('skipped to ', (value/25))
        except Exception as e:
            logging.error(e)

    def moveSliderClient(self, value):
        time.sleep(0.05)
        self.wf.setpos(int((value / self.video_fps) * self.sample_rate))

    def playAudio(self):
        # print('chunk {}, sample rate {}, second {}'.format(self.wf.tell(),
        #                                                    self.sample_rate,
        #                                                    self.wf.tell()/self.sample_rate))

        self.data = self.wf.readframes(self.CHUNK)
        current_position = self.wf.tell()
        progress = str(timedelta(seconds=(current_position / self.sample_rate))) + ' / ' \
                   + str(timedelta(seconds=(self.total_frames / self.sample_rate)))
        self.audioProgressLabel.setText(progress)

        self.audio_socket.sendto(self.data, self.client_addr)
        self.stream.write(self.data)


class TcpChat(QThread):
    def __init__(self, threadVideoPlay, threadAudioPlay):
        super().__init__()
        self.threadVideoPlay = threadVideoPlay
        self.threadAudioPlay = threadAudioPlay

        self.IP = '192.168.0.106'  # LocalHost
        self.PORT = 7976  # Choosing unreserved port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization
        self.server.bind((self.IP, self.PORT))  # binding host and port to socket
        self.server.listen()

        self.clients = []
        self.nicknames = []

        print(f'Listening for TCP chat connections on {self.IP}:{self.PORT}...')

    def broadcast(self, message):  # broadcast function declaration
        for client in self.clients:
            client.send(message)

    def handle(self, client):
        while True:
            try:  # recieving valid messages from client
                message = client.recv(1024)
                self.broadcast(message)

                command = message.decode('ascii')
                print(command)
            except:  # removing clients
                index = self.clients.index(client)
                self.clients.remove(client)
                client.close()
                nickname = self.nicknames[index]
                self.broadcast('{} left!'.format(nickname).encode('ascii'))
                self.nicknames.remove(nickname)
                break

    def receive(self):  # accepting multiple clients
        while True:
            client, address = self.server.accept()
            print("Connected with {}".format(str(address)))
            client.send('NICKNAME'.encode('ascii'))
            nickname = client.recv(1024).decode('ascii')
            self.nicknames.append(nickname)
            self.clients.append(client)
            print("Nickname is {}".format(nickname))
            self.broadcast("{} joined!".format(nickname).encode('ascii'))
            client.send('Connected to server!'.encode('ascii'))
            thread = threading.Thread(target=self.handle, args=(client,))
            thread.start()

    def update_threads(self, video_thread, audio_thread):
        self.threadVideoPlay = video_thread
        self.threadAudioPlay = audio_thread

    def run(self):
        self.receive()


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        loadUi('open.ui', self)
        self.frame.setScaledContents(True)
        self.setWindowTitle('OpenParty Server')
        self.totalFrames = 0
        self.fps = 0
        self.q = queue.Queue(maxsize=10)
        self.openButton.clicked.connect(self.openFile)

        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()
        self.threadChat = QThread()

    # initialize threads for each component
    def startVideoGen(self):
        self.threadVideoGen = VideoGen(self.cap, self.q)
        self.threadVideoGen.start()

    def startVideoPlay(self):
        self.threadVideoPlay = PlayVideo(self.cap, self.q, self.progresslabel, self.progressBar, self.frame,
                                         self.totalFrames, self.fps, self.playButton, self.stopButton,
                                         self.fpsLabel)
        self.threadVideoPlay.start()

    def startAudio(self):
        self.threadAudio = LocalAudio(self.playButton, self.stopButton,
                                      self.progressBar, self.audioProgressLabel,
                                      self.fps)
        self.threadAudio.start()

    def startTcpChat(self):
        if not self.threadChat.isRunning():
            print('starting chat thread...')
            self.threadChat = TcpChat(self.threadVideoPlay, self.threadAudio)
            self.threadChat.start()
        else:
            self.threadChat.update_threads(self.threadVideoPlay, self.threadAudio)


    # after opening file start threads for each component
    def openFile(self):
        if self.threadVideoPlay.isRunning():
            self.threadVideoPlay.stopSignal.emit()
        if self.threadAudio.isRunning():
            self.threadAudio.stopSignal.emit()

        if self.threadVideoGen.isRunning():
            self.threadVideoGen.destroy()
        if self.threadVideoPlay.isRunning():
            self.threadVideoPlay.destroy()
        if self.threadAudio.isRunning():
            self.threadAudio.destroy()
        self.threadVideoGen = QThread()
        self.threadVideoPlay = QThread()
        self.threadAudio = QThread()

        self.videoFileName = QFileDialog.getOpenFileName(self, 'Select Video File')
        self.file_name = list(self.videoFileName)[0]
        self.cap = cv2.VideoCapture(self.file_name)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        print('Opening file {} with fps {}'.format(list(self.videoFileName)[0], self.fps))

        # extract and convert audio from the video file into a temp.wav to be sent
        command = "ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {} -y".format(self.videoFileName[0], 'temp.wav')
        os.system(command)

        self.totalFrames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.startAudio()
        self.startVideoGen()
        self.startVideoPlay()
        self.startTcpChat()

    # when exiting the UI make sure the threads are closed properly
    def closeEvent(self, event):
        print('closed manually')
        self.threadVideoGen.destroy()
        self.threadVideoPlay.destroy()
        self.threadAudio.destroy()
        self.threadChat.terminate()


# run main component
app = QApplication(sys.argv)
widget = MainWindow()
widget.show()
sys.exit(app.exec_())
