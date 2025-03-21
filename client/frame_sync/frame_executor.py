# frame_executor.py
"""
帧执行器模块：执行游戏帧逻辑

主要功能：
- 执行输入帧
- 管理帧回滚和重放
- 处理确定性运行
"""

import time
import pygame
from common.constants import *
from common.frame_data import InputFrame, StateFrame, FrameBuffer
from client.frame_sync.input_manager import InputBuffer


class FrameExecutor:
    """
    帧执行器：执行游戏帧逻辑，处理帧同步

    主要功能：
    - 从输入帧执行游戏逻辑
    - 管理帧缓冲区
    - 实现回滚和重放
    """

    def __init__(self, game_engine, local_player_id):
        """
        初始化帧执行器

        Args:
            game_engine: 游戏引擎对象，用于执行游戏逻辑
            local_player_id: 本地玩家ID
        """
        self.game_engine = game_engine  # 游戏引擎引用
        self.local_player_id = local_player_id

        # 帧状态
        self.current_frame_id = 0
        self.last_executed_frame_id = -1
        self.last_confirmed_frame_id = -1

        # 帧缓冲区
        self.frame_buffer = FrameBuffer(max_size=300)
        self.input_buffer = InputBuffer()

        # 调试信息
        self.rollback_count = 0
        self.dropped_frames = 0
        self.debug_mode = False

    def add_input_frame(self, frame):
        """
        添加输入帧到缓冲区

        Args:
            frame: InputFrame对象或字典
        """
        self.frame_buffer.add_input_frame(frame)

        # 更新输入缓冲区
        if isinstance(frame, dict):
            frame_id = frame.get('frame_id')
            commands = frame.get('commands', {})
        else:
            frame_id = frame.frame_id
            commands = frame.commands

        for player_id, command in commands.items():
            self.input_buffer.add_input(frame_id, player_id, command)

    def add_state_frame(self, frame):
        """
        添加状态帧到缓冲区

        Args:
            frame: StateFrame对象或字典
        """
        self.frame_buffer.add_state_frame(frame)

    def set_confirmed_frame(self, frame_id):
        """
        设置已确认的帧ID

        Args:
            frame_id: 确认的帧ID
        """
        if frame_id > self.last_confirmed_frame_id:
            self.last_confirmed_frame_id = frame_id
            self.frame_buffer.set_confirmed_frame(frame_id)

            # 清理确认帧之前的输入
            self.input_buffer.clear_before(frame_id - 100)  # 保留一些历史以便于调试

    def execute_frame(self, target_frame_id=None):
        """
        执行到指定帧

        Args:
            target_frame_id: 目标帧ID，如果为None则执行下一帧

        Returns:
            bool: 是否成功执行
        """
        if target_frame_id is None:
            target_frame_id = self.current_frame_id

        # 检查是否需要回滚
        if self.last_executed_frame_id > target_frame_id:
            return self._rollback_and_execute(target_frame_id)

        # 从上次执行的帧开始执行
        start_frame_id = self.last_executed_frame_id + 1

        for frame_id in range(start_frame_id, target_frame_id + 1):
            # 获取当前帧的所有输入
            inputs = self.input_buffer.get_frame_inputs(frame_id)

            # 执行游戏逻辑
            if not self._execute_single_frame(frame_id, inputs):
                return False

        # 更新执行状态
        self.last_executed_frame_id = target_frame_id
        self.current_frame_id = target_frame_id + 1
        return True

    def _execute_single_frame(self, frame_id, inputs):
        """
        执行单个帧的游戏逻辑

        Args:
            frame_id: 帧ID
            inputs: 玩家输入字典

        Returns:
            bool: 是否成功执行
        """
        # 这里调用游戏引擎的帧执行函数
        # 通常包括：应用输入、更新游戏状态、处理碰撞等
        try:
            self.game_engine.execute_frame(frame_id, inputs)
            return True
        except Exception as e:
            print(f"Error executing frame {frame_id}: {e}")
            return False

    def _rollback_and_execute(self, target_frame_id):
        """
        回滚到指定帧并重新执行

        Args:
            target_frame_id: 目标帧ID

        Returns:
            bool: 是否成功执行
        """
        self.rollback_count += 1
        if self.debug_mode:
            print(f"Rolling back from frame {self.last_executed_frame_id} to {target_frame_id}")

        # 查找最近的关键帧（完整状态）
        keyframe = self.frame_buffer.get_last_keyframe()
        if not keyframe or keyframe.frame_id >= target_frame_id:
            # 如果找不到合适的关键帧，尝试从头开始
            keyframe_id = -1
        else:
            keyframe_id = keyframe.frame_id
            # 加载关键帧状态
            self.game_engine.load_state(keyframe.game_state)

        # 从关键帧之后逐帧执行
        start_frame_id = keyframe_id + 1

        for frame_id in range(start_frame_id, target_frame_id + 1):
            inputs = self.input_buffer.get_frame_inputs(frame_id)
            if not self._execute_single_frame(frame_id, inputs):
                return False

        # 更新状态
        self.last_executed_frame_id = target_frame_id
        self.current_frame_id = target_frame_id + 1
        return True

    def get_current_state(self):
        """
        获取当前游戏状态

        Returns:
            dict: 游戏状态
        """
        return self.game_engine.get_game_state()

    def create_state_frame(self, is_keyframe=False):
        """
        创建当前状态的状态帧

        Args:
            is_keyframe: 是否为关键帧

        Returns:
            StateFrame: 创建的状态帧
        """
        frame = StateFrame(
            frame_id=self.current_frame_id - 1,
            is_keyframe=is_keyframe
        )
        frame.set_game_state(self.get_current_state())
        return frame


class FrameRate:
    """
    帧率控制器：控制游戏的逻辑帧率

    主要功能：
    - 控制游戏帧率
    - 计算帧时间和帧延迟
    """

    def __init__(self, tick_rate=TICK_RATE):
        """
        初始化帧率控制器

        Args:
            tick_rate: 每秒的逻辑帧数
        """
        self.tick_rate = tick_rate
        self.frame_time = 1.0 / tick_rate
        self.last_tick_time = time.time()
        self.accumulated_time = 0

        # 帧率统计
        self.fps_history = []
        self.fps_update_time = time.time()
        self.fps_count = 0

    def should_execute_frame(self):
        """
        检查是否应该执行新的帧

        Returns:
            bool: 如果应该执行新帧则返回True
        """
        current_time = time.time()
        delta_time = current_time - self.last_tick_time
        self.last_tick_time = current_time

        # 将时间差累加起来
        self.accumulated_time += delta_time

        # 如果累积时间超过一帧的时间，则应该执行帧
        if self.accumulated_time >= self.frame_time:
            # 减去一帧的时间
            self.accumulated_time -= self.frame_time
            return True

        return False

    def get_frames_to_execute(self):
        """
        获取应该执行的帧数

        Returns:
            int: 应该执行的帧数
        """
        current_time = time.time()
        delta_time = current_time - self.last_tick_time
        self.last_tick_time = current_time

        # 将时间差累加起来
        self.accumulated_time += delta_time

        # 计算应该执行的帧数
        frames_to_execute = int(self.accumulated_time / self.frame_time)

        # 减去已执行帧的时间
        self.accumulated_time -= frames_to_execute * self.frame_time

        # 限制每次最多执行5帧，避免长时间卡顿后出现问题
        return min(frames_to_execute, 5)

    def update_fps(self):
        """
        更新FPS统计

        Returns:
            float: 当前FPS
        """
        self.fps_count += 1
        current_time = time.time()
        elapsed = current_time - self.fps_update_time

        # 每秒更新一次FPS
        if elapsed >= 1.0:
            fps = self.fps_count / elapsed
            self.fps_history.append(fps)

            # 保持历史在合理大小
            if len(self.fps_history) > 60:
                self.fps_history.pop(0)

            # 重置计数
            self.fps_count = 0
            self.fps_update_time = current_time

            return fps

        # 使用最近的FPS
        if self.fps_history:
            return self.fps_history[-1]
        return 0

    def get_average_fps(self):
        """
        获取平均FPS

        Returns:
            float: 平均FPS
        """
        if not self.fps_history:
            return 0
        return sum(self.fps_history) / len(self.fps_history)

    def set_tick_rate(self, tick_rate):
        """
        设置每秒的逻辑帧数

        Args:
            tick_rate: 每秒的逻辑帧数
        """
        self.tick_rate = tick_rate
        self.frame_time = 1.0 / tick_rate