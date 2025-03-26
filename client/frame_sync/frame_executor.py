# client/frame_sync/frame_executor.py
from collections import defaultdict, deque
from common.constants import *


class FrameExecutor:
    def __init__(self, game_client):
        self.game_client = game_client  # 引用游戏客户端实例
        self.current_frame = 0
        self.turn_size = 5  # 与服务器保持一致
        self.input_buffer = defaultdict(dict)  # frame -> {client_id -> inputs}
        self.waiting_for_input = False
        self.last_executed_turn = -1

    def add_input_frame(self, frame, inputs):
        """添加从服务器接收的输入帧"""
        print(f"[FrameExecutor] Adding input frame data with {len(inputs)} frames")

        # 记录接收到的每个帧的输入
        for frame_num_str, frame_inputs in inputs.items():
            frame_num = int(frame_num_str)
            self.input_buffer[frame_num] = frame_inputs
            print(f"[FrameExecutor] Added inputs for frame {frame_num}: {frame_inputs}")

        # 如果正在等待输入，尝试恢复执行
        if self.waiting_for_input:
            print(f"[FrameExecutor] Was waiting for input, trying to resume execution")
            self.execute_frame()

        # 打印当前输入缓冲区状态
        self.debug_print_input_buffer()

    def execute_frame(self):
        """执行当前帧的游戏逻辑"""
        print(f"[FrameExecutor] Executing frame {self.current_frame}")

        # 检查是否是输入帧（turn_size的倍数）
        is_input_frame = self.current_frame % self.turn_size == 0

        if is_input_frame:
            print(f"[FrameExecutor] Frame {self.current_frame} is an input frame")

            # 检查当前帧的输入是否存在
            if self.current_frame in self.input_buffer:
                print(f"[FrameExecutor] Found input for frame {self.current_frame}")

                # 应用所有客户端的输入
                for client_id, inputs in self.input_buffer[self.current_frame].items():
                    self.apply_input(client_id, inputs)
                    print(f"[FrameExecutor] Applied input from client {client_id} for frame {self.current_frame}")

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

            # 更新游戏状态
            self.game_client.update_game_state()

            # 增加帧计数
            self.current_frame += 1
            print(f"[FrameExecutor] Advanced to frame {self.current_frame}")
            return True

    def apply_input(self, client_id, inputs):
        """将输入应用到对应的游戏对象"""
        # 找到对应client_id的坦克
        tank = None
        if self.game_client.player_tank and self.game_client.player_tank.tank_id == client_id:
            tank = self.game_client.player_tank
        else:
            for enemy_tank in self.game_client.enemy_tanks:
                if enemy_tank.tank_id == client_id:
                    tank = enemy_tank
                    break

        # 应用输入
        if tank:
            tank.apply_input(inputs)
            print(f"[FrameExecutor] Applied input to tank {tank.tank_id}: {inputs}")

            # 处理射击
            if inputs.get('shoot'):
                self.game_client.handle_tank_shoot(tank)
        else:
            print(f"[FrameExecutor] No tank found for client {client_id}")

    def debug_print_input_buffer(self):
        """打印当前输入缓冲区状态"""
        print(f"[Debug] Input Buffer Status - Current Frame: {self.current_frame}")
        for frame in sorted(self.input_buffer.keys()):
            inputs = self.input_buffer[frame]
            print(f"  Frame {frame}: {inputs}")