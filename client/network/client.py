# client/network/client.py
import asyncio
import websockets
import json
import time
import random
import traceback


class NetworkClient:
    def __init__(self, game_client, server_url="ws://localhost:8766"):
        self.game_client = game_client
        self.server_url = server_url
        self.websocket = None
        self.connected = False
        self.client_id = None
        self.message_queue = asyncio.Queue()
        self.reconnect_interval = 1.0  # 重连间隔（秒）
        self.max_retries = 10  # 最大重试次数
        self.retry_count = 0

    async def connect_with_retry(self):
        """不断尝试连接到服务器，直到成功或达到最大重试次数"""
        if self.retry_count >= self.max_retries:
            print(f"[Client] Reached max retry attempts ({self.max_retries})")
            return False

        try:
            print(f"[Client] Connecting to {self.server_url} (attempt {self.retry_count + 1}/{self.max_retries})...")
            # 设置超时以避免长时间等待
            self.websocket = await asyncio.wait_for(
                websockets.connect(self.server_url),
                timeout=3.0
            )
            self.connected = True
            self.retry_count = 0  # 重置重试计数
            print(f"[Client] Connected to server successfully!")

            # 启动消息处理任务
            asyncio.create_task(self.receiver())
            asyncio.create_task(self.message_handler())

            return True
        except asyncio.TimeoutError:
            print(f"[Client] Connection timed out")
        except ConnectionRefusedError:
            print(f"[Client] Connection refused - server may not be running")
        except Exception as e:
            print(f"[Client] Connection error: {e}")
            print(f"[Client] Trace: {traceback.format_exc()}")

        self.retry_count += 1
        return False

    async def connect(self):
        """连接到游戏服务器（为保持兼容）"""
        return await self.connect_with_retry()

    async def disconnect(self):
        """断开与服务器的连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("[Client] Disconnected from server")

    async def send_message(self, message):
        """发送消息到服务器"""
        if not self.connected:
            print("[Client] Can't send message - not connected")
            return False

        try:
            message_json = json.dumps(message)
            await self.websocket.send(message_json)
            return True
        except Exception as e:
            print(f"[Client] Send error: {e}")
            self.connected = False
            # 自动重连
            asyncio.create_task(self.reconnect())
            return False

    async def reconnect(self):
        """断线重连"""
        print("[Client] Attempting to reconnect...")
        self.connected = False
        self.retry_count = 0  # 重置重试计数
        await self.reconnect_with_exponential_backoff()

    async def reconnect_with_exponential_backoff(self):
        """使用指数退避策略进行重连"""
        retry_delay = 1.0  # 初始延迟1秒
        max_delay = 30.0  # 最大延迟30秒

        while self.retry_count < self.max_retries and not self.connected:
            print(
                f"[Client] Reconnecting attempt {self.retry_count + 1}/{self.max_retries}, waiting {retry_delay:.1f}s...")
            await asyncio.sleep(retry_delay)

            success = await self.connect_with_retry()
            if success:
                print("[Client] Reconnected successfully!")
                return True

            # 增加延迟，但不超过最大值
            retry_delay = min(retry_delay * 1.5, max_delay)
            self.retry_count += 1

        if not self.connected:
            print("[Client] Failed to reconnect after multiple attempts")
        return self.connected

    async def receiver(self):
        """接收服务器消息"""
        while self.connected and self.game_client.running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                await self.message_queue.put(data)
            except websockets.exceptions.ConnectionClosed:
                print(f"[Client] Connection closed by server")
                self.connected = False
                # 尝试重连
                asyncio.create_task(self.reconnect())
                break
            except Exception as e:
                print(f"[Client] Receive error: {e}")
                self.connected = False
                # 尝试重连
                asyncio.create_task(self.reconnect())
                break

    async def message_handler(self):
        """处理接收到的消息"""
        while self.connected and self.game_client.running:
            try:
                data = await self.message_queue.get()
                self.process_message(data)
                self.message_queue.task_done()
            except Exception as e:
                print(f"[Client] Message handling error: {e}")

    def process_message(self, data):
        """处理服务器消息"""
        msg_type = data.get('type')
        print(f"[Client] Received message type: {msg_type}")

        if msg_type == 'welcome':
            # 服务器欢迎消息，保存客户端ID
            self.client_id = data.get('client_id')
            print(f"[Client] Received client ID: {self.client_id}")
            self.game_client.on_client_id_received(self.client_id)

        elif msg_type == 'game_ready':
            # 游戏准备就绪
            players = data.get('players', 0)
            clients = data.get('clients', [])
            print(f"[Client] Game ready with {players} players")
            self.game_client.on_game_ready(players, clients)

        elif msg_type == 'game_start':
            # 游戏开始
            start_time = data.get('start_time')
            players = data.get('players', 0)
            current_time = int(time.time() * 1000)
            print(
                f"[Client] Game will start at {start_time}, Current time: {current_time}, Delta: {start_time - current_time}ms")
            self.game_client.on_game_start(start_time, players)

        elif msg_type == 'input_frame':
            # 输入帧
            current_frame = data.get('current_frame')
            inputs = data.get('inputs', {})
            inputs_count = sum(
                len(frame_inputs) for frame_num, frame_inputs in inputs.items() if isinstance(frame_inputs, dict))
            print(f"[Client] Received input frame for frame {current_frame}, inputs count: {inputs_count}")

            # 详细输出每个帧的输入，便于调试
            for frame_num, frame_data in inputs.items():
                print(f"[Client] Frame {frame_num} has inputs: {frame_data}")

            self.game_client.on_input_frame(current_frame, inputs)

        elif msg_type == 'frame_response':
            # 响应请求的输入帧
            frames = data.get('frames', {})
            print(f"[Client] Received response for requested frames: {list(frames.keys())}")
            self.game_client.on_frame_response(frames)

    async def send_connect_request(self):
        """发送连接请求"""
        message = {
            'type': 'connect_request'
        }
        print("[Client] Sending connect request")
        await self.send_message(message)

    async def send_client_ready(self):
        """发送客户端就绪消息"""
        message = {
            'type': 'client_ready'
        }
        print("[Client] Sending client ready message")
        await self.send_message(message)

    async def send_input(self, inputs):
        """发送输入到服务器"""
        message = {
            'type': 'input',
            'inputs': inputs
        }
        await self.send_message(message)

    async def request_frames(self, frames):
        """请求特定帧的输入"""
        message = {
            'type': 'request_frames',
            'frames': frames
        }
        print(f"[Client] Requesting frames: {frames}")
        await self.send_message(message)