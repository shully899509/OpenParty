import socket
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
import queue
import logging, random, imutils
import pyaudio, wave, subprocess
import threading

logging.basicConfig(format="%(message)s", level=logging.INFO)


class AudioRec(QThread):
    def __init__(self):
        super().__init__()

        self.host_name = socket.gethostname()
        self.host_ip = '192.168.0.106'  # client ip
        print(self.host_ip)
        self.port = 9631
        self.q = queue.Queue(maxsize=100)

        self.BUFF_SIZE = 65536
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.audio_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, self.BUFF_SIZE)
        self.socket_address = (self.host_ip, self.port)
        self.audio_socket.bind(self.socket_address)
        self.p = pyaudio.PyAudio()
        self.CHUNK = 1024
        self.stream = self.p.open(format=self.p.get_format_from_width(2),
                                  channels=2,
                                  rate=44100,
                                  output=True,
                                  frames_per_buffer=self.CHUNK)

        self.timer = QTimer()
        self.timer.timeout.connect(self.play_audio)
        self.timer.start(1000 * 0.8 * self.CHUNK / 44100)

        t1 = threading.Thread(target=self.get_audio_data, args=())
        t1.start()
        print('Now Playing...')

    def get_audio_data(self):
        while True:
            try:
                self.frame, _ = self.audio_socket.recvfrom(self.BUFF_SIZE)
                self.q.put(self.frame)
            except BlockingIOError:
                pass
            except Exception as e:
                logging.error(e)

    def play_audio(self):
        if not self.q.empty():
            frame = self.q.get()
            self.stream.write(frame)
