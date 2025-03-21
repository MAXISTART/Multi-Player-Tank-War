# state_synchronizer.py
"""
状态同步器模块：处理客户端与服务器之间的状态同步

主要功能：
- 发送本地输入到服务器
- 接收和应用服务器状态更新
- 处理预测和校正
"""

import time
import pygame
from common.frame_data import InputFrame, StateFrame
from common.protocol import create_input_message, NetworkLatencyEstimator


class StateSynchronizer:
    """
    状态同步器：处理客户端与服务器之间的状态同步

    主要功能：
    - 管理本地和远程状态
    - 处理状态校正
    - 发送输入和接收状态更新
    """

    def __init__(self, network_client, frame_executor, input_manager, local_player_id):
        """
        初始化状态同步器

        Args:
            network_client: 网络客户端对象
            frame_executor: 帧执行器
            input_manager: 输入管理器
            local_player_id: 本地玩家ID
        """
        self.network_client = network_client
        self.frame_executor = frame_executor
        self.input_manager = input_manager
        self.local_player_id = local_player_id

        # 状态同步参数
        self.input_delay = 2  # 本地输入延迟帧数
        self.prediction_window = 10  # 预测窗口大小

        # 网络延迟估计
        self.latency_estimator = NetworkLatencyEstimator()

        # 状态指标
        self.correction_count = 0
        self.last_mismatch_time = 0
        self.mismatch_count = 0

    def send_input(self, frame_id, input_command):
        """
        发送输入命令到服务器

        Args:
            frame_id: 帧ID
            input_command: 输入命令
        """
        # 创建输入消息
        input_message = create_input_message(
            player_id=self.local_player_id,
            frame_id=frame_id,
            input_command=input_command
        )

        # 发送消息
        self.network_client.send_message(input_message)

        # 存储输入到本地历史
        self.input_manager.store_input(frame_id, input_command)

        # 创建并添加输入帧到帧执行器
        input_frame = InputFrame(frame_id=frame_id)
        input_frame.add_command(self.local_player_id, input_command)
        self.frame_executor.add_input_frame(input_frame)

    def apply_state_update(self, state_frame):
        """
        应用服务器的状态更新

        Args:
            state_frame: 状态帧

        Returns:
            bool: 是否需要进行状态校正
        """
        # 添加状态帧到帧执行器
        self.frame_executor.add_state_frame(state_frame)

        # 更新确认帧
        self.frame_executor.set_confirmed_frame(state_frame.frame_id)

        # 检查是否需要状态校正
        need_correction = self._check_state_mismatch(state_frame)

        if need_correction:
            # 执行状态校正
            self._perform_correction(state_frame)
            self.correction_count += 1

        return need_correction

    def _check_state_mismatch(self, server_state_frame):
        """
        检查本地状态与服务器状态是否不匹配

        Args:
            server_state_frame: 服务器发送的状态帧

        Returns:
            bool: 如果状态不匹配则返回True
        """
        # 如果服务器帧比本地执行的帧新，不进行校验
        if server_state_frame.frame_id > self.frame_executor.last_executed_frame_id:
            return False

        # 如果服务器帧太旧，不进行校验
        if server_state_frame.frame_id < self.frame_executor.last_executed_frame_id - self.prediction_window:
            return False

        # 获取本地状态帧
        local_state_frame = self.frame_executor.frame_buffer.get_state_frame(server_state_frame.frame_id)

        # 如果没有本地帧，需要校正
        if not local_state_frame:
            return True

        # 比较状态校验和
        if local_state_frame.checksum != server_state_frame.checksum:
            # 记录不匹配
            current_time = time.time()
            if current_time - self.last_mismatch_time > 5:  # 每5秒最多记录一次
                self.last_mismatch_time = current_time
                self.mismatch_count += 1
                print(f"State mismatch at frame {server_state_frame.frame_id}")
            return True

        return False

    def _perform_correction(self, server_state_frame):
        """
        执行状态校正

        Args:
            server_state_frame: 服务器发送的状态帧
        """
        # 回滚到服务器帧，并重新执行
        target_frame_id = self.frame_executor.current_frame_id - 1

        # 加载服务器状态
        self.frame_executor.game_engine.load_state(server_state_frame.game_state)

        # 更新执行状态
        self.frame_executor.last_executed_frame_id = server_state_frame.frame_id

        # 执行到当前帧
        if target_frame_id > server_state_frame.frame_id:
            self.frame_executor.execute_frame(target_frame_id)

    def update(self, events, keys_pressed):
        """
        更新状态同步

        Args:
            events: pygame事件列表
            keys_pressed: pygame按键状态

        Returns:
            bool: 是否有新的帧执行
        """
        # 计算目标帧（考虑输入延迟）
        target_frame_id = self.frame_executor.current_frame_id + self.input_delay

        # 捕获当前输入
        input_command = self.input_manager.capture_input(events, keys_pressed)

        # 发送输入到服务器
        self.send_input(target_frame_id, input_command)

        # 执行当前帧（帧执行器内部会决定是否需要回滚）
        frame_executed = self.frame_executor.execute_frame()

        return frame_executed

    def get_statistics(self):
        """
        获取同步统计信息

        Returns:
            dict: 同步统计信息
        """
        return {
            'current_frame': self.frame_executor.current_frame_id,
            'confirmed_frame': self.frame_executor.last_confirmed_frame_id,
            'input_delay': self.input_delay,
            'latency': self.latency_estimator.get_average_rtt(),
            'corrections': self.correction_count,
            'mismatches': self.mismatch_count,
            'rollbacks': self.frame_executor.rollback_count
        }

    def adjust_input_delay(self):
        """根据网络延迟自动调整输入延迟"""
        # 获取平均往返时间（毫秒）
        avg_rtt = self.latency_estimator.get_average_rtt()

        # 计算需要的帧数（每帧33.3ms，对应30FPS）
        frames_needed = int(avg_rtt / (1000 / TICK_RATE)) + 1

        # 确保最小延迟
        self.input_delay = max(2, min(frames_needed, 10))