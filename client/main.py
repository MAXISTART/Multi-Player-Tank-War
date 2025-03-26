# client/main.py
import pygame
import sys
import asyncio
import time
from common.constants import *
from common.utils import current_time_ms
from client.game_engine.tank import Tank
from client.game_engine.bullet import Bullet
from client.game_engine.map import Map
from client.game_engine.particle_system import particle_system
from client.frame_sync.input_manager import InputManager
from client.frame_sync.frame_executor import FrameExecutor
from client.network.client import NetworkClient


class GameClient:
    def __init__(self):
        """初始化游戏客户端"""
        # 初始化pygame
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank Battle - Multiplayer")
        self.clock = pygame.time.Clock()

        # 游戏状态
        self.running = False
        self.paused = False
        self.game_state = STATE_MENU
        self.waiting_for_connection = False
        self.game_ready = False
        self.game_start_time = 0
        self.players_count = 0
        self.player_id = None
        self.all_client_ids = []

        # 加载状态
        self.loading_progress = 0
        self.loading_complete = False

        # 帧同步组件
        self.input_manager = InputManager()
        self.frame_executor = FrameExecutor(self)
        server_url = "ws://localhost:8766"
        print(f"[Client] Initializing with server URL: {server_url}")
        self.network_client = NetworkClient(self, server_url)

        # 游戏对象
        self.map = None
        self.player_tank = None
        self.enemy_tanks = []
        self.bullets = []

        # 字体
        self.font = pygame.font.SysFont(None, 36)
        self.small_font = pygame.font.SysFont(None, 24)

    async def start(self):
        """启动游戏客户端"""
        self.running = True
        self.game_state = STATE_MENU

        # 连接到服务器
        self.waiting_for_connection = True
        asyncio.create_task(self.attempt_connection())

        # 进入游戏循环
        await self.game_loop()

    async def attempt_connection(self):
        """尝试连接到服务器"""
        while self.waiting_for_connection and self.running:
            connected = await self.network_client.connect_with_retry()
            if connected:
                print("[Client] Connected to server")
                await self.network_client.send_connect_request()
                break
            await asyncio.sleep(1)  # 避免过于频繁的连接尝试

    def on_client_id_received(self, client_id):
        """处理收到客户端ID"""
        self.player_id = client_id
        print(f"[Client] Client ID set to: {self.player_id}")

    def on_game_ready(self, players, client_ids):
        """处理游戏准备就绪信号"""
        print(f"[Client] Received game_ready with {players} players")
        self.game_ready = True
        self.waiting_for_connection = False
        self.players_count = players
        self.all_client_ids = client_ids

        # 转换到加载状态
        self.game_state = STATE_LOADING
        print(f"[Client] Changed state to LOADING")

        # 开始异步加载资源
        asyncio.create_task(self.load_game_resources())

    async def load_game_resources(self):
        """异步加载游戏资源"""
        # 模拟资源加载过程
        total_steps = 10
        for i in range(total_steps):
            self.loading_progress = (i + 1) / total_steps
            print(f"[Client] Loading progress: {self.loading_progress * 100:.0f}%")
            await asyncio.sleep(0.1)  # 模拟加载延迟

        # 加载完成，初始化游戏
        self.loading_complete = True
        print(f"[Client] Loading complete, initializing game")

        # 初始化游戏，但不开始执行逻辑
        self.initialize_game()

        print(f"[Client] Game initialized, sending client_ready")

        # 发送客户端准备就绪消息
        await self.network_client.send_client_ready()

    def on_game_start(self, start_time, players):
        """处理游戏开始信号"""
        print(f"[Client] Received game_start with start_time={start_time}, players={players}")
        self.game_start_time = start_time
        self.players_count = players

        # 设置帧执行器的开始时间
        self.frame_executor.set_start_time(start_time)

        current_time = int(time.time() * 1000)
        time_until_start = start_time - current_time
        print(f"[Client] Game will start in {time_until_start}ms")

    def update(self):
        """游戏主更新循环（在game_loop中调用）"""
        current_time = int(time.time() * 1000)

        # 检查游戏是否应该开始
        if self.game_start_time > 0 and current_time >= self.game_start_time and self.game_state != STATE_PLAYING:
            print(f"[Client] Start time reached! Changing state to PLAYING")
            self.game_state = STATE_PLAYING

        # 只有在游戏状态且非暂停时才执行帧逻辑
        if self.game_state == STATE_PLAYING and not self.paused:
            # 捕获输入并发送给服务器（仅当输入非空时）
            inputs = self.input_manager.capture_input()
            if self.input_manager.is_input_non_empty():
                print(f"[Client] Sending non-empty input: {inputs}")
                asyncio.create_task(self.network_client.send_input(inputs))

            # 执行帧更新
            self.frame_executor.execute_logic_frame()

    def on_input_frame(self, frame, inputs):
        """处理输入帧
        inputs格式: {client_id: [inputs1, inputs2, ...]}
        """
        print(f"[Client] Processing input frame {frame} with {len(inputs)} clients")

        # 检查并输出接收到的具体帧数据
        for client_id, inputs_list in inputs.items():
            print(f"[Client] Received {len(inputs_list)} inputs for client {client_id} at frame {frame}")

        # 添加到帧执行器
        self.frame_executor.add_input_frame(frame, inputs)

    def on_frame_response(self, frames):
        """处理服务器响应的帧请求"""
        print(f"[Client] Processing frame response with {len(frames)} frames")

        # 添加到帧执行器
        for frame_num_str, frame_data in frames.items():
            frame_num = int(frame_num_str)
            print(f"[Client] Adding frame response data for frame {frame_num}")
            self.frame_executor.add_input_frame(frame_num, frame_data)

    def send_message(self, message):
        """发送消息到服务器（供帧执行器调用）"""
        asyncio.create_task(self.network_client.send_message(message))

    def initialize_game(self):
        """初始化游戏状态"""
        # 加载地图
        self.map = Map()
        self.map.generate_random_map(seed=42)  # 使用固定种子确保所有客户端生成相同地图

        # 创建坦克等游戏对象
        spawn_points = self.map.get_spawn_points()

        # 根据玩家ID和位置创建坦克
        try:
            player_index = self.all_client_ids.index(self.player_id)
        except ValueError:
            player_index = 0
            print(f"[Client WARNING] Player ID {self.player_id} not found in client list!")

        if spawn_points and player_index < len(spawn_points):
            self.player_tank = Tank(
                spawn_points[player_index][0],
                spawn_points[player_index][1],
                'blue',
                tank_id=self.player_id,
                is_player=True
            )
        else:
            print("[Client ERROR] No suitable spawn point found!")
            # 默认位置
            self.player_tank = Tank(100, 100, 'blue', tank_id=self.player_id, is_player=True)

        # 创建敌方坦克
        self.enemy_tanks = []
        for i, client_id in enumerate(self.all_client_ids):
            if client_id != self.player_id:
                # 选择不同于玩家的颜色
                tank_color = 'red' if i % 3 == 0 else 'green' if i % 3 == 1 else 'yellow'

                # 为敌方坦克选择生成点
                if i < len(spawn_points):
                    enemy_tank = Tank(
                        spawn_points[i][0],
                        spawn_points[i][1],
                        tank_color,
                        tank_id=client_id,
                        is_player=False
                    )
                    self.enemy_tanks.append(enemy_tank)
                    print(f"[Client] Created enemy tank for {client_id} at spawn point {i}")
                else:
                    print(f"[Client ERROR] No spawn point for enemy tank {client_id}!")

        # 重置子弹列表
        self.bullets = []

        print(f"[Client] Game initialized with {len(self.enemy_tanks)} enemy tanks")

    def update_game_state(self):
        """更新游戏状态（由帧执行器调用）"""
        # 应用逻辑输入到游戏对象
        self.apply_inputs_to_game_objects()

        # 更新粒子系统
        particle_system.update(LOGIC_DELTA_TIME)

        # 更新坦克
        if self.player_tank:
            self.player_tank.update(LOGIC_DELTA_TIME)

        for tank in self.enemy_tanks:
            tank.update(LOGIC_DELTA_TIME)

        # 更新子弹
        current_bullets = []
        for bullet in self.bullets:
            hit_type, hit_obj = bullet.update(LOGIC_DELTA_TIME, self.map.obstacles if self.map else [],
                                              [self.player_tank] + self.enemy_tanks if self.player_tank else [])
            if bullet.active:
                current_bullets.append(bullet)

        self.bullets = current_bullets

    def apply_inputs_to_game_objects(self):
        """将逻辑输入应用到游戏对象"""
        # 应用玩家坦克输入
        logical_inputs = self.frame_executor.logical_inputs

        if self.player_tank:
            player_input = logical_inputs.get_client_input(self.player_tank.tank_id)
            self.player_tank.apply_input(player_input, self.map.obstacles)

            # 处理射击
            if player_input.get('shoot'):
                self.handle_tank_shoot(self.player_tank)

            print(f"[FrameExecutor] Applied input to player tank: {player_input}")

        # 应用敌方坦克输入
        for enemy_tank in self.enemy_tanks:
            enemy_input = logical_inputs.get_client_input(enemy_tank.tank_id)
            enemy_tank.apply_input(enemy_input, self.map.obstacles)

            # 处理射击
            if enemy_input.get('shoot'):
                self.handle_tank_shoot(enemy_tank)

            print(f"[FrameExecutor] Applied input to enemy tank {enemy_tank.tank_id}: {enemy_input}")

    def handle_tank_shoot(self, tank):
        """处理坦克射击"""
        current_time = current_time_ms()
        bullet_info = tank.shoot(current_time)

        if bullet_info:
            bullet_x, bullet_y, direction = bullet_info
            bullet = Bullet((bullet_x, bullet_y), direction, tank.tank_id)
            self.bullets.append(bullet)

    def render(self):
        """渲染游戏画面"""
        # 清屏
        self.screen.fill(COLOR_BLACK)

        if self.game_state == STATE_MENU:
            self._draw_menu()
        elif self.game_state == STATE_LOADING:
            self._draw_loading()
        elif self.game_state == STATE_PLAYING:
            self._draw_game()

        pygame.display.flip()

    def _draw_menu(self):
        """绘制菜单画面"""
        # 绘制标题
        title_text = self.font.render("Tank Battle - Multiplayer", True, COLOR_WHITE)
        self.screen.blit(title_text, (SCREEN_WIDTH / 2 - title_text.get_width() / 2, 100))

        if self.waiting_for_connection:
            # 连接中
            connecting_text = self.font.render("Connecting to server...", True, COLOR_WHITE)
            self.screen.blit(connecting_text, (SCREEN_WIDTH / 2 - connecting_text.get_width() / 2, 200))
        else:
            # 未知状态
            status_text = self.font.render("Waiting for server response...", True, COLOR_WHITE)
            self.screen.blit(status_text, (SCREEN_WIDTH / 2 - status_text.get_width() / 2, 200))

    def _draw_loading(self):
        """绘制加载画面"""
        # 绘制标题
        title_text = self.font.render("Loading Game...", True, COLOR_WHITE)
        self.screen.blit(title_text, (SCREEN_WIDTH / 2 - title_text.get_width() / 2, 100))

        # 绘制玩家ID
        if self.player_id:
            player_id_text = self.font.render(f"Your Player ID: {self.player_id[:8]}...", True, COLOR_WHITE)
            self.screen.blit(player_id_text, (SCREEN_WIDTH / 2 - player_id_text.get_width() / 2, 150))

        # 绘制玩家数量
        players_text = self.font.render(f"Players in game: {self.players_count}", True, COLOR_WHITE)
        self.screen.blit(players_text, (SCREEN_WIDTH / 2 - players_text.get_width() / 2, 200))

        # 绘制进度条背景
        progress_bar_width = 400
        progress_bar_height = 30
        progress_bar_x = SCREEN_WIDTH / 2 - progress_bar_width / 2
        progress_bar_y = 250
        pygame.draw.rect(self.screen, COLOR_WHITE,
                         (progress_bar_x, progress_bar_y, progress_bar_width, progress_bar_height), 2)

        # 绘制进度条
        filled_width = int(progress_bar_width * self.loading_progress)
        if filled_width > 0:
            pygame.draw.rect(self.screen, COLOR_GREEN,
                             (progress_bar_x, progress_bar_y, filled_width, progress_bar_height))

        # 绘制进度文本
        progress_text = self.font.render(f"{self.loading_progress * 100:.0f}%", True, COLOR_WHITE)
        self.screen.blit(progress_text, (SCREEN_WIDTH / 2 - progress_text.get_width() / 2, 300))

        # 如果加载完成但还在等待游戏开始
        if self.loading_complete and self.game_start_time > 0:
            current_time = int(time.time() * 1000)
            if current_time < self.game_start_time:
                remaining_ms = self.game_start_time - current_time
                remaining_seconds = max(0, remaining_ms // 1000 + 1)
                waiting_text = self.font.render(f"Starting in {remaining_seconds} seconds...", True, COLOR_WHITE)
                self.screen.blit(waiting_text, (SCREEN_WIDTH / 2 - waiting_text.get_width() / 2, 350))
            else:
                starting_text = self.font.render("Starting now...", True, COLOR_WHITE)
                self.screen.blit(starting_text, (SCREEN_WIDTH / 2 - starting_text.get_width() / 2, 350))

    def _draw_game(self):
        """绘制游戏画面"""
        # 绘制地图
        if self.map:
            self.map.draw(self.screen)

        # 绘制坦克
        if self.player_tank:
            self.player_tank.draw(self.screen)

        for tank in self.enemy_tanks:
            tank.draw(self.screen)

        # 绘制子弹
        for bullet in self.bullets:
            bullet.draw(self.screen)

        # 绘制粒子
        particle_system.draw(self.screen)

        # 添加诊断信息
        self._draw_diagnostics()

    def _draw_diagnostics(self):
        """绘制诊断信息"""
        debug_font = self.small_font
        debug_y = 10
        debug_x = 10
        debug_color = COLOR_WHITE

        # 基本状态信息
        debug_texts = [
            f"Game State: {self.game_state}",
            f"Player ID: {self.player_id[:8] if self.player_id else 'None'}",
            f"Frame: {self.frame_executor.current_frame}",
            f"Latest Received: {self.frame_executor.latest_received_frame}",
            f"Waiting: {self.frame_executor.waiting_for_input}",
            f"Players: {self.players_count}",
            f"Input Buffer Size: {len(self.frame_executor.input_buffer)}"
        ]

        # 绘制所有文本
        for text in debug_texts:
            text_surface = debug_font.render(text, True, debug_color)
            self.screen.blit(text_surface, (debug_x, debug_y))
            debug_y += 20

    async def handle_events(self):
        """处理游戏事件和用户输入"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p and self.game_state == STATE_PLAYING:
                    self.paused = not self.paused

    async def game_loop(self):
        """游戏主循环"""
        while self.running:
            # 处理事件
            await self.handle_events()

            # 更新游戏状态
            self.update()

            # 渲染
            self.render()

            # 控制帧率
            await asyncio.sleep(1 / 120)  # 尝试以120fps运行渲染循环

        # 游戏结束，断开连接
        await self.network_client.disconnect()
        pygame.quit()


# 主入口
def main():
    client = GameClient()
    asyncio.run(client.start())


if __name__ == "__main__":
    main()