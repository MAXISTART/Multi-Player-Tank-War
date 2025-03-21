# server/network/server.py
"""
网络服务器模块：处理网络通信
"""

import socket
import threading
import json
import time
import struct
from queue import Queue

from common.constants import SERVER_IP, SERVER_PORT, NET_DEBUG


class NetworkServer:
    """
    网络服务器：处理客户端连接和通信

    主要功能：
    - 接受客户端连接
    - 发送和接收消息
    - 管理客户端列表
    """

    def __init__(self, host=SERVER_IP, port=SERVER_PORT):
        """初始化网络服务器"""
        self.host = host
        self.port = port
        self.socket = None
        self.running = False

        # 客户端连接
        self.clients = {}  # client_id -> client_socket
        self.client_addresses = {}  # client_id -> address

        # 线程和队列
        self.accept_thread = None
        self.message_queue = Queue()

        # 消息处理回调
        self.message_handlers = {}

        # 调试标志
        self.debug = NET_DEBUG

    def start(self):
        """启动服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(10)

            self.running = True

            # 启动接受客户端线程
            self.accept_thread = threading.Thread(target=self._accept_clients)
            self.accept_thread.daemon = True
            self.accept_thread.start()

            if self.debug:
                print(f"Server started on {self.host}:{self.port}")

            return True

        except Exception as e:
            if self.debug:
                print(f"Error starting server: {e}")
            return False

    def stop(self):
        """停止服务器"""
        self.running = False

        # 关闭所有客户端连接
        for client_id, client_socket in list(self.clients.items()):
            try:
                client_socket.close()
            except:
                pass

        # 关闭服务器套接字
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

        if self.debug:
            print("Server stopped")

    def register_handler(self, message_type, handler_function):
        """
        注册消息处理函数

        Args:
            message_type: 消息类型
            handler_function: 处理函数，接收(client_id, message)作为参数
        """
        self.message_handlers[message_type] = handler_function

    def send_message(self, client_id, message):
        """
        发送消息给指定客户端

        Args:
            client_id: 客户端ID
            message: 要发送的消息（字典）

        Returns:
            布尔值，表示是否发送成功
        """
        if client_id not in self.clients:
            return False

        try:
            # 序列化消息
            msg_json = json.dumps(message)
            msg_bytes = msg_json.encode('utf-8')

            # 添加长度前缀
            msg_len = len(msg_bytes)
            prefix = struct.pack('!I', msg_len)

            # 发送消息
            self.clients[client_id].sendall(prefix + msg_bytes)

            if self.debug and message.get('type') != 'input_frame' and message.get('type') != 'game_state':
                print(f"Sent to {client_id}: {message}")

            return True
        except Exception as e:
            if self.debug:
                print(f"Error sending message to {client_id}: {e}")

            # 客户端可能已断开连接，移除
            self._remove_client(client_id)

            return False

    def broadcast_message(self, message, exclude_client_id=None):
        """
        广播消息给所有客户端

        Args:
            message: 要广播的消息（字典）
            exclude_client_id: 要排除的客户端ID
        """
        for client_id in list(self.clients.keys()):
            if exclude_client_id and client_id == exclude_client_id:
                continue
            self.send_message(client_id, message)

    def process_messages(self):
        """
        处理消息队列中的所有消息

        Returns:
            处理的消息数量
        """
        processed = 0
        while not self.message_queue.empty():
            try:
                client_id, message = self.message_queue.get_nowait()
                message_type = message.get('type')

                # 调用对应的处理函数
                if message_type in self.message_handlers:
                    self.message_handlers[message_type](client_id, message)

                self.message_queue.task_done()
                processed += 1

            except Exception as e:
                if self.debug:
                    print(f"Error processing message: {e}")
                break

        return processed

    def get_client_count(self):
        """
        获取当前连接的客户端数量

        Returns:
            客户端数量
        """
        return len(self.clients)

    def get_client_list(self):
        """
        获取客户端列表

        Returns:
            客户端ID列表
        """
        return list(self.clients.keys())

    def _accept_clients(self):
        """接受客户端连接的线程函数"""
        while self.running:
            try:
                client_socket, address = self.socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.running:  # 只在仍然运行时打印错误
                    if self.debug:
                        print(f"Error accepting client: {e}")
                break

    def _handle_client(self, client_socket, address):
        """
        处理单个客户端的连接

        Args:
            client_socket: 客户端套接字
            address: 客户端地址
        """
        client_id = None
        buffer = b''

        if self.debug:
            print(f"New client connected: {address}")

        try:
            while self.running:
                # 读取消息头（4字节，表示消息长度）
                while len(buffer) < 4:
                    data = client_socket.recv(4096)
                    if not data:
                        raise Exception("Connection closed by client")
                    buffer += data

                # 获取消息长度并读取完整消息
                msg_len = struct.unpack('!I', buffer[:4])[0]
                buffer = buffer[4:]

                while len(buffer) < msg_len:
                    data = client_socket.recv(4096)
                    if not data:
                        raise Exception("Connection closed by client")
                    buffer += data

                # 提取完整消息并处理
                msg_data = buffer[:msg_len]
                buffer = buffer[msg_len:]

                # 解析JSON消息
                try:
                    message = json.loads(msg_data.decode('utf-8'))

                    # 获取客户端ID（如果是连接消息或已知客户端）
                    if message.get('type') == 'connect':
                        client_id = message.get('client_id')
                        self.clients[client_id] = client_socket
                        self.client_addresses[client_id] = address

                        if self.debug:
                            print(f"Client identified: {client_id} from {address}")
                    elif 'client_id' in message:
                        client_id = message.get('client_id')

                    # 将消息添加到队列
                    if client_id:
                        self.message_queue.put((client_id, message))

                    if self.debug and message.get('type') != 'input_frame' and message.get('type') != 'game_state':
                        print(f"Received from {client_id}: {message}")

                except json.JSONDecodeError:
                    if self.debug:
                        print(f"Error decoding message from {address}")

        except Exception as e:
            if self.running:  # 只在仍然运行时打印错误
                if self.debug:
                    print(f"Error handling client {client_id}: {e}")
        finally:
            # 关闭连接并清理
            try:
                client_socket.close()
            except:
                pass

            if client_id:
                self._remove_client(client_id)

    def _remove_client(self, client_id):
        """
        移除客户端

        Args:
            client_id: 要移除的客户端ID
        """
        if client_id in self.clients:
            del self.clients[client_id]

        if client_id in self.client_addresses:
            address = self.client_addresses[client_id]
            del self.client_addresses[client_id]

            if self.debug:
                print(f"Client disconnected: {client_id} from {address}")