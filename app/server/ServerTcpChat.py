import pickle
import socket
from PyQt5.QtCore import QThread
import threading
import logging

logging.basicConfig(format="%(message)s", level=logging.INFO)

# source: https://hackernoon.com/creating-command-line-based-chat-room-using-python-oxu3u33
class TcpChat(QThread):
    def __init__(self, threadVideoPlay, threadAudioPlay):
        super().__init__()
        self.threadVideoPlay = threadVideoPlay
        self.threadAudioPlay = threadAudioPlay

        self.host_name = socket.gethostname()
        self.IP = socket.gethostbyname(self.host_name)
            #'192.168.0.106'  # LocalHost
        self.PORT = 7976  # Choosing unreserved port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization
        self.server.bind((self.IP, self.PORT))  # binding host and port to socket
        self.server.listen()

        self.clients = []
        self.nicknames = []
        self.clients_address = []

        print(f'Listening for TCP chat connections on {self.IP}:{self.PORT}...')

    def broadcast(self, message):  # broadcast function declaration
        msg = pickle.dumps({"user": 'server', "msg": message})
        for client in self.clients:
            client.send(msg)


    def handle(self, client):
        while True:
            try:  # recieving valid messages from client
                user_msg = pickle.loads(client.recv(1024))
                command = user_msg["msg"]
                self.broadcast('{}: {}'.format(user_msg["user"], command))
                print('{}: {}'.format(user_msg["user"], command))

                if command == '/play':
                    self.threadVideoPlay.playSignal.emit()
                    self.threadAudioPlay.playSignal.emit()
                elif command == '/pause':
                    self.threadVideoPlay.stopSignal.emit()
                    self.threadAudioPlay.stopSignal.emit()
                elif command[:7] == '/skipto':
                    try:
                        frame_nb = int(command[8:])
                        video_was_paused = self.threadVideoPlay.is_paused
                        self.threadVideoPlay.stopSignal.emit()
                        self.threadAudioPlay.stopSignal.emit()
                        self.threadVideoPlay.move_progress_bar_client(frame_nb)
                        self.threadAudioPlay.move_slider_client(frame_nb)
                        if not video_was_paused:
                            self.threadVideoPlay.playSignal.emit()
                            self.threadAudioPlay.playSignal.emit()
                    except Exception as e:
                        logging.error('Error reading frame skip command\n', e)

            except:  # removing clients
                index = self.clients.index(client)
                self.clients.remove(client)
                client.close()

                clients_address = [client.getpeername()[0] for client in self.clients]
                self.threadVideoPlay.update_clients(clients_address)
                self.threadAudioPlay.update_clients(clients_address)

                nickname = self.nicknames[index]
                self.broadcast('{} left!'.format(nickname))
                print('{} left!'.format(nickname))
                self.nicknames.remove(nickname)
                break

    def receive(self):  # accepting multiple clients
        while True:
            client, address = self.server.accept()
            print("Connected with {}".format(str(address)))
            client.send(pickle.dumps({"msg": 'NICKNAME'}))
            nickname = pickle.loads(client.recv(1024))["msg"]
            self.nicknames.append(nickname)
            self.clients.append(client)

            self.clients_address = [client.getpeername()[0] for client in self.clients]
            self.threadVideoPlay.update_clients(self.clients_address)
            self.threadAudioPlay.update_clients(self.clients_address)

            print("Hello {}!".format(nickname))
            self.broadcast("{} joined!".format(nickname))
            client.send(pickle.dumps({"msg": 'Connected to server!'}))
            thread = threading.Thread(target=self.handle, args=(client,))
            thread.start()

    def update_threads(self, video_thread, audio_thread):
        self.threadVideoPlay = video_thread
        self.threadAudioPlay = audio_thread
        self.threadVideoPlay.update_clients(self.clients_address)
        self.threadAudioPlay.update_clients(self.clients_address)

    def run(self):
        self.receive()
