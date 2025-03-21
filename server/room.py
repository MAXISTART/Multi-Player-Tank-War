# server/room.py
"""
房间管理模块：管理游戏房间和客户端
"""

import time
from common.constants import FRAME_DEBUG


class Room:
    """
    游戏房间：管理一组客户端和一个游戏会话

    主要功能：
    - 管理客户端加入和离开
    - 跟踪房间状态
    - 关联游戏会话
    """

    def __init__(self, room_id, name="Game Room", max_clients=4):
        """
        初始化游戏房间

        Args:
            room_id: 房间ID
            name: 房间名称
            max_clients: 最大客户端数量
        """
        self.id = room_id
        self.name = name
        self.max_clients = max_clients
        self.clients = []
        self.status = "waiting"  # waiting, starting, running, ended
        self.session = None
        self.create_time = time.time()

        # 房间配置
        self.settings = {
            "map": "random",
            "mode": "deathmatch",
            "time_limit": 300,  # 秒
            "seed": int(time.time())
        }

        # 调试标志
        self.debug = FRAME_DEBUG

    def add_client(self, client_id):
        """
        将客户端添加到房间

        Args:
            client_id: 客户端ID

        Returns:
            布尔值，表示添加是否成功
        """
        # 检查是否已经在房间中
        if client_id in self.clients:
            if self.debug:
                print(f"Client {client_id} already in room {self.id}")
            return False

        # 检查房间是否已满
        if len(self.clients) >= self.max_clients:
            if self.debug:
                print(f"Room {self.id} is full, cannot add client {client_id}")
            return False

        # 检查房间是否已经开始游戏
        if self.status not in ["waiting", "starting"]:
            if self.debug:
                print(f"Room {self.id} has already started, cannot add client {client_id}")
            return False

        # 添加客户端
        self.clients.append(client_id)

        # 通知会话有新客户端加入
        if self.session:
            self.session.client_joined(client_id)

        if self.debug:
            print(f"Client {client_id} added to room {self.id}")

        return True

    def remove_client(self, client_id):
        """
        从房间移除客户端

        Args:
            client_id: 客户端ID

        Returns:
            布尔值，表示移除是否成功
        """
        if client_id not in self.clients:
            return False

        # 移除客户端
        self.clients.remove(client_id)

        # 通知会话有客户端离开
        if self.session:
            self.session.client_left(client_id)

        if self.debug:
            print(f"Client {client_id} removed from room {self.id}")

        # 如果房间空了，重置状态
        if not self.clients:
            self.reset()

        return True

    def set_session(self, session):
        """
        设置关联的游戏会话

        Args:
            session: 游戏会话
        """
        self.session = session
        if session:
            session.set_room(self)
            if self.debug:
                print(f"Session {session.id} assigned to room {self.id}")

    def get_session(self):
        """
        获取关联的游戏会话

        Returns:
            游戏会话
        """
        return self.session

    def get_settings(self):
        """
        获取房间设置

        Returns:
            房间设置字典
        """
        return self.settings

    def update_settings(self, settings):
        """
        更新房间设置

        Args:
            settings: 新的设置字典
        """
        self.settings.update(settings)
        if self.debug:
            print(f"Room {self.id} settings updated: {settings}")

    def start_game(self):
        """
        开始游戏

        Returns:
            布尔值，表示是否成功开始游戏
        """
        if not self.clients:
            if self.debug:
                print(f"Cannot start game in empty room {self.id}")
            return False

        if not self.session:
            if self.debug:
                print(f"Cannot start game in room {self.id}, no session assigned")
            return False

        if self.status != "waiting":
            if self.debug:
                print(f"Room {self.id} already started or ended")
            return False

        # 更新状态为开始中
        self.status = "starting"

        # 启动会话
        success = self.session.start_game()

        if success:
            self.status = "running"
            if self.debug:
                print(f"Game started in room {self.id}")
        else:
            self.status = "waiting"
            if self.debug:
                print(f"Failed to start game in room {self.id}")

        return success

    def end_game(self, winner=None):
        """
        结束游戏

        Args:
            winner: 胜利者ID或团队
        """
        if self.status != "running":
            return

        self.status = "ended"

        if self.session:
            self.session.end_game(winner)

        if self.debug:
            print(f"Game ended in room {self.id}, winner: {winner}")

    def reset(self):
        """重置房间状态"""
        self.status = "waiting"

        # 更新随机种子
        self.settings["seed"] = int(time.time())

        if self.debug:
            print(f"Room {self.id} reset to waiting state")

    def get_client_count(self):
        """
        获取客户端数量

        Returns:
            客户端数量
        """
        return len(self.clients)

    def is_full(self):
        """
        检查房间是否已满

        Returns:
            布尔值，表示房间是否已满
        """
        return len(self.clients) >= self.max_clients

    def is_empty(self):
        """
        检查房间是否为空

        Returns:
            布尔值，表示房间是否为空
        """
        return len(self.clients) == 0

    def serialize(self):
        """
        序列化房间信息

        Returns:
            房间信息字典
        """
        return {
            "id": self.id,
            "name": self.name,
            "clients": self.clients,
            "client_count": len(self.clients),
            "max_clients": self.max_clients,
            "status": self.status,
            "settings": self.settings,
            "create_time": self.create_time
        }