# client/tests/test_tank_movement.py
"""
测试坦克移动和旋转是否正常工作
"""

import pygame
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.constants import *
from client.game_engine.tank import Tank
from client.game_engine.map import Map
from client.game_engine.obstacle import WallObstacle


def main():
    """测试坦克移动和旋转"""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Tank Movement Test")
    clock = pygame.time.Clock()

    # 创建地图
    game_map = Map()
    game_map.generate_random_map(seed=42)

    # 创建坦克在地图中央
    tank = Tank(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, 'blue', is_player=True)

    # 显示当前方向和位置的函数
    font = pygame.font.SysFont(None, 24)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        # 处理按键
        keys = pygame.key.get_pressed()

        # 记录移动前的位置
        old_x, old_y = tank.x, tank.y

        # 重置移动标志
        tank.moving = False

        # 处理移动和方向
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            tank.move_in_direction(Tank.UP, game_map.obstacles)
        elif keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            tank.move_in_direction(Tank.RIGHT, game_map.obstacles)
        elif keys[pygame.K_s] or keys[pygame.K_DOWN]:
            tank.move_in_direction(Tank.DOWN, game_map.obstacles)
        elif keys[pygame.K_a] or keys[pygame.K_LEFT]:
            tank.move_in_direction(Tank.LEFT, game_map.obstacles)

        # 清屏
        screen.fill(COLOR_BLACK)

        # 绘制地图
        game_map.draw(screen)

        # 绘制坦克
        tank.draw(screen)

        # 显示信息
        direction_text = font.render(f"Direction: {tank.direction}°", True, COLOR_WHITE)
        screen.blit(direction_text, (10, 10))

        position_text = font.render(f"Position: ({tank.x:.1f}, {tank.y:.1f})", True, COLOR_WHITE)
        screen.blit(position_text, (10, 30))

        moved_text = font.render(
            f"Moved: {tank.x - old_x:.1f}, {tank.y - old_y:.1f}",
            True, COLOR_WHITE
        )
        screen.blit(moved_text, (10, 50))

        # 添加控制提示
        controls_text = font.render("WASD: Move | ESC: Quit", True, COLOR_WHITE)
        screen.blit(controls_text, (10, SCREEN_HEIGHT - 30))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()