# server/frame_sync/frame_manager.py
import time
from collections import defaultdict


class FrameManager:
    def __init__(self, turn_size=5):
        self.current_frame = 0
        self.turn_size = turn_size  # 每个turn的帧数
        self.clients = {}  # client_id -> client_session

        # 临时输入缓冲区: {client_id -> [inputs1, inputs2, ...]}
        # 这里只存储客户端发来的尚未处理的输入
        self.input_buffer = defaultdict(list)

        # 历史输入记录: {turn_id -> {client_id -> [inputs1, inputs2, ...]}}
        # 这里存储已经处理过的每个turn的输入
        self.input_history = defaultdict(lambda: defaultdict(list))

        self.ready_clients = set()  # 准备好的客户端
        self.game_started = False
        self.game_start_time = 0
        self.last_broadcast_frame = -1  # 上次广播的帧
        self.last_processed_turn = -1  # 上次处理的turn

    def add_client(self, client_id, client_session):
        """添加客户端连接"""
        self.clients[client_id] = client_session

    def remove_client(self, client_id):
        """移除客户端连接"""
        if client_id in self.clients:
            del self.clients[client_id]
        if client_id in self.input_buffer:
            del self.input_buffer[client_id]
        if client_id in self.ready_clients:
            self.ready_clients.remove(client_id)

    def is_input_empty(self, inputs):
        """检查输入是否为空"""
        if not inputs:
            return True
        return inputs.get('movement') == 'stop' and not inputs.get('shoot', False)

    def receive_input(self, client_id, inputs):
        """接收客户端输入，存入临时缓冲区"""
        # 如果输入为空（即默认状态），不进行处理
        if self.is_input_empty(inputs):
            print(f"[FrameManager] Received empty input from client {client_id}, ignoring")
            return

        # 将输入添加到对应客户端的临时缓冲区列表中
        self.input_buffer[client_id].append(inputs)
        print(f"[FrameManager] Added input from client {client_id} to input buffer: {inputs}")
        print(f"[FrameManager] Client {client_id} now has {len(self.input_buffer[client_id])} inputs in buffer")

    def process_inputs_for_turn(self, turn_id):
        """处理临时缓冲区中的输入，移动到历史记录中"""
        # 只在处理新的turn时执行
        if turn_id <= self.last_processed_turn:
            print(f"[FrameManager] Turn {turn_id} already processed, skipping")
            return

        print(f"[FrameManager] Processing inputs for turn {turn_id}")

        # 将临时缓冲区中的输入移到历史记录中
        for client_id, inputs_list in self.input_buffer.items():
            if inputs_list:  # 只处理非空输入列表
                self.input_history[turn_id][client_id] = inputs_list.copy()
                print(
                    f"[FrameManager] Moved {len(inputs_list)} inputs from client {client_id} to history for turn {turn_id}")

        # 清空临时缓冲区
        self.input_buffer = defaultdict(list)
        print(f"[FrameManager] Cleared input buffer after processing turn {turn_id}")

        # 更新最后处理的turn
        self.last_processed_turn = turn_id

        # 调试输出历史记录状态
        self.debug_print_buffers()

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

        # 初始化第0个turn的历史记录(空的)
        turn_id = 0
        for client_id in self.clients:
            # 确保每个客户端在turn 0有一个空的输入列表
            _ = self.input_history[turn_id][client_id]  # 利用defaultdict自动创建空列表
            print(f"[FrameManager] Initialized empty input history for client {client_id} at turn {turn_id}")

        print(f"[FrameManager] Game starting at {self.game_start_time} (current time + {delay_ms}ms)")
        self.debug_print_buffers()
        return self.game_start_time

    def get_client_inputs_for_turn(self, turn_id):
        """获取某个turn的所有客户端历史输入，确保每个客户端都有输入列表"""
        turn_inputs = {}

        # 确保每个客户端都有输入数据，即使是空列表
        for client_id in self.clients:
            if turn_id in self.input_history and client_id in self.input_history[turn_id]:
                # 客户端在这个turn有历史输入，使用现有输入
                turn_inputs[client_id] = self.input_history[turn_id][client_id]
            else:
                # 客户端在这个turn没有历史输入，提供空列表
                turn_inputs[client_id] = []

        return turn_inputs

    def prepare_input_broadcast(self):
        """准备广播给所有客户端的输入数据"""
        # 确定需要广播的输入帧
        current_turn = self.current_frame // self.turn_size
        current_frame = current_turn * self.turn_size

        # 收集这个turn的所有客户端输入
        turn_inputs = self.get_client_inputs_for_turn(current_turn)

        # 记录最后广播的帧
        self.last_broadcast_frame = current_frame

        # 打印调试信息
        client_count = len(turn_inputs)
        input_count = sum(len(inputs) for inputs in turn_inputs.values())
        print(
            f"[Server] Prepared broadcast for frame {current_frame} (turn {current_turn}) with {client_count} clients and {input_count} total inputs")

        # 详细输出每个客户端的输入状态
        for client_id, inputs in turn_inputs.items():
            input_status = f"{len(inputs)} inputs" if inputs else "empty input list"
            print(f"[Server] Client {client_id}: {input_status}")

        # 返回需要广播的数据
        return {
            'type': 'input_frame',
            'current_frame': current_frame,
            'inputs': turn_inputs
        }

    def collect_inputs_for_frame(self, frame):
        """收集特定帧的输入数据（用于响应客户端请求）"""
        turn = frame // self.turn_size

        # 获取该turn的所有客户端输入
        turn_inputs = self.get_client_inputs_for_turn(turn)

        # 添加到结果中
        result = {str(frame): turn_inputs}

        # 打印调试信息
        input_count = sum(len(inputs) for inputs in turn_inputs.values())
        print(
            f"[Server] Prepared response for frame {frame} (turn {turn}) with {len(turn_inputs)} clients and {input_count} total inputs")

        return result

    def reset(self):
        """重置帧管理器状态"""
        self.current_frame = 0
        self.input_buffer = defaultdict(list)
        self.input_history = defaultdict(lambda: defaultdict(list))
        self.ready_clients = set()
        self.game_started = False
        self.game_start_time = 0
        self.last_broadcast_frame = -1
        self.last_processed_turn = -1
        print("[FrameManager] Reset complete")

    def debug_print_buffers(self):
        """打印当前输入缓冲区和历史记录状态"""
        print(
            f"[Debug] FrameManager Status - Current Frame: {self.current_frame}, Last Processed Turn: {self.last_processed_turn}")

        # 打印临时缓冲区
        print("[Debug] Temporary Input Buffer:")
        if not self.input_buffer:
            print("  Empty buffer")
        else:
            for client_id, inputs_list in self.input_buffer.items():
                input_count = len(inputs_list)
                if input_count > 0:
                    print(f"  Client {client_id}: {input_count} inputs in buffer")
                    # 打印每个输入的详细信息（限制数量以避免日志过长）
                    for i, input_data in enumerate(inputs_list[:3]):  # 只显示前3个输入
                        print(f"    Input {i + 1}: {input_data}")
                    if len(inputs_list) > 3:
                        print(f"    ... and {len(inputs_list) - 3} more inputs")

        # 打印历史记录
        print("[Debug] Input History:")
        if not self.input_history:
            print("  No input history yet")
        else:
            for turn in sorted(self.input_history.keys()):
                turn_data = self.input_history[turn]
                client_count = len(turn_data)
                input_count = sum(len(inputs) for inputs in turn_data.values())

                print(
                    f"  Turn {turn} (Frame {turn * self.turn_size}): {client_count} clients, {input_count} total inputs")

                # 只打印有实际输入的客户端详情
                clients_with_inputs = 0
                for client_id, inputs_list in turn_data.items():
                    if inputs_list:  # 只打印非空输入列表
                        clients_with_inputs += 1
                        print(f"    Client {client_id}: {len(inputs_list)} inputs")
                        # 打印每个输入的详细信息（限制数量）
                        for i, input_data in enumerate(inputs_list[:2]):  # 只显示前2个输入
                            print(f"      Input {i + 1}: {input_data}")
                        if len(inputs_list) > 2:
                            print(f"      ... and {len(inputs_list) - 2} more inputs")

                # 如果所有客户端都没有输入，打印提示信息
                if clients_with_inputs == 0:
                    print(f"    All clients have empty input lists")