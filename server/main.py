# server/main.py
"""
服务器主模块：服务器入口点
"""

import time
import sys
import argparse
import threading
from server.network.server import NetworkServer
from server.frame_sync.frame_manager import FrameManager
from server.room import Room
from server.session import GameSession
from common.constants import SERVER_IP, SERVER_PORT


class GameServer:
    """
    游戏服务器：管理整个服务器流程

    主要功能：
    - 初始化服务器组件
    - 管理房间和会话
    - 处理命令行命令
    """

    def __init__(self, host=SERVER_IP, port=SERVER_PORT):
        """初始化游戏服务器"""
        self.host = host
        self.port = port
        self.running = False

        # 网络组件
        self.network_server = NetworkServer(host, port)

        # 房间和会话
        self.rooms = {}
        self.default_room = None

        # 帧同步
        self.frame_manager = None

        # 调试标志
        self.debug = True

    def start(self):
        """启动服务器"""
        print(f"Starting server on {self.host}:{self.port}")

        # 启动网络服务器
        if not self.network_server.start():
            print("Failed to start network server")
            return False

        # 创建默认房间
        self.default_room = Room("default", "Default Room")
        self.rooms["default"] = self.default_room

        # 注册网络消息处理函数
        self.network_server.register_handler('connect', self._handle_connect)
        self.network_server.register_handler('disconnect', self._handle_disconnect)

        # 创建默认游戏会话
        default_session = GameSession("default_session", self.network_server)
        self.default_room.set_session(default_session)

        # 创建帧管理器
        self.frame_manager = FrameManager(self.network_server, default_session)
        self.frame_manager.start()

        self.running = True
        print("Server started successfully")

        # 启动命令行处理线程
        command_thread = threading.Thread(target=self._command_loop)
        command_thread.daemon = True
        command_thread.start()

        # 启动主循环
        self._main_loop()

        return True

    def stop(self):
        """停止服务器"""
        print("Stopping server...")

        self.running = False

        # 停止帧管理器
        if self.frame_manager:
            self.frame_manager.stop()

        # 停止网络服务器
        if self.network_server:
            self.network_server.stop()

        print("Server stopped")

    def _main_loop(self):
        """服务器主循环"""
        try:
            while self.running:
                # 更新帧管理器
                if self.frame_manager:
                    self.frame_manager.update()

                # 控制循环速度
                time.sleep(1 / 60)  # 约60FPS

        except KeyboardInterrupt:
            print("\nServer shutdown requested...")
        finally:
            self.stop()

    def _command_loop(self):
        """命令行处理循环"""
        print("Type commands and press Enter. Type 'help' for available commands.")
        while self.running:
            try:
                # 此处使用普通的阻塞式输入
                command = input("> ").strip()
                self._handle_command(command)
            except EOFError:
                break
            except Exception as e:
                print(f"Error processing command: {e}")

    def _handle_command(self, command):
        """
        处理命令行命令

        Args:
            command: 命令字符串
        """
        if not command:
            return

        parts = command.split()
        cmd = parts[0].lower()

        if cmd == "quit" or cmd == "exit":
            print("Shutting down server...")
            self.running = False

        elif cmd == "clients":
            clients = self.network_server.get_client_list()
            print(f"Connected clients ({len(clients)}):")
            for i, client_id in enumerate(clients):
                print(f"  {i + 1}. {client_id}")

        elif cmd == "rooms":
            print(f"Rooms ({len(self.rooms)}):")
            for room_id, room in self.rooms.items():
                print(f"  {room_id}: {room.name} - {len(room.clients)} clients")

        elif cmd == "start":
            # 启动默认房间的游戏
            if self.default_room:
                session = self.default_room.get_session()
                if session:
                    if self.default_room.start_game():
                        print("Game started in default room")
                    else:
                        print("Failed to start game in default room")
            else:
                print("Default room not found")

        elif cmd == "help":
            print("Available commands:")
            print("  clients - Show connected clients")
            print("  rooms   - Show active rooms")
            print("  start   - Start game in default room")
            print("  quit    - Shutdown the server")
            print("  help    - Show this help message")

        else:
            print(f"Unknown command: {cmd}")
            print("Type 'help' for available commands")

    def _handle_connect(self, client_id, message):
        """
        处理客户端连接

        Args:
            client_id: 客户端ID
            message: 连接消息
        """
        print(f"Client connected: {client_id}")

        # 将客户端添加到默认房间
        if self.default_room:
            self.default_room.add_client(client_id)

            # 发送欢迎消息
            self.network_server.send_message(client_id, {
                'type': 'welcome',
                'message': f"Welcome to the server, {client_id}!",
                'room_id': self.default_room.id,
                'room_name': self.default_room.name
            })

    def _handle_disconnect(self, client_id, message):
        """
        处理客户端断开连接

        Args:
            client_id: 客户端ID
            message: 断开连接消息
        """
        print(f"Client disconnected: {client_id}")

        # 从所有房间移除客户端
        for room in self.rooms.values():
            room.remove_client(client_id)


# 启动服务器
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Tank Battle Game Server')
    parser.add_argument('-H', '--host', default=SERVER_IP, help='Server host address')
    parser.add_argument('-p', '--port', type=int, default=SERVER_PORT, help='Server port')

    args = parser.parse_args()

    server = GameServer(args.host, args.port)
    server.start()