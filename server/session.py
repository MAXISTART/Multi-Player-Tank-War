# server/session.py
"""
会话管理模块：管理游戏会话和状态
"""

import time
import random
import hashlib
import json
from common.constants import FRAME_DEBUG


class GameSession:
    """
    游戏会话：管理游戏状态和逻辑

    主要功能：
    - 维护游戏状态
    - 处理游戏逻辑
    - 提供状态同步支持
    """

    def __init__(self, session_id, network_server=None):
        """
        初始化游戏会话

        Args:
            session_id: 会话ID
            network_server: 网络服务器实例
        """
        self.id = session_id
        self.network_server = network_server
        self.room = None
        self.players = {}  # player_id -> player_data
        self.game_state = {
            "tanks": [],
            "bullets": [],
            "game_over": False,
            "winner": None,
            "timestamp": time.time()
        }
        self.status = "waiting"  # waiting, running, ended
        self.start_time = 0
        self.end_time = 0

        # 调试标志
        self.debug = FRAME_DEBUG

    def set_room(self, room):
        """
        设置关联的房间

        Args:
            room: 房间实例
        """
        self.room = room

    def client_joined(self, client_id):
        """
        处理客户端加入

        Args:
            client_id: 客户端ID
        """
        # 如果游戏已经开始，不允许加入
        if self.status == "running":
            if self.debug:
                print(f"Session {self.id}: Cannot add player {client_id}, game already running")
            return

        # 如果不是新客户端，忽略
        if client_id in self.players:
            return

        # 添加新玩家
        player_index = len(self.players)
        colors = ['blue', 'red', 'green', 'yellow']

        self.players[client_id] = {
            "id": client_id,
            "index": player_index,
            "color": colors[player_index % len(colors)],
            "ready": False,
            "score": 0,
            "kills": 0,
            "deaths": 0
        }

        if self.debug:
            print(f"Session {self.id}: Added player {client_id} with index {player_index}")

    def client_left(self, client_id):
        """
        处理客户端离开

        Args:
            client_id: 客户端ID
        """
        # 如果不是已知客户端，忽略
        if client_id not in self.players:
            return

        # 移除玩家
        del self.players[client_id]

        if self.debug:
            print(f"Session {self.id}: Removed player {client_id}")

        # 如果游戏正在运行，检查是否应该结束游戏
        if self.status == "running" and not self.players:
            self.end_game()

    def start_game(self):
        """
        开始游戏

        Returns:
            布尔值，表示是否成功开始游戏
        """
        if not self.players:
            if self.debug:
                print(f"Session {self.id}: Cannot start game with no players")
            return False

        if not self.room:
            if self.debug:
                print(f"Session {self.id}: Cannot start game, no room assigned")
            return False

        if self.status == "running":
            if self.debug:
                print(f"Session {self.id}: Game already running")
            return False

        # 获取房间设置
        settings = self.room.get_settings()
        seed = settings.get("seed", int(time.time()))
        map_name = settings.get("map", "random")

        # 更新状态
        self.status = "running"
        self.start_time = time.time()

        # 创建玩家列表
        players_list = []
        for client_id, player_data in self.players.items():
            players_list.append(player_data)

        # 给所有客户端发送游戏开始消息
        if self.network_server:
            for client_id in self.players:
                self.network_server.send_message(client_id, {
                    'type': 'game_start',
                    'game_id': self.id,
                    'seed': seed,
                    'map_name': map_name,
                    'player_id': client_id,
                    'player_index': self.players[client_id]['index'],
                    'players': players_list
                })

        if self.debug:
            print(f"Session {self.id}: Game started with seed {seed}")

        return True

    def end_game(self, winner=None):
        """
        结束游戏

        Args:
            winner: 胜利者ID或团队
        """
        if self.status != "running":
            return

        self.status = "ended"
        self.end_time = time.time()

        # 更新游戏状态
        self.game_state["game_over"] = True
        self.game_state["winner"] = winner

        # 发送游戏结束消息
        if self.network_server:
            for client_id in self.players:
                self.network_server.send_message(client_id, {
                    'type': 'game_end',
                    'game_id': self.id,
                    'winner': winner,
                    'duration': self.end_time - self.start_time,
                    'players': list(self.players.values())
                })

        if self.debug:
            print(f"Session {self.id}: Game ended, winner: {winner}")

    def update(self, frame_number, frame_inputs):
        """
        更新游戏状态

        Args:
            frame_number: 帧号
            frame_inputs: 帧输入数据
        """
        if self.status != "running":
            return

        # 游戏逻辑更新将在这里实现
        # 这里只是一个简单的示例，实际游戏逻辑会更复杂

        # 更新时间戳
        self.game_state["timestamp"] = time.time()

        # 更新帧号
        self.game_state["frame"] = frame_number

    def get_state(self):
        """
        获取当前游戏状态

        Returns:
            游戏状态字典
        """
        return self.game_state

    def calculate_checksum(self):
        """
        计算游戏状态的校验和

        Returns:
            校验和字符串
        """
        # 创建状态副本并移除不稳定元素
        state_copy = dict(self.game_state)
        state_copy.pop("timestamp", None)

        # 序列化状态并计算哈希
        state_str = json.dumps(state_copy, sort_keys=True)
        checksum = hashlib.md5(state_str.encode()).hexdigest()

        return checksum

    def reset(self):
        """重置会话状态"""
        self.status = "waiting"
        self.start_time = 0
        self.end_time = 0
        self.game_state = {
            "tanks": [],
            "bullets": [],
            "game_over": False,
            "winner": None,
            "timestamp": time.time()
        }

        # 重置玩家状态
        for player_id in self.players:
            self.players[player_id]["ready"] = False
            self.players[player_id]["score"] = 0
            self.players[player_id]["kills"] = 0
            self.players[player_id]["deaths"] = 0

        if self.debug:
            print(f"Session {self.id}: Reset to waiting state")

    def set_player_ready(self, client_id, ready=True):
        """
        设置玩家准备状态

        Args:
            client_id: 客户端ID
            ready: 准备状态
        """
        if client_id not in self.players:
            return

        self.players[client_id]["ready"] = ready

        if self.debug:
            print(f"Session {self.id}: Player {client_id} ready: {ready}")

        # 检查是否所有玩家都准备好了
        all_ready = all(player["ready"] for player in self.players.values())

        if all_ready and self.status == "waiting" and self.room:
            # 自动开始游戏
            self.room.start_game()

    def get_player_data(self, client_id):
        """
        获取玩家数据

        Args:
            client_id: 客户端ID

        Returns:
            玩家数据字典
        """
        return self.players.get(client_id)

    def get_all_players(self):
        """
        获取所有玩家数据

        Returns:
            玩家数据字典列表
        """
        return list(self.players.values())

    def serialize(self):
        """
        序列化会话信息

        Returns:
            会话信息字典
        """
        return {
            "id": self.id,
            "status": self.status,
            "player_count": len(self.players),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.end_time - self.start_time if self.end_time else 0,
            "game_over": self.game_state.get("game_over", False),
            "winner": self.game_state.get("winner")
        }