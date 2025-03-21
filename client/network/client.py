# client/network/client.py
"""
客户端网络模块：处理网络通信
"""

import socket
import json
import time
import queue
import threading


class NetworkClient:
    """
    网络客户端：处理与服务器的通信

    主要功能：
    - 连接到服务器
    - 发送和接收消息
    - 维持连接状态
    """

    def __init__(self, host, port, debug=False):
        """
        初始化网络客户端

        Args:
            host: 服务器主机名或IP
            port: 服务器端口
            debug: 是否启用调试输出
        """
        self.host = host
        self.port = port
        self.debug = debug

        self.socket = None
        self.connected = False

        # 消息队列
        self.send_queue = queue.Queue()
        self.receive_queue = queue.Queue()

        # 线程
        self.send_thread = None
        self.receive_thread = None

        # 回调函数
        self.message_callback = None
        self.game_start_callback = None
        self.game_end_callback = None

    def connect(self):
        """
        连接到服务器

        Returns:
            布尔值，表示连接是否成功
        """
        try:
            # 创建套接字
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 设置超时时间

            # 连接到服务器
            self.socket.connect((self.host, self.port))
            self.connected = True

            print(f"Connected to server at {self.host}:{self.port}")

            # 启动发送和接收线程
            self.send_thread = threading.Thread(target=self._send_loop)
            self.send_thread.daemon = True
            self.send_thread.start()

            self.receive_thread = threading.Thread(target=self._receive_loop)
            self.receive_thread.daemon = True
            self.receive_thread.start()

            # 发送连接消息
            client_id = f"client_{int(time.time())}"
            self.send_message({
                'type': 'connect',
                'client_id': client_id
            })

            return True

        except Exception as e:
            print(f"Error connecting to server: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开与服务器的连接"""
        if not self.connected:
            return

        print("Disconnecting from server...")
        self.connected = False

        try:
            # 发送断开连接消息
            self.send_message({'type': 'disconnect'})
            time.sleep(0.1)  # 给一点时间让消息发送出去
        except:
            pass  # 忽略发送错误

        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except:
            pass  # 忽略关闭错误

        try:
            self.socket.close()
        except:
            pass  # 忽略关闭错误

        print("Disconnected from server")

    def send_message(self, message):
        """
        发送消息到服务器

        Args:
            message: 要发送的消息(dict)
        """
        if not self.connected:
            return

        self.send_queue.put(message)

    def receive_message(self, block=True, timeout=None):
        """
        从接收队列获取消息

        Args:
            block: 如果队列为空，是否阻塞
            timeout: 阻塞的超时时间

        Returns:
            消息字典或None
        """
        try:
            return self.receive_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def is_connected(self):
        """
        检查是否连接到服务器

        Returns:
            布尔值，表示是否已连接
        """
        return self.connected

    def _send_loop(self):
        """发送消息的循环"""
        try:
            while self.connected:
                try:
                    # 从发送队列获取消息
                    if not self.send_queue.empty():
                        message = self.send_queue.get()

                        # 序列化和发送消息
                        message_data = json.dumps(message).encode('utf-8')
                        message_length = len(message_data).to_bytes(4, byteorder='big')

                        try:
                            self.socket.sendall(message_length + message_data)

                            if self.debug:
                                print(f"Sent: {message}")
                        except (socket.error, BrokenPipeError) as e:
                            print(f"Error sending message: {e}")
                            self.connected = False
                            break

                    # 避免CPU过载
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Error in send loop: {e}")
                    # 继续循环而不是退出，这样小的错误不会导致整个连接断开
                    time.sleep(0.1)  # 错误后稍微等待一下
        except Exception as e:
            print(f"Fatal error in send loop: {e}")
        finally:
            print("Send loop terminated")

    def _receive_loop(self):
        """接收消息的循环"""
        try:
            while self.connected:
                try:
                    # 接收消息长度（4字节）
                    length_data = self._receive_exactly(4)
                    if not length_data:
                        # 连接关闭
                        self.connected = False
                        break

                    message_length = int.from_bytes(length_data, byteorder='big')

                    # 接收消息内容
                    message_data = self._receive_exactly(message_length)
                    if not message_data:
                        # 连接关闭
                        self.connected = False
                        break

                    # 解析消息
                    message = json.loads(message_data.decode('utf-8'))

                    # 放入接收队列
                    self.receive_queue.put(message)

                    if self.debug:
                        print(f"Received: {message}")

                    # 处理特定类型的消息
                    self._process_message(message)

                except json.JSONDecodeError as e:
                    print(f"Error decoding message: {e}")
                except Exception as e:
                    print(f"Error in receive loop: {e}")
                    time.sleep(0.1)  # 错误后稍微等待一下
        except Exception as e:
            print(f"Fatal error in receive loop: {e}")
        finally:
            print("Receive loop terminated")
            self.connected = False

    def _receive_exactly(self, n):
        """确保接收恰好n个字节"""
        data = bytearray()
        remaining = n
        while remaining > 0:
            try:
                chunk = self.socket.recv(remaining)
                if not chunk:  # 连接关闭
                    return None
                data.extend(chunk)
                remaining -= len(chunk)
            except socket.timeout:
                # 超时后继续尝试接收
                continue
            except Exception as e:
                print(f"Error receiving data: {e}")
                return None
        return bytes(data)

    def _process_message(self, message):
        """
        处理特定类型的消息

        Args:
            message: 收到的消息
        """
        if not isinstance(message, dict):
            return

        message_type = message.get('type')

        # 处理欢迎消息
        if message_type == 'welcome':
            room_id = message.get('room_id')
            room_name = message.get('room_name')
            welcome_msg = message.get('message')
            print(f"Received welcome: {welcome_msg}")
            print(f"Joined room: {room_name} (ID: {room_id})")

        # 处理游戏开始消息
        elif message_type == 'game_start':
            game_id = message.get('game_id')
            player_id = message.get('player_id')
            player_index = message.get('player_index')
            print(f"Game started! Game ID: {game_id}")
            print(f"You are player {player_index} (ID: {player_id})")

            # 通知游戏开始
            if self.game_start_callback:
                self.game_start_callback(message)

        # 处理游戏结束消息
        elif message_type == 'game_end':
            winner = message.get('winner')
            duration = message.get('duration')
            print(f"Game ended! Winner: {winner}")
            print(f"Game duration: {duration:.2f} seconds")

            # 通知游戏结束
            if self.game_end_callback:
                self.game_end_callback(message)

        # 其他消息由回调函数处理
        elif self.message_callback:
            self.message_callback(message)

    def set_message_callback(self, callback):
        """
        设置消息回调函数

        Args:
            callback: 回调函数，接收一个参数(消息)
        """
        self.message_callback = callback

    def set_game_start_callback(self, callback):
        """
        设置游戏开始回调函数

        Args:
            callback: 回调函数，接收一个参数(游戏开始消息)
        """
        self.game_start_callback = callback

    def set_game_end_callback(self, callback):
        """
        设置游戏结束回调函数

        Args:
            callback: 回调函数，接收一个参数(游戏结束消息)
        """
        self.game_end_callback = callback