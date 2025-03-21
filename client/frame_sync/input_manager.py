# input_manager.py
"""
输入管理器模块：捕获和处理玩家输入

主要功能：
- 捕获键盘/鼠标输入
- 将原始输入转换为确定性输入命令
- 维护输入历史和预测
"""

import pygame
import time
from common.constants import *
from common.frame_data import InputCommand


class InputManager:
    """
    输入管理器：捕获和处理玩家输入

    主要功能：
    - 捕获键盘/鼠标输入
    - 将输入映射到游戏动作
    - 生成输入命令
    """

    def __init__(self, player_id=None):
        """初始化输入管理器"""
        self.player_id = player_id
        self.last_command = None
        self.input_history = {}  # 帧ID -> 输入命令的映射

    def capture_input(self, events, keys_pressed):
        """
        捕获当前帧的输入

        Args:
            events: pygame事件列表
            keys_pressed: pygame按键状态

        Returns:
            InputCommand: 当前帧的输入命令
        """
        # 检测移动输入
        movement = None
        if keys_pressed[pygame.K_w] or keys_pressed[pygame.K_UP]:
            movement = 'up'
        elif keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]:
            movement = 'right'
        elif keys_pressed[pygame.K_s] or keys_pressed[pygame.K_DOWN]:
            movement = 'down'
        elif keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]:
            movement = 'left'
        else:
            movement = 'stop'

        # 检测射击输入
        shooting = False
        for event in events:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                shooting = True
                break

        # 创建输入命令
        command = InputCommand(
            player_id=self.player_id,
            movement=movement,
            shooting=shooting
        )

        # 更新最后的命令
        self.last_command = command

        return command

    def store_input(self, frame_id, command):
        """存储输入历史"""
        self.input_history[frame_id] = command

        # 保持历史记录在合理大小
        while len(self.input_history) > 300:  # 存储最近300帧
            oldest_frame_id = min(self.input_history.keys())
            del self.input_history[oldest_frame_id]

    def get_input(self, frame_id):
        """获取指定帧的输入"""
        return self.input_history.get(frame_id, None)

    def predict_input(self, current_frame_id, target_frame_id):
        """
        预测未来帧的输入

        Args:
            current_frame_id: 当前帧ID
            target_frame_id: 目标帧ID

        Returns:
            InputCommand: 预测的输入命令
        """
        if current_frame_id >= target_frame_id:
            return self.get_input(target_frame_id)

        # 如果有最后的命令，则假设玩家继续相同的输入
        if self.last_command:
            # 创建一个新的输入命令，避免修改原始命令
            predicted_command = InputCommand(
                player_id=self.last_command.player_id,
                movement=self.last_command.movement,
                shooting=False  # 通常不预测射击动作
            )
            return predicted_command

        # 没有历史输入，返回停止命令
        return InputCommand(player_id=self.player_id, movement='stop')

    def clear_history(self):
        """清空输入历史"""
        self.input_history.clear()
        self.last_command = None


class InputBuffer:
    """
    输入缓冲区：管理多个玩家的输入

    主要功能：
    - 存储所有玩家的输入
    - 提供输入查询功能
    """

    def __init__(self):
        """初始化输入缓冲区"""
        self.inputs = {}  # (frame_id, player_id) -> 输入命令的映射

    def add_input(self, frame_id, player_id, command):
        """
        添加输入命令

        Args:
            frame_id: 帧ID
            player_id: 玩家ID
            command: 输入命令
        """
        self.inputs[(frame_id, player_id)] = command

    def get_input(self, frame_id, player_id):
        """
        获取指定帧和玩家的输入

        Args:
            frame_id: 帧ID
            player_id: 玩家ID

        Returns:
            InputCommand: 输入命令，如果不存在则返回None
        """
        return self.inputs.get((frame_id, player_id), None)

    def get_frame_inputs(self, frame_id):
        """
        获取指定帧的所有输入

        Args:
            frame_id: 帧ID

        Returns:
            Dict[player_id, InputCommand]: 玩家ID到输入命令的映射
        """
        result = {}
        for (fid, pid), command in self.inputs.items():
            if fid == frame_id:
                result[pid] = command
        return result

    def clear_before(self, frame_id):
        """
        清除指定帧之前的所有输入

        Args:
            frame_id: 帧ID
        """
        keys_to_remove = [key for key in self.inputs.keys() if key[0] < frame_id]
        for key in keys_to_remove:
            del self.inputs[key]

    def clear_all(self):
        """清空所有输入"""
        self.inputs.clear()