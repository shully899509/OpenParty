import pickle
import socket
from PyQt5.QtCore import QThread
import threading
import logging

logging.basicConfig(format="%(message)s", level=logging.INFO)

# source: https://hackernoon.com/creating-command-line-based-chat-room-using-python-oxu3u33
class TcpChat(QThread):
    def __init__(self, threadVideoPlay, threadAudioPlay, chat_box, message_box):
        super().__init__()
        self.threadVideoPlay = threadVideoPlay
        self.threadAudioPlay = threadAudioPlay

        self.host_name = socket.gethostname()
        self.IP = socket.gethostbyname(self.host_name)
        #self.IP = '92.81.39.98'
        # self.IP = '127.0.0.1'
        self.PORT = 7976  # Choosing unreserved port

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization
        self.server.bind((self.IP, self.PORT))  # binding host and port to socket
        self.server.listen()

        self.clients = []
        self.nicknames = []
        self.clients_address = []

        self.chat_box = chat_box
        self.message_box = message_box
        self.message_box.returnPressed.connect(self.write)

        print(f'Listening for TCP chat connections on {self.IP}:{self.PORT}...')
        self.chat_box.append(f'Listening for TCP chat connections on {self.IP}:{self.PORT}...')

    def broadcast(self, message):  # broadcast function declaration
        msg = pickle.dumps({"user": 'server', "msg": message})
        for client in self.clients:
            client.send(msg)

    # server messages on chat box
    def write(self):
        try:
            message = self.message_box.text()
            if len(message) < 1024:
                if self.started:
                    self.chat_box.append('server: {}'.format(message))
                    self.broadcast('server: {}'.format(message))
            else:
                self.chat_box.append("Message was too long. Character limit is 1024")
            self.message_box.setText("")
        except Exception as e:
            logging.error('write message err: {}'.format(e))

    def handle(self, client):
        while True:
            try:  # recieving valid messages from client
                user_msg = pickle.loads(client.recv(1024))
                client_message = user_msg["msg"]
                if client_message not in ['/play', '/pause'] and client_message[:7] != '/skipto':
                    self.broadcast('{}: {}'.format(user_msg["user"], client_message))
                print('{}: {}'.format(user_msg["user"], client_message))
                self.chat_box.append('{}: {}'.format(user_msg["user"], client_message))

                if client_message == '/play':
                    self.threadVideoPlay.playSignal.emit()
                    self.threadAudioPlay.playSignal.emit()
                    if self.threadVideoPlay.is_paused:
                        self.broadcast('{} resumed playback'.format(user_msg["user"]))
                elif client_message == '/pause':
                    self.threadVideoPlay.stopSignal.emit()
                    self.threadAudioPlay.stopSignal.emit()
                    if not self.threadVideoPlay.is_paused:
                        self.broadcast('{} stopped playback'.format(user_msg["user"]))
                elif client_message[:7] == '/skipto':
                    try:
                        frame_nb = int(client_message[8:])
                        if frame_nb > self.threadVideoPlay.totalFrames - 10 or frame_nb < 0:
                            raise Exception('invalid frame number selected')
                        video_was_paused = self.threadVideoPlay.is_paused
                        self.threadVideoPlay.stopSignal.emit()
                        self.threadAudioPlay.stopSignal.emit()
                        self.threadVideoPlay.move_progress_bar_client(frame_nb)
                        self.threadAudioPlay.move_slider_client(frame_nb)
                        if not video_was_paused:
                            self.threadVideoPlay.playSignal.emit()
                            self.threadAudioPlay.playSignal.emit()
                        self.broadcast('{} skipped to {}'.format(
                            user_msg["user"],
                            self.threadVideoPlay.frame_to_timestamp(frame_nb,
                                                                    self.threadVideoPlay.fps_metadata)
                        ))
                    except Exception as e:
                        logging.error('Error reading frame skip command\n')

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
                self.chat_box.append('{} left!'.format(nickname))
                self.nicknames.remove(nickname)
                break

    def receive(self):  # accepting multiple clients
        while True:
            try:
                client, address = self.server.accept()
                print("Connected with {}".format(str(address)))
                client.send(pickle.dumps({"msg": 'NICKNAME'}))
                nickname = pickle.loads(client.recv(1024))["msg"]
                self.nicknames.append(nickname)
                self.clients.append(client)

                # get only the IP address for each client, remove the port as it is irrelevant
                self.clients_address = [client.getpeername()[0] for client in self.clients]
                self.threadVideoPlay.update_clients(self.clients_address)
                self.threadAudioPlay.update_clients(self.clients_address)

                print("Hello {}!".format(nickname))
                self.chat_box.append("Hello {}!".format(nickname))
                self.broadcast("{} joined!".format(nickname))
                client.send(pickle.dumps({"msg": 'Connected to server!'}))
                thread = threading.Thread(target=self.handle, args=(client,))
                thread.start()
            except Exception as e:
                logging.error('err in receiving messages: {}'.format(e))

    def update_threads(self, video_thread, audio_thread):
        self.threadVideoPlay = video_thread
        self.threadAudioPlay = audio_thread
        self.threadVideoPlay.update_clients(self.clients_address)
        self.threadAudioPlay.update_clients(self.clients_address)

    def run(self):
        self.receive()
