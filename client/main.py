# main.py
"""
客户端主模块：游戏的入口点（单机游戏原型版本）
"""

import pygame
import sys
import os
import math
import random
from common.constants import *
from common.utils import current_time_ms, ensure_dir, vector_from_angle
from common.deterministic_engine import DeterministicPhysics, DeterministicRandom
from client.game_engine.tank import Tank
from client.game_engine.bullet import Bullet
from client.game_engine.map import Map
from client.game_engine.obstacle import WallObstacle, BrickObstacle
from client.game_engine.collision import CollisionSystem
from client.game_engine.particle_system import particle_system


class GameClient:
    """
    游戏客户端：管理整个游戏流程（单机版）

    主要功能：
    - 初始化游戏组件
    - 处理游戏状态
    - 管理游戏循环
    - 处理用户输入
    """

    def __init__(self):
        """初始化游戏客户端"""
        # 初始化pygame
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank Battle - Prototype")
        self.clock = pygame.time.Clock()

        # 确保资源目录存在
        ensure_dir(RESOURCES_DIR)
        ensure_dir(IMAGES_DIR)
        ensure_dir(SOUNDS_DIR)
        ensure_dir(MAPS_DIR)

        # 游戏状态
        self.running = False
        self.paused = False

        # 游戏对象
        self.map = None
        self.player_tank = None
        self.enemy_tanks = []
        self.bullets = []
        self.game_over = False
        self.winner = None

        # 字体
        self.font = pygame.font.SysFont(None, 36)

        # 调试标志
        self.DEBUG = True  # 设置为True开启调试信息

    def start(self):
        """启动游戏"""
        self.running = True

        # 加载地图
        self.map = Map()
        self.map.generate_random_map(seed=42)

        # 确保地图有安全的出生点
        if len(self.map.get_spawn_points()) < 4:
            print("Warning: Not enough safe spawn points. Regenerating map...")
            self.map.generate_random_map(seed=43)  # 尝试不同的种子

        # 用于跟踪已使用的出生点
        used_spawn_points = []

        # 创建玩家坦克
        spawn_point = self.map.get_random_spawn_point(used_spawn_points)
        if spawn_point:
            used_spawn_points.append(spawn_point)
            self.player_tank = Tank(spawn_point[0], spawn_point[1], 'blue', is_player=True)
            print(f"Created player tank at position: {spawn_point}")
        else:
            print("Error: Could not find a safe spawn point for player tank")
            # 使用一个固定的安全位置
            self.player_tank = Tank(self.map.screen_width // 4, self.map.screen_height // 4, 'blue', is_player=True)

        # 创建敌方坦克
        self.enemy_tanks = []
        tank_colors = ['red', 'green', 'yellow']  # 定义不同敌方坦克的颜色

        for i in range(len(tank_colors)):
            enemy_spawn = self.map.get_random_spawn_point(used_spawn_points)
            if enemy_spawn:
                used_spawn_points.append(enemy_spawn)
                enemy_tank = Tank(enemy_spawn[0], enemy_spawn[1], tank_colors[i])
                self.enemy_tanks.append(enemy_tank)
                print(f"Created {tank_colors[i]} tank at position: {enemy_spawn}")
            else:
                # 如果找不到安全的出生点，暂时不添加这个敌方坦克
                print(f"Warning: Could not find a safe spawn point for {tank_colors[i]} tank")

        # 重置游戏状态
        self.bullets = []
        self.game_over = False
        self.winner = None

        # 验证并修复坦克位置
        self._validate_tank_positions()

        # 调试：检查坦克碰撞
        self._debug_check_tank_collisions()

    def _validate_tank_positions(self):
        """验证坦克位置，确保没有重叠"""
        all_tanks = [self.player_tank] + self.enemy_tanks

        for i, tank1 in enumerate(all_tanks):
            for j, tank2 in enumerate(all_tanks):
                if i != j:  # 不与自己比较
                    # 计算两个坦克中心点之间的距离
                    distance = math.sqrt((tank1.x - tank2.x) ** 2 + (tank1.y - tank2.y) ** 2)

                    # 如果距离小于两个坦克宽度之和的一半，认为它们重叠
                    min_distance = (tank1.width + tank2.width) / 2

                    if distance < min_distance:
                        print(f"Warning: Tank {i} ({tank1.color}) overlaps with Tank {j} ({tank2.color})")
                        print(f"  Tank {i} position: ({tank1.x}, {tank1.y})")
                        print(f"  Tank {j} position: ({tank2.x}, {tank2.y})")
                        print(f"  Distance: {distance}, Minimum required: {min_distance}")

                        # 可以在这里尝试修复重叠问题
                        # 例如，稍微移动一个坦克
                        offset = min_distance - distance + 5  # 额外5像素的间距
                        angle = math.atan2(tank2.y - tank1.y, tank2.x - tank1.x)

                        # 将tank2向远离tank1的方向移动
                        tank2.x += math.cos(angle) * offset
                        tank2.y += math.sin(angle) * offset

                        # 更新tank2的碰撞盒
                        tank2.rect = (
                            tank2.x - tank2.width / 2,
                            tank2.y - tank2.height / 2,
                            tank2.width,
                            tank2.height
                        )

                        print(f"  Fixed: Tank {j} moved to ({tank2.x}, {tank2.y})")

    def _debug_check_tank_collisions(self):
        """调试函数：检查坦克是否与障碍物重叠"""
        if not self.DEBUG:
            return

        # 检查玩家坦克
        player_collisions = []

        if self.player_tank:
            # 使用标准碰撞盒检查
            tank_rect = (
                self.player_tank.x - self.player_tank.width / 2,
                self.player_tank.y - self.player_tank.height / 2,
                self.player_tank.width,
                self.player_tank.height
            )

            for obstacle in self.map.obstacles:
                if DeterministicPhysics.check_collision(tank_rect, obstacle.rect):
                    player_collisions.append(obstacle)

            if player_collisions:
                print(f"WARNING: Player tank collides with {len(player_collisions)} obstacles")
                print(f"Player position: ({self.player_tank.x}, {self.player_tank.y})")
                for obs in player_collisions[:3]:  # 只显示前3个
                    print(f"  Obstacle at ({obs.x}, {obs.y})")

        # 检查敌方坦克
        for i, tank in enumerate(self.enemy_tanks):
            enemy_collisions = []

            # 使用标准碰撞盒检查
            tank_rect = (
                tank.x - tank.width / 2,
                tank.y - tank.height / 2,
                tank.width,
                tank.height
            )

            for obstacle in self.map.obstacles:
                if DeterministicPhysics.check_collision(tank_rect, obstacle.rect):
                    enemy_collisions.append(obstacle)

            if enemy_collisions:
                print(f"WARNING: Enemy tank {i} ({tank.color}) collides with {len(enemy_collisions)} obstacles")
                print(f"Enemy position: ({tank.x}, {tank.y})")
                for obs in enemy_collisions[:3]:  # 只显示前3个
                    print(f"  Obstacle at ({obs.x}, {obs.y})")

        # 添加测试代码：检查地图上狭窄通道的宽度
        if self.DEBUG:
            print("\nDebug: Map passages analysis")

            # 检查水平方向的通道
            for y in range(1, self.map.map_height - 1):
                row_obstacles = []
                for x in range(self.map.map_width):
                    grid_obstacles = self.map.get_obstacles_at(x, y)
                    if grid_obstacles:
                        row_obstacles.append((x, y))

                # 检查通道宽度
                if row_obstacles:
                    passage_widths = []
                    last_x = -1
                    for x, y in sorted(row_obstacles):
                        if last_x != -1:
                            passage_width = x - last_x - 1
                            if 0 < passage_width < 3:  # 检查较窄的通道
                                passage_widths.append((last_x, x, passage_width))
                        last_x = x

                    if passage_widths:
                        print(f"Row {y}: Narrow passages detected")
                        for start_x, end_x, width in passage_widths:
                            print(f"  Passage between x={start_x} and x={end_x}, width={width} cells")

            # 检查垂直方向的通道
            for x in range(1, self.map.map_width - 1):
                col_obstacles = []
                for y in range(self.map.map_height):
                    grid_obstacles = self.map.get_obstacles_at(x, y)
                    if grid_obstacles:
                        col_obstacles.append((x, y))

                # 检查通道宽度
                if col_obstacles:
                    passage_widths = []
                    last_y = -1
                    for x, y in sorted(col_obstacles, key=lambda pos: pos[1]):
                        if last_y != -1:
                            passage_width = y - last_y - 1
                            if 0 < passage_width < 3:  # 检查较窄的通道
                                passage_widths.append((last_y, y, passage_width))
                        last_y = y

                    if passage_widths:
                        print(f"Column {x}: Narrow passages detected")
                        for start_y, end_y, width in passage_widths:
                            print(f"  Passage between y={start_y} and y={end_y}, width={width} cells")

    def handle_events(self):
        """处理游戏事件和用户输入"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_p:
                    self.paused = not self.paused
                elif event.key == pygame.K_r and self.game_over:
                    self.start()  # 游戏结束时按R重新开始
                elif event.key == pygame.K_d and event.mod & pygame.KMOD_CTRL:
                    self.DEBUG = not self.DEBUG  # Ctrl+D切换调试模式

                # 玩家坦克控制
                if not self.paused and not self.game_over and self.player_tank:
                    if event.key == pygame.K_SPACE:
                        self.handle_player_shoot()

            elif event.type == pygame.KEYUP:
                # 处理松开按键
                pass

        # 处理按键状态
        if not self.paused and not self.game_over and self.player_tank:
            keys = pygame.key.get_pressed()
            self.handle_player_movement(keys)

    def handle_player_movement(self, keys):
        """处理玩家坦克移动"""
        if not self.player_tank or self.player_tank.is_destroyed:
            return

        # 重置移动标志
        self.player_tank.moving = False

        # 获取障碍物列表
        obstacles = self.map.obstacles

        # 处理移动，尝试各个方向
        moved = False

        if keys[pygame.K_w] or keys[pygame.K_UP]:
            moved = self.player_tank.move_in_direction(Tank.UP, obstacles)
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            moved = self.player_tank.move_in_direction(Tank.RIGHT, obstacles)
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            moved = self.player_tank.move_in_direction(Tank.DOWN, obstacles)
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            moved = self.player_tank.move_in_direction(Tank.LEFT, obstacles)

        # 如果玩家坦克移动了，检查与其他坦克的碰撞
        if moved:
            CollisionSystem.handle_tank_collision(self.player_tank, self.enemy_tanks)

    def handle_player_shoot(self):
        """处理玩家坦克射击"""
        if not self.player_tank or self.player_tank.is_destroyed:
            return

        current_time = current_time_ms()
        bullet_info = self.player_tank.shoot(current_time)

        if bullet_info:
            bullet_x, bullet_y, direction = bullet_info
            bullet = Bullet((bullet_x, bullet_y), direction, self.player_tank.tank_id)
            self.bullets.append(bullet)

    def update(self, delta_time=1 / 60):
        """更新游戏状态"""
        if self.paused or self.game_over:
            return

        # 更新粒子系统
        particle_system.update(delta_time)

        # 更新地图
        self.map.update()

        # 更新玩家坦克
        if self.player_tank and not self.player_tank.is_destroyed:
            self.player_tank.update(delta_time)

        # 更新障碍物
        for obstacle in self.map.obstacles:
            if hasattr(obstacle, 'update'):
                obstacle.update(delta_time)

        # 更新敌方坦克
        for tank in self.enemy_tanks[:]:
            if not tank.is_destroyed:
                tank.update(delta_time)

                # 这里可以添加简单的AI逻辑控制敌方坦克移动
                # 如果实现了敌方AI移动，需要检查碰撞
                # if tank.moving:
                #     CollisionSystem.handle_tank_collision(tank, [self.player_tank] + [t for t in self.enemy_tanks if t != tank])

            # 移除被销毁的坦克
            if tank.is_destroyed:
                self.enemy_tanks.remove(tank)

        # 更新子弹
        current_bullets = []
        for bullet in self.bullets:
            hit_type, hit_obj = bullet.update(delta_time, self.map.obstacles,
                                              [self.player_tank] + self.enemy_tanks)

            # 如果子弹击中了物体，创建火花效果
            if not bullet.active and hit_type:
                # 创建火花效果
                spark_angle = (bullet.direction + 180) % 360  # 火花向相反方向发散
                particle_system.create_spark(
                    x=bullet.x,
                    y=bullet.y,
                    direction_angle=spark_angle,
                    spread_angle=30,
                    count=8,
                    duration=300
                )

            if bullet.active:
                current_bullets.append(bullet)

        self.bullets = current_bullets

        # 检查游戏是否结束
        if self.player_tank and (self.player_tank.health <= 0 or self.player_tank.is_destroyed):
            if not self.game_over:  # 防止重复设置
                self.game_over = True
                self.winner = "Enemy"
        elif not self.enemy_tanks:
            if not self.game_over:  # 防止重复设置
                self.game_over = True
                self.winner = "Player"

    def _draw_debug_collision_boxes(self, surface):
        """绘制碰撞盒，用于调试"""
        if not self.DEBUG:
            return

        # 绘制玩家坦克碰撞盒
        if self.player_tank and not self.player_tank.is_destroyed:
            # 标准碰撞盒
            tank_rect = (
                self.player_tank.x - self.player_tank.width / 2,
                self.player_tank.y - self.player_tank.height / 2,
                self.player_tank.width,
                self.player_tank.height
            )
            pygame.draw.rect(surface, COLOR_RED, tank_rect, 1)

            # 缩小的碰撞盒
            collision_shrink = 2
            shrunk_rect = (
                self.player_tank.x - self.player_tank.width / 2 + collision_shrink,
                self.player_tank.y - self.player_tank.height / 2 + collision_shrink,
                self.player_tank.width - 2 * collision_shrink,
                self.player_tank.height - 2 * collision_shrink
            )
            pygame.draw.rect(surface, COLOR_GREEN, shrunk_rect, 1)

        # 绘制敌方坦克碰撞盒
        for tank in self.enemy_tanks:
            if not tank.is_destroyed:
                # 标准碰撞盒
                tank_rect = (
                    tank.x - tank.width / 2,
                    tank.y - tank.height / 2,
                    tank.width,
                    tank.height
                )
                pygame.draw.rect(surface, COLOR_RED, tank_rect, 1)

                # 缩小的碰撞盒
                collision_shrink = 2
                shrunk_rect = (
                    tank.x - tank.width / 2 + collision_shrink,
                    tank.y - tank.height / 2 + collision_shrink,
                    tank.width - 2 * collision_shrink,
                    tank.height - 2 * collision_shrink
                )
                pygame.draw.rect(surface, COLOR_GREEN, shrunk_rect, 1)

        # 绘制障碍物碰撞盒
        for obstacle in self.map.obstacles:
            pygame.draw.rect(surface, COLOR_BLUE, obstacle.rect, 1)

    def render(self):
        """渲染游戏画面"""
        # 绘制地图和障碍物
        self.map.draw(self.screen)

        # 绘制子弹
        for bullet in self.bullets:
            bullet.draw(self.screen)

        # 绘制坦克
        if self.player_tank and not self.player_tank.is_destroyed:
            self.player_tank.draw(self.screen)

        for tank in self.enemy_tanks:
            tank.draw(self.screen)

        # 绘制粒子效果（要在其他元素之后绘制以确保正确的层次关系）
        particle_system.draw(self.screen)

        # 调试模式：绘制碰撞盒
        if self.DEBUG:
            self._draw_debug_collision_boxes(self.screen)

        # 绘制UI
        self._draw_ui()

        # 如果游戏暂停，显示暂停信息
        if self.paused:
            pause_text = self.font.render("PAUSED - Press P to continue", True, COLOR_WHITE)
            text_rect = pause_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(pause_text, text_rect)

        # 如果游戏结束，显示游戏结束信息
        if self.game_over:
            self._draw_game_over()

        pygame.display.flip()

    def _draw_ui(self):
        """绘制游戏UI"""
        if not self.player_tank:
            return

        # 绘制玩家生命值
        health_text = self.font.render(f"Health: {self.player_tank.health}", True, COLOR_WHITE)
        self.screen.blit(health_text, (10, 10))

        # 绘制玩家弹药
        ammo_text = self.font.render(f"Ammo: {self.player_tank.ammo}", True, COLOR_WHITE)
        self.screen.blit(ammo_text, (10, 50))

        # 绘制敌人数量
        enemies_text = self.font.render(f"Enemies: {len(self.enemy_tanks)}", True, COLOR_WHITE)
        self.screen.blit(enemies_text, (SCREEN_WIDTH - 150, 10))

        # 调试信息：显示当前方向
        direction_text = self.font.render(f"Direction: {self.player_tank.direction}°", True, COLOR_WHITE)
        self.screen.blit(direction_text, (10, 90))

        # 调试模式：显示坦克坐标和粒子数量
        if self.DEBUG:
            debug_y = 130
            # 显示玩家坦克位置
            pos_text = self.font.render(f"Player: ({int(self.player_tank.x)}, {int(self.player_tank.y)})",
                                        True, COLOR_WHITE)
            self.screen.blit(pos_text, (10, debug_y))
            debug_y += 25

            # 显示敌方坦克位置
            for i, tank in enumerate(self.enemy_tanks):
                tank_text = self.font.render(
                    f"{tank.color}: ({int(tank.x)}, {int(tank.y)})",
                    True, COLOR_WHITE
                )
                self.screen.blit(tank_text, (10, debug_y))
                debug_y += 25

            # 显示粒子系统信息
            particle_groups = len(particle_system.particle_groups)
            total_particles = sum(len(particles) for particles in particle_system.particle_groups.values())
            particles_text = self.font.render(
                f"Particles: {total_particles} in {particle_groups} groups",
                True, COLOR_WHITE
            )
            self.screen.blit(particles_text, (10, debug_y))

        # 显示控制提示
        controls_text = self.font.render("WASD: Move | SPACE: Shoot | P: Pause | ESC: Quit", True, COLOR_WHITE)
        self.screen.blit(controls_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT - 30))

    def _draw_game_over(self):
        """绘制游戏结束画面"""
        # 半透明背景
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 128))
        self.screen.blit(overlay, (0, 0))

        # 游戏结束文本
        game_over_text = self.font.render("GAME OVER", True, COLOR_WHITE)
        text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 30))
        self.screen.blit(game_over_text, text_rect)

        # 胜利者文本
        if self.winner:
            winner_text = self.font.render(f"{self.winner} Wins!", True, COLOR_WHITE)
            text_rect = winner_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 10))
            self.screen.blit(winner_text, text_rect)

        # 重新开始提示
        restart_text = self.font.render("Press R to Restart", True, COLOR_WHITE)
        text_rect = restart_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 50))
        self.screen.blit(restart_text, text_rect)

        # 胜利/失败时创建一些粒子效果
        current_time = current_time_ms()
        if not getattr(self, '_victory_particles_created', False):
            self._victory_particles_created = True
            self._victory_particle_time = current_time

            if self.winner == "Player":
                # 玩家胜利，创建庆祝粒子
                for _ in range(5):
                    x = random.randint(0, SCREEN_WIDTH)
                    y = random.randint(0, SCREEN_HEIGHT // 3)
                    colors = [COLOR_YELLOW, COLOR_GREEN, COLOR_BLUE, COLOR_PURPLE, COLOR_PINK]
                    particle_system.create_explosion(
                        x=x, y=y,
                        color_palette=colors,
                        count=20,
                        min_speed=1,
                        max_speed=3,
                        duration=2000,
                        gravity=0.05
                    )

    def run(self):
        """运行游戏主循环"""
        self.start()

        last_time = pygame.time.get_ticks()

        while self.running:
            # 计算帧间时间差，确保动画平滑
            current_time = pygame.time.get_ticks()
            delta_time = (current_time - last_time) / 1000.0  # 转换为秒
            last_time = current_time

            self.handle_events()
            self.update(delta_time)  # 传递时间差到更新函数
            self.render()

            # 限制帧率但保持移动的平滑性
            pygame.time.delay(1)  # 很小的延迟以减少CPU使用
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


# 程序入口
def main():
    """主函数"""
    client = GameClient()
    client.run()


if __name__ == "__main__":
    main()