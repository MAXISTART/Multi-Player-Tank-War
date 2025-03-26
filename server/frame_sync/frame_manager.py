# server/frame_sync/frame_manager.py
import time
from collections import defaultdict


class FrameManager:
    def __init__(self, turn_size=5):
        self.current_frame = 0
        self.turn_size = turn_size  # 每个turn的帧数
        self.clients = {}  # client_id -> client_session
        self.input_buffer = defaultdict(dict)  # frame -> {client_id -> inputs}
        self.ready_clients = set()  # 准备好的客户端
        self.game_started = False
        self.game_start_time = 0
        self.last_broadcast_frame = -1  # 上次广播的帧

    def add_client(self, client_id, client_session):
        """添加客户端连接"""
        self.clients[client_id] = client_session

    def remove_client(self, client_id):
        """移除客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.ready_clients:
            self.ready_clients.remove(client_id)

    def receive_input(self, client_id, frame, inputs):
        """接收客户端输入"""
        # 将输入存储到下一个应该处理输入的帧
        next_input_frame = ((frame // self.turn_size) + 1) * self.turn_size
        self.input_buffer[next_input_frame][client_id] = inputs
        print(
            f"[FrameManager] Stored input from client {client_id} at frame {frame} for future frame {next_input_frame}: {inputs}")

    def mark_client_ready(self, client_id):
        """标记客户端已准备好"""
        self.ready_clients.add(client_id)
        print(
            f"[FrameManager] Client {client_id} marked as ready. Ready clients: {len(self.ready_clients)}/{len(self.clients)}")
        return len(self.ready_clients) == len(self.clients)

    def start_game(self, delay_ms=500):
        """开始游戏，设置开始时间"""
        self.game_started = True
        self.game_start_time = int(time.time() * 1000) + delay_ms

        # 为每个客户端在第0帧添加默认输入
        default_input = {'movement': 'stop', 'shoot': False}
        for client_id in self.clients:
            self.input_buffer[0][client_id] = default_input
            print(f"[FrameManager] Added default input for client {client_id} at frame 0")

        print(f"[FrameManager] Game starting at {self.game_start_time} (current time + {delay_ms}ms)")
        self.debug_print_input_buffer()
        return self.game_start_time

    def prepare_input_broadcast(self):
        """准备广播给所有客户端的输入数据"""
        # 确定需要广播的输入帧
        current_turn = self.current_frame // self.turn_size
        current_input_frame = current_turn * self.turn_size

        # 收集这个输入帧的所有输入
        turn_inputs = {}

        # 特殊处理：始终包含第0帧
        if 0 in self.input_buffer and self.input_buffer[0]:
            turn_inputs["0"] = self.input_buffer[0]
            print(f"[Server] Including frame 0 inputs in broadcast")

        # 加入当前输入帧
        if current_input_frame in self.input_buffer and self.input_buffer[current_input_frame]:
            turn_inputs[str(current_input_frame)] = self.input_buffer[current_input_frame]
            print(f"[Server] Including frame {current_input_frame} inputs in broadcast")
        else:
            # 如果当前帧没有输入，使用默认输入
            default_input = {}
            for client_id in self.clients:
                default_input[client_id] = {'movement': 'stop', 'shoot': False}
            turn_inputs[str(current_input_frame)] = default_input
            print(f"[Server] Using default inputs for frame {current_input_frame}")

        # 记录最后广播的帧
        self.last_broadcast_frame = current_input_frame

        # 打印调试信息
        input_count = sum(len(inputs) for inputs in turn_inputs.values())
        print(f"[Server] Prepared broadcast for input frame {current_input_frame} with {input_count} total inputs")
        self.debug_print_input_buffer()

        # 返回需要广播的数据
        return {
            'type': 'input_frame',
            'current_frame': current_input_frame,
            'inputs': turn_inputs
        }

    def reset(self):
        """重置帧管理器状态"""
        self.current_frame = 0
        self.input_buffer = defaultdict(dict)
        self.ready_clients = set()
        self.game_started = False
        self.game_start_time = 0
        self.last_broadcast_frame = -1
        print("[FrameManager] Reset complete")

    def debug_print_input_buffer(self):
        """打印当前输入缓冲区状态"""
        print(f"[Debug] Input Buffer Status - Current Frame: {self.current_frame}")
        for frame in sorted(self.input_buffer.keys()):
            inputs = self.input_buffer[frame]
            client_count = len(inputs)
            print(f"  Frame {frame}: {client_count} clients have inputs")
            for client_id, client_input in inputs.items():
                print(f"    Client {client_id}: {client_input}")