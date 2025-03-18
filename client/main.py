# main.py
"""
客户端主模块：游戏的入口点（单机游戏原型版本）
"""

import pygame
import sys
import os
from common.constants import *
from common.utils import current_time_ms, ensure_dir
from client.game_engine.tank import Tank
from client.game_engine.bullet import Bullet
from client.game_engine.map import Map
from client.game_engine.obstacle import WallObstacle, BrickObstacle
from client.game_engine.collision import CollisionSystem


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

    def start(self):
        """启动游戏"""
        self.running = True

        # 加载地图
        self.map = Map()
        self.map.generate_random_map(seed=42)

        # 创建玩家坦克
        spawn_point = self.map.get_random_spawn_point()
        self.player_tank = Tank(spawn_point[0], spawn_point[1], 'blue', is_player=True)

        # 创建敌方坦克
        for i in range(3):  # 创建3个敌方坦克
            enemy_spawn = self.map.get_random_spawn_point()
            while enemy_spawn == spawn_point:  # 确保敌方坦克不会出现在玩家坦克的位置
                enemy_spawn = self.map.get_random_spawn_point()

            enemy_color = 'red' if i == 0 else 'green' if i == 1 else 'yellow'
            enemy_tank = Tank(enemy_spawn[0], enemy_spawn[1], enemy_color)
            self.enemy_tanks.append(enemy_tank)

        # 重置游戏状态
        self.bullets = []
        self.game_over = False
        self.winner = None

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
        # 重置移动标志
        self.player_tank.moving = False

        # 处理移动
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            self.player_tank.direction = 0  # 上
            self.player_tank.moving = True
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.player_tank.direction = 90  # 右
            self.player_tank.moving = True
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            self.player_tank.direction = 180  # 下
            self.player_tank.moving = True
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.player_tank.direction = 270  # 左
            self.player_tank.moving = True

        # 更新图像以反映新方向
        self.player_tank.update_image()

        # 移动坦克（处理碰撞）
        if self.player_tank.moving:
            obstacles = self.map.obstacles
            other_tanks = self.enemy_tanks
            self.player_tank.move(obstacles=obstacles)

            # 检查与其他坦克的碰撞
            collision, _ = CollisionSystem.check_tank_tank_collision(
                self.player_tank, other_tanks
            )
            if collision:
                # 如果碰撞，回退移动
                self.player_tank.x = self.player_tank.rect[0] + self.player_tank.width / 2
                self.player_tank.y = self.player_tank.rect[1] + self.player_tank.height / 2

    def handle_player_shoot(self):
        """处理玩家坦克射击"""
        if not self.player_tank:
            return

        current_time = current_time_ms()
        bullet_info = self.player_tank.shoot(current_time)

        if bullet_info:
            bullet_x, bullet_y, direction = bullet_info
            bullet = Bullet((bullet_x, bullet_y), direction, self.player_tank.tank_id)
            self.bullets.append(bullet)

    def update(self):
        """更新游戏状态"""
        if self.paused or self.game_over:
            return

        # 更新地图
        self.map.update()

        # 更新敌方坦克（简单AI：随机移动和射击）
        for tank in self.enemy_tanks:
            # 此处实现简单的敌方坦克AI逻辑
            pass

        # 更新子弹
        current_bullets = []
        for bullet in self.bullets:
            hit_type, hit_obj = bullet.update(1 / 60, self.map.obstacles,
                                              [self.player_tank] + self.enemy_tanks)

            if hit_type == "tank":
                # 检查坦克是否被摧毁
                if hit_obj.health <= 0:
                    if hit_obj == self.player_tank:
                        self.game_over = True
                        self.winner = "Enemy"
                    else:
                        self.enemy_tanks.remove(hit_obj)
                        if not self.enemy_tanks:
                            self.game_over = True
                            self.winner = "Player"

            if bullet.active:
                current_bullets.append(bullet)

        self.bullets = current_bullets

        # 检查游戏是否结束
        if self.player_tank and self.player_tank.health <= 0:
            self.game_over = True
            self.winner = "Enemy"
        elif not self.enemy_tanks:
            self.game_over = True
            self.winner = "Player"

    def render(self):
        """渲染游戏画面"""
        # 绘制地图和障碍物
        self.map.draw(self.screen)

        # 绘制子弹
        for bullet in self.bullets:
            bullet.draw(self.screen)

        # 绘制坦克
        if self.player_tank:
            self.player_tank.draw(self.screen)

        for tank in self.enemy_tanks:
            tank.draw(self.screen)

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

    def run(self):
        """运行游戏主循环"""
        self.start()

        while self.running:
            self.handle_events()
            self.update()
            self.render()
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