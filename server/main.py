# server/main.py
import asyncio
import websockets
import json
import time
import uuid
from collections import defaultdict
from server.frame_sync.frame_manager import FrameManager
from common.constants import LOGIC_TICK_RATE


class GameServer:
    def __init__(self, port=8766, required_players=2):
        self.port = port
        self.clients = {}  # websocket -> client_id
        self.client_details = {}  # client_id -> details
        self.frame_manager = FrameManager()
        self.connection_phase = True
        self.server = None
        self.required_players = required_players  # 需要的玩家数量
        print(f"[Server] Initialized with port {port}, requiring {required_players} players")

    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        # 如果游戏已经开始，拒绝新连接
        if self.frame_manager.game_started:
            print(f"[Server] Rejecting new connection - game already in progress")
            await websocket.close(1000, "Game already in progress")
            return

        client_id = str(uuid.uuid4())
        self.clients[websocket] = client_id
        self.client_details[client_id] = {
            'connected_at': int(time.time()),
            'ready': False
        }

        print(f"[Server] New client connected with ID: {client_id}")
        print(f"[Server] Connected players: {len(self.clients)}/{self.required_players}")

        try:
            # 发送欢迎消息
            welcome_message = {
                'type': 'welcome',
                'client_id': client_id
            }
            await websocket.send(json.dumps(welcome_message))

            # 加入帧管理器
            self.frame_manager.add_client(client_id, websocket)

            # 检查是否已达到所需玩家数量
            if self.connection_phase and len(self.clients) >= self.required_players:
                print(f"[Server] Required number of players ({self.required_players}) reached!")
                # 发送游戏准备消息
                ready_message = {
                    'type': 'game_ready',
                    'players': len(self.clients),
                    'clients': list(self.clients.values())
                }
                print(f"[Server] Broadcasting game_ready message to {len(self.clients)} players")
                await self.broadcast(ready_message)

            # 持续接收消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_message(websocket, client_id, data)
                except json.JSONDecodeError:
                    print(f"[Server] Invalid JSON from client {client_id}")
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[Server] Client {client_id} disconnected: {e.code} {e.reason}")
        except Exception as e:
            print(f"[Server] Error handling client {client_id}: {e}")
        finally:
            # 客户端断开连接，清理资源
            if websocket in self.clients:
                del self.clients[websocket]
            if client_id in self.client_details:
                del self.client_details[client_id]
            self.frame_manager.remove_client(client_id)

            print(
                f"[Server] Client {client_id} removed. Remaining players: {len(self.clients)}/{self.required_players}")

            # 如果游戏已经开始，但玩家数量不足，重置游戏
            if self.frame_manager.game_started and len(self.clients) < self.required_players:
                print(f"[Server] Not enough players to continue. Resetting game.")
                self.reset_game()

    def reset_game(self):
        """重置游戏状态"""
        self.frame_manager = FrameManager()  # 创建新的帧管理器
        self.connection_phase = True
        print(f"[Server] Game reset. Waiting for {self.required_players} players to connect.")

    async def process_message(self, websocket, client_id, data):
        """处理客户端消息"""
        msg_type = data.get('type')
        print(f"[Server] Received {msg_type} message from client {client_id}")

        if msg_type == 'connect_request':
            # 连接请求
            print(f"[Server] Client {client_id} sent connect_request")

        elif msg_type == 'client_ready':
            # 客户端准备就绪
            print(f"[Server] Client {client_id} is ready")

            # 更新客户端状态
            if client_id in self.client_details:
                self.client_details[client_id]['ready'] = True

            # 标记客户端准备就绪
            all_ready = self.frame_manager.mark_client_ready(client_id)

            # 检查是否所有客户端都已准备就绪
            ready_count = sum(1 for details in self.client_details.values() if details['ready'])
            total_count = len(self.clients)
            print(f"[Server] Ready clients: {ready_count}/{total_count}")

            if all_ready:
                # 所有客户端都准备好了，开始游戏
                # 设置游戏开始时间为当前时间+500ms
                start_delay_ms = 500
                game_start_time = self.frame_manager.start_game(start_delay_ms)
                start_message = {
                    'type': 'game_start',
                    'start_time': game_start_time,
                    'players': len(self.clients)
                }
                print(f"[Server] All clients ready, starting game at {game_start_time} (in {start_delay_ms}ms)")
                await self.broadcast(start_message)

        elif msg_type == 'input':
            # 处理客户端输入
            inputs = data.get('inputs')
            print(f"[Server] Input from {client_id}: {inputs}")
            self.frame_manager.receive_input(client_id, inputs)

        elif msg_type == 'request_frames':
            # 处理客户端请求帧数据
            requested_frames = data.get('frames', [])
            print(f"[Server] Client {client_id} requested frames: {requested_frames}")

            response = {}
            for frame in requested_frames:
                frame_data = self.frame_manager.collect_inputs_for_frame(frame)
                if frame_data:
                    response.update(frame_data)

            if response:
                response_message = {
                    'type': 'frame_response',
                    'frames': response
                }
                await websocket.send(json.dumps(response_message))
                print(f"[Server] Sent requested frames to client {client_id}: {list(response.keys())}")

    async def broadcast(self, message):
        """向所有客户端广播消息"""
        if not self.clients:
            print("[Server] No clients to broadcast to")
            return

        message_json = json.dumps(message)
        print(f"[Server] Broadcasting message type: {message.get('type')} to {len(self.clients)} clients")

        # 创建所有发送任务
        send_tasks = []
        for websocket in self.clients:
            try:
                await websocket.send(message_json)
                client_id = self.clients.get(websocket, "unknown")
                print(f"[Server] Sent message to client {client_id}")
            except Exception as e:
                client_id = self.clients.get(websocket, "unknown")
                print(f"[Server] Error sending to client {client_id}: {e}")

    async def start_server(self):
        """启动游戏服务器"""
        # 创建WebSocket服务器
        self.server = await websockets.serve(
            self.handle_client,
            "localhost",  # 使用localhost以便于测试
            self.port
        )

        print(f"[Server] Game server started on localhost:{self.port}")
        print(f"[Server] Waiting for {self.required_players} players to connect...")

        # 启动游戏循环
        await self.game_loop()

    async def game_loop(self):
        """游戏主循环"""
        debug_interval = 5  # 每5秒打印一次调试信息
        last_debug_time = 0

        while True:
            current_time = int(time.time())

            # 定期打印调试信息
            if current_time - last_debug_time >= debug_interval:
                self.print_server_state()
                last_debug_time = current_time

            # 游戏已经开始，处理帧更新
            if self.frame_manager.game_started:
                current_time_ms = int(time.time() * 1000)
                elapsed_time = current_time_ms - self.frame_manager.game_start_time

                # 只有在游戏开始时间已过后才进行帧更新
                if elapsed_time >= 0:
                    # 计算当前应该处于哪一帧
                    frames_should_have_passed = int(elapsed_time * LOGIC_TICK_RATE / 1000)

                    # 更新到当前应该的帧
                    if frames_should_have_passed > self.frame_manager.current_frame:
                        self.frame_manager.current_frame = frames_should_have_passed

                        # 检查是否到达了新的turn
                        current_turn = frames_should_have_passed // self.frame_manager.turn_size

                        # 如果到达了新的turn，先处理输入
                        if frames_should_have_passed % self.frame_manager.turn_size == 0:
                            # 处理当前turn的输入
                            self.frame_manager.process_inputs_for_turn(current_turn)

                            # 广播输入帧
                            current_frame = frames_should_have_passed
                            input_message = self.frame_manager.prepare_input_broadcast()
                            print(f"[Server] Broadcasting inputs for frame {current_frame}")
                            await self.broadcast(input_message)

            # 短暂等待避免CPU占用过高
            await asyncio.sleep(0.01)

    def print_server_state(self):
        """打印服务器当前状态（用于调试）"""
        print("\n=== SERVER STATE ===")
        print(f"Connected clients: {len(self.clients)}/{self.required_players}")
        print(f"Connection phase: {self.connection_phase}")
        print(f"Game started: {self.frame_manager.game_started}")

        if self.client_details:
            print("Client details:")
            for client_id, details in self.client_details.items():
                print(f"  - {client_id[:8]}...: Ready: {details['ready']}")

        if self.frame_manager.game_started:
            print(f"Current frame: {self.frame_manager.current_frame}")
            print(f"Ready clients: {len(self.frame_manager.ready_clients)}/{len(self.clients)}")
            print(f"Game start time: {self.frame_manager.game_start_time}")
        print("===================\n")

    async def stop_server(self):
        """停止服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            print("[Server] Server stopped")


# 主函数
async def main():
    # 可以通过命令行参数来指定所需的玩家数量
    import sys
    required_players = 1  # 默认为2
    if len(sys.argv) > 1:
        try:
            required_players = int(sys.argv[1])
            print(f"[Server] Setting required players to: {required_players}")
        except ValueError:
            print(f"[Server] Invalid player count: {sys.argv[1]}, using default: {required_players}")

    server = GameServer(required_players=required_players)
    try:
        await server.start_server()
    except KeyboardInterrupt:
        print("[Server] Interrupted, shutting down...")
        await server.stop_server()
    except Exception as e:
        print(f"[Server] Error: {e}")
        await server.stop_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[Server] Server shutting down")