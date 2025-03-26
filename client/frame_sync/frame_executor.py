# client/frame_sync/frame_executor.py
from collections import defaultdict, deque
import time
from common.constants import *
from client.frame_sync.logical_input_manager import LogicalInputManager


class FrameExecutor:
    def __init__(self, game_client):
        self.game_client = game_client  # 引用游戏客户端实例
        self.current_frame = 0
        self.turn_size = 5  # 与服务器保持一致
        self.input_buffer = {}  # frameId -> {clientId -> [inputs1, inputs2, ...]}
        self.waiting_for_input = False
        self.last_executed_turn = -1
        self.latest_received_frame = -1
        self.missing_frames = []  # 存储缺失的帧ID

        # 时间控制相关
        self.game_start_time = 0
        self.logic_accumulator = 0  # 时间累积器
        self.logic_frame_interval = 1000 / LOGIC_TICK_RATE  # 逻辑帧间隔（毫秒）
        self.last_update_time = 0  # 上次更新时间

        # 逻辑输入管理器
        self.logical_inputs = LogicalInputManager()

    def set_start_time(self, start_time):
        """设置游戏开始时间"""
        self.game_start_time = start_time
        self.last_update_time = start_time
        self.logic_accumulator = 0
        print(f"[FrameExecutor] Set game start time to {start_time}")

    def add_input_frame(self, frame, inputs):
        """添加从服务器接收的输入帧
        inputs格式: {clientId: [inputs1, inputs2, ...]}
        """
        print(f"[FrameExecutor] Adding input frame data for frame {frame}")

        # 处理接收到的输入数据
        if isinstance(frame, int) and isinstance(inputs, dict):
            self.input_buffer[frame] = inputs
            self.latest_received_frame = max(self.latest_received_frame, frame)

            # 计算总输入数量用于调试
            input_count = sum(len(client_inputs) for client_inputs in inputs.values())
            print(f"[FrameExecutor] Added {input_count} inputs across {len(inputs)} clients for frame {frame}")

            # 详细输出
            for client_id, client_inputs in inputs.items():
                print(f"[FrameExecutor] Client {client_id} has {len(client_inputs)} inputs for frame {frame}")
        elif isinstance(inputs, dict):
            # 处理字符串键的输入（来自服务器的JSON）
            for frame_num_str, frame_inputs in inputs.items():
                frame_num = int(frame_num_str)
                self.input_buffer[frame_num] = frame_inputs
                self.latest_received_frame = max(self.latest_received_frame, frame_num)

                # 计算总输入数量用于调试
                input_count = sum(len(client_inputs) for client_inputs in frame_inputs.values())
                print(
                    f"[FrameExecutor] Added {input_count} inputs across {len(frame_inputs)} clients for frame {frame_num}")

        # 如果有缺失的帧，检查是否已经收到
        if self.missing_frames:
            self.missing_frames = [f for f in self.missing_frames if f not in self.input_buffer]

            # 如果所有缺失的帧都收到了
            if not self.missing_frames and self.waiting_for_input:
                self.waiting_for_input = False
                print(f"[FrameExecutor] All missing frames received, resuming execution")

        # 打印当前输入缓冲区状态
        self.debug_print_input_buffer()

    def execute_logic_frame(self):
        """执行逻辑帧更新"""
        current_time = int(time.time() * 1000)

        # 游戏尚未开始
        if current_time < self.game_start_time:
            return

        # 第一次执行，初始化last_update_time
        if self.last_update_time == 0:
            self.last_update_time = self.game_start_time
            return

        # 计算经过的时间
        delta_time = current_time - self.last_update_time
        self.last_update_time = current_time

        # 将实际经过的时间添加到累积器
        self.logic_accumulator += delta_time

        # 当累积器超过帧间隔时执行逻辑帧
        frames_executed = 0
        while self.logic_accumulator >= self.logic_frame_interval:
            # 检查是否需要追帧
            if self.latest_received_frame > self.current_frame:
                # 需要追帧
                if not self.execute_catch_up():
                    break  # 如果追帧失败（等待输入），中断循环
            else:
                # 正常执行当前帧
                if not self.execute_frame():
                    break  # 如果执行失败（等待输入），中断循环

            # 从累积器中减去一个帧间隔
            self.logic_accumulator -= self.logic_frame_interval
            frames_executed += 1

            # 为了防止过度追帧，设置一个最大执行帧数
            if frames_executed > 10:  # 一次最多执行10帧
                print(f"[FrameExecutor] Max frame execution limit reached ({frames_executed} frames)")
                break

        if frames_executed > 0:
            print(f"[FrameExecutor] Executed {frames_executed} logic frames")

    def execute_frame(self):
        """执行当前帧的游戏逻辑"""
        print(f"[FrameExecutor] Executing frame {self.current_frame}")

        # 检查是否是输入帧（turn_size的倍数）
        is_input_frame = self.current_frame != 0 and self.current_frame % self.turn_size == 0

        if is_input_frame:
            print(f"[FrameExecutor] Frame {self.current_frame} is an input frame")

            # 检查当前帧的输入是否存在
            if self.current_frame in self.input_buffer:
                print(f"[FrameExecutor] Found input for frame {self.current_frame}")

                # 更新逻辑输入
                input_frame_data = self.input_buffer[self.current_frame]
                self.logical_inputs.set_input_frame(input_frame_data)

                # 更新游戏状态
                self.game_client.update_game_state()

                # 增加帧计数
                self.current_frame += 1
                print(f"[FrameExecutor] Advanced to frame {self.current_frame}")

                # 不再等待输入
                self.waiting_for_input = False
                return True
            else:
                # 输入帧但没有找到输入，需要等待
                print(f"[FrameExecutor] Input frame {self.current_frame} but no input found, waiting")
                self.waiting_for_input = True
                return False
        else:
            # 非输入帧，仅更新游戏状态，不处理输入
            print(f"[FrameExecutor] Non-input frame {self.current_frame}, updating game state without input processing")

            # 清空逻辑输入
            self.logical_inputs.set_non_input()

            # 更新游戏状态
            self.game_client.update_game_state()

            # 增加帧计数
            self.current_frame += 1
            print(f"[FrameExecutor] Advanced to frame {self.current_frame}")
            return True

    def execute_catch_up(self):
        """执行追帧逻辑"""
        print(f"[FrameExecutor] Trying to catch up from frame {self.current_frame} to {self.latest_received_frame}")

        # 找出所有需要的输入帧
        needed_frames = []
        for frame in range(self.current_frame, self.latest_received_frame + 1):
            if frame % self.turn_size == 0 and frame not in self.input_buffer:
                needed_frames.append(frame)

        if needed_frames:
            # 添加到缺失列表并一次性请求所有缺失的帧
            self.missing_frames = needed_frames
            self.waiting_for_input = True
            print(f"[FrameExecutor] Missing frames detected: {needed_frames}, requesting...")
            self.request_missing_frames(needed_frames)
            return False

        # 尝试执行当前帧
        return self.execute_frame()

    def request_missing_frames(self, frames):
        """请求缺失的输入帧"""
        if not frames:
            return

        print(f"[FrameExecutor] Requesting missing frames: {frames}")

        # 创建请求消息
        request_message = {
            'type': 'request_frames',
            'frames': frames
        }

        # 通过游戏客户端发送请求
        self.game_client.send_message(request_message)

    def debug_print_input_buffer(self):
        """打印当前输入缓冲区状态"""
        print(
            f"[Debug] Input Buffer Status - Current Frame: {self.current_frame}, Latest Received: {self.latest_received_frame}")
        print(f"[Debug] Waiting for input: {self.waiting_for_input}, Missing frames: {self.missing_frames}")

        for frame in sorted(self.input_buffer.keys()):
            inputs = self.input_buffer[frame]
            client_count = len(inputs)
            input_count = sum(len(client_inputs) for client_inputs in inputs.values())
            print(f"  Frame {frame}: {client_count} clients, {input_count} total inputs")

            # 显示每个客户端的输入数量
            for client_id, client_inputs in inputs.items():
                print(f"    Client {client_id}: {len(client_inputs)} inputs")