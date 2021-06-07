import socket
from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
import threading


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
