import pickle

from PyQt5.QtCore import QThread
import logging
import threading

logging.basicConfig(format="%(message)s", level=logging.INFO)


class TcpChat(QThread):
    def __init__(self, chat_socket, host_ip, chat_box, message_box):
        super().__init__()
        # self.nickname = 'test_user'
        self.nickname = ""
        self.host_ip = host_ip
        self.chat_socket = chat_socket

        self.chat_box = chat_box
        self.message_box = message_box
        self.message_box.returnPressed.connect(self.set_username)

        self.started = False

    def receive(self):
        while True:  # making valid connection
            try:
                packed_msg = self.chat_socket.recv(1024)
                user_msg = pickle.loads(packed_msg)
                if user_msg["msg"] == 'NICKNAME':
                    self.chat_socket.send(pickle.dumps({"msg": self.nickname}))
                elif user_msg["msg"] != "":
                    print(user_msg["msg"])
                    self.chat_box.append(user_msg["msg"])
                    pass
            except Exception as e:  # case on wrong ip/port details
                logging.info('Ended connection with server')
                # logging.error(e)
                self.chat_socket.close()
                break

    def set_username(self):
        try:
            self.nickname = self.message_box.text()
            self.message_box.setText("")

            self.message_box.returnPressed.disconnect(self.set_username)
            self.message_box.returnPressed.connect(self.write)

            print(self.host_ip)
            self.chat_socket.connect((self.host_ip, 7976))  # connecting client to server

            receive_thread = threading.Thread(target=self.receive)  # receiving multiple messages
            receive_thread.start()

            self.started = True
        except Exception as e:
            logging.error(e)

    def write(self):
        try:
            user = self.nickname
            message = self.message_box.text()
            if len(message) < 1024:
                user_msg = pickle.dumps({"user": user, "msg": message})
                if self.started:
                    self.chat_socket.send(user_msg)
            else:
                self.chat_box.append("Message was too long. Character limit is 1024")
            self.message_box.setText("")
        except Exception as e:
            logging.error('write message err: {}'.format(e))

    def run(self):
        self.chat_box.append("Choose your nickname:")

        # waiting until nickname is set before connecting socket
        while not self.started and self.nickname == "":
            pass
