# frame_manager.py
"""
帧管理器模块：在服务器上管理游戏帧

主要功能：
- 收集客户端输入
- 分发确定性帧
- 维护游戏状态
"""

import time
import threading
from common.constants import *
from common.frame_data import InputFrame, StateFrame, FrameBuffer
from common.protocol import create_state_update_message


class FrameManager:
    """
    帧管理器：在服务器上管理游戏帧

    主要功能：
    - 收集每个客户端的输入
    - 创建和分发确定性帧
    - 确保游戏状态一致
    """

    def __init__(self, game_engine, network_server):
        """
        初始化帧管理器

        Args:
            game_engine: 游戏引擎对象，用于执行游戏逻辑
            network_server: 网络服务器对象，用于发送消息
        """
        self.game_engine = game_engine
        self.network_server = network_server

        # 帧状态
        self.current_frame_id = 0
        self.last_executed_frame_id = -1

        # 帧缓冲区
        self.frame_buffer = FrameBuffer(max_size=300)

        # 玩家输入状态跟踪
        self.player_inputs = {}  # player_id -> {frame_id -> command}
        self.player_ready = {}  # player_id -> 最后接收的帧ID

        # 玩家列表和房间信息
        self.players = []
        self.players_lock = threading.Lock()

        # 游戏状态
        self.is_running = False
        self.tick_rate = TICK_RATE
        self.frame_interval = 1.0 / self.tick_rate
        self.last_frame_time = 0

        # 性能指标
        self.frame_processing_times = []
        self.input_collection_times = []

    def add_player(self, player_id):
        """
        添加玩家到管理器

        Args:
            player_id: 玩家ID
        """
        with self.players_lock:
            if player_id not in self.players:
                self.players.append(player_id)
                self.player_inputs[player_id] = {}
                self.player_ready[player_id] = -1

    def remove_player(self, player_id):
        """
        从管理器移除玩家

        Args:
            player_id: 玩家ID
        """
        with self.players_lock:
            if player_id in self.players:
                self.players.remove(player_id)
                if player_id in self.player_inputs:
                    del self.player_inputs[player_id]
                if player_id in self.player_ready:
                    del self.player_ready[player_id]

    def add_input(self, player_id, frame_id, input_command):
        """
        添加玩家输入

        Args:
            player_id: 玩家ID
            frame_id: 帧ID
            input_command: 输入命令
        """
        if player_id not in self.player_inputs:
            self.add_player(player_id)

        self.player_inputs[player_id][frame_id] = input_command
        self.player_ready[player_id] = max(self.player_ready[player_id], frame_id)

    def start_game(self):
        """启动游戏"""
        self.is_running = True
        self.current_frame_id = 0
        self.last_executed_frame_id = -1
        self.last_frame_time = time.time()

        # 重置游戏引擎
        self.game_engine.reset()

    def stop_game(self):
        """停止游戏"""
        self.is_running = False

    def update(self):
        """
        更新帧管理器，执行游戏逻辑

        Returns:
            bool: 是否执行了新帧
        """
        if not self.is_running:
            return False

        current_time = time.time()
        elapsed = current_time - self.last_frame_time

        # 检查是否到了执行下一帧的时间
        if elapsed < self.frame_interval:
            return False

        # 更新时间
        self.last_frame_time = current_time

        # 执行下一帧
        return self._execute_next_frame()

    def _execute_next_frame(self):
        """
        执行下一帧游戏逻辑

        Returns:
            bool: 是否成功执行
        """
        # 增加当前帧ID
        self.current_frame_id += 1

        # 收集输入
        start_time = time.time()
        input_frame = self._collect_inputs()
        self.input_collection_times.append(time.time() - start_time)

        # 保留最近100次数据
        if len(self.input_collection_times) > 100:
            self.input_collection_times.pop(0)

        # 将输入帧添加到缓冲区
        self.frame_buffer.add_input_frame(input_frame)

        # 执行游戏逻辑
        start_time = time.time()
        try:
            self.game_engine.execute_frame(
                self.current_frame_id,
                {pid: cmd for pid, cmd in input_frame.commands.items()}
            )
        except Exception as e:
            print(f"Error executing frame {self.current_frame_id}: {e}")
            return False

        self.frame_processing_times.append(time.time() - start_time)

        # 保留最近100次数据
        if len(self.frame_processing_times) > 100:
            self.frame_processing_times.pop(0)

        # 创建状态帧
        is_keyframe = self.current_frame_id % 30 == 0  # 每30帧创建一个关键帧
        state_frame = StateFrame(
            frame_id=self.current_frame_id,
            is_keyframe=is_keyframe
        )
        state_frame.set_game_state(self.game_engine.get_game_state())

        # 将状态帧添加到缓冲区
        self.frame_buffer.add_state_frame(state_frame)

        # 更新执行状态
        self.last_executed_frame_id = self.current_frame_id

        # 发送状态更新
        self._broadcast_state_update(state_frame)

        return True

    def _collect_inputs(self):
        """
        收集所有玩家的输入

        Returns:
            InputFrame: 包含所有玩家输入的帧
        """
        input_frame = InputFrame(frame_id=self.current_frame_id)

        with self.players_lock:
            for player_id in self.players:
                # 获取玩家在当前帧的输入
                if player_id in self.player_inputs and self.current_frame_id in self.player_inputs[player_id]:
                    command = self.player_inputs[player_id][self.current_frame_id]
                    input_frame.add_command(player_id, command)
                else:
                    # 如果没有输入，使用空输入
                    from common.frame_data import InputCommand
                    input_frame.add_command(player_id, InputCommand(
                        player_id=player_id,
                        movement='stop',
                        shooting=False
                    ))

        return input_frame

    def _broadcast_state_update(self, state_frame):
        """
        广播状态更新到所有客户端

        Args:
            state_frame: 状态帧
        """
        # 创建状态更新消息
        message = create_state_update_message(
            frame_id=state_frame.frame_id,
            state_frame=state_frame
        )

        # 广播消息到所有客户端
        self.network_server.broadcast_message(message)

    def get_performance_stats(self):
        """
        获取性能统计信息

        Returns:
            dict: 性能统计信息
        """
        frame_time_avg = sum(self.frame_processing_times) / max(1, len(self.frame_processing_times))
        input_time_avg = sum(self.input_collection_times) / max(1, len(self.input_collection_times))

        return {
            'frame_time_avg': frame_time_avg * 1000,  # 转换为毫秒
            'input_time_avg': input_time_avg * 1000,  # 转换为毫秒
            'current_frame': self.current_frame_id,
            'player_count': len(self.players),
            'tick_rate': self.tick_rate
        }

    def cleanup_old_inputs(self, max_age=300):
        """
        清理旧的输入数据

        Args:
            max_age: 保留的最大帧数差
        """
        if self.current_frame_id <= max_age:
            return

        # 清理旧的输入数据
        cutoff_frame = self.current_frame_id - max_age

        for player_id in self.player_inputs:
            frames_to_remove = [
                fid for fid in self.player_inputs[player_id]
                if fid < cutoff_frame
            ]

            for fid in frames_to_remove:
                del self.player_inputs[player_id][fid]