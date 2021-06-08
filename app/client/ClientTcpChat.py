import pickle

from PyQt5.QtCore import QThread
import logging
import threading


logging.basicConfig(format="%(message)s", level=logging.INFO)


class TcpChat(QThread):
    def __init__(self, chat_socket, host_ip):
        super().__init__()
        # self.nickname = 'test_user'
        self.nickname = input("Choose your nickname: ")

        self.client = chat_socket
        self.client.connect((host_ip, 7976))  # connecting client to server

    def receive(self):
        while True:  # making valid connection
            try:
                user_msg = pickle.loads(self.client.recv(1024))
                if user_msg["msg"] == 'NICKNAME':
                    self.client.send(pickle.dumps({"msg": self.nickname}))
                else:
                    print(user_msg["msg"])  # received in bytes
                    pass
            except Exception as e:  # case on wrong ip/port details
                print("An error occured on the server side!")
                logging.error(e)
                self.client.close()
                break

    def write(self):
        while True:  # message layout
            try:
                user = self.nickname
                message = input('')
                user_msg = pickle.dumps({"user": user, "msg": message})
                self.client.send(user_msg)
            except Exception as e:
                logging.error(e)

    def run(self):
        receive_thread = threading.Thread(target=self.receive)  # receiving multiple messages
        receive_thread.start()
        write_thread = threading.Thread(target=self.write)  # sending messages
        write_thread.start()
