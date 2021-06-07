from PyQt5.QtCore import pyqtSlot, QTimer, QObject, pyqtSignal, QThread
import logging
import threading

logging.basicConfig(format="%(message)s", level=logging.INFO)


class TcpChat(QThread):
    def __init__(self, chat_socket):
        super().__init__()
        self.nickname = 'test_user'  # input("Choose your nickname: ")

        self.client = chat_socket
        self.client.connect(('192.168.0.106', 7976))  # connecting client to server

    def receive(self):
        while True:  # making valid connection
            try:
                message = self.client.recv(1024).decode('ascii')
                if message == 'NICKNAME':
                    self.client.send(self.nickname.encode('ascii'))
                else:
                    print(message)  # received in bytes
            except Exception as e:  # case on wrong ip/port details
                print("An error occured on the server side!")
                logging.error(e)
                self.client.close()
                break

    def write(self):
        while True:  # message layout
            message = '{}: {}'.format(self.nickname, input(''))
            self.client.send(message.encode('ascii'))

    def run(self):
        receive_thread = threading.Thread(target=self.receive)  # receiving multiple messages
        receive_thread.start()
        write_thread = threading.Thread(target=self.write)  # sending messages
        write_thread.start()
