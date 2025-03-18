# map.py
"""
地图类模块：定义游戏地图和关卡
"""

import pygame
import random
import os
import json
from common.constants import *
from common.utils import ensure_dir
from client.game_engine.obstacle import WallObstacle, BrickObstacle
from common.deterministic_engine import DeterministicRandom


class Map:
    """
    地图类：管理游戏地图、障碍物和出生点

    主要功能：
    - 初始化地图
    - 加载地图布局
    - 管理障碍物
    - 提供出生点
    - 绘制地图
    """

    def __init__(self, width=MAP_WIDTH, height=MAP_HEIGHT, seed=None):
        """初始化地图对象"""
        self.width = width  # 格子数
        self.height = height
        self.grid_size = GRID_SIZE
        self.screen_width = width * self.grid_size
        self.screen_height = height * self.grid_size

        self.obstacles = []
        self.spawn_points = []
        self.random = DeterministicRandom(seed)

        # 背景图像
        self.background_image = None
        self.load_background()

    def load_background(self):
        """加载背景图像"""
        try:
            # 尝试加载图像
            image_path = os.path.join(IMAGES_DIR, "background.png")
            if os.path.exists(image_path):
                self.background_image = pygame.image.load(image_path).convert()
                self.background_image = pygame.transform.scale(
                    self.background_image, (self.screen_width, self.screen_height)
                )
        except pygame.error:
            # 如果加载失败，创建一个默认背景
            self.background_image = pygame.Surface((self.screen_width, self.screen_height))
            self.background_image.fill(COLOR_DARK_GREEN)

            # 添加一些网格线
            for x in range(0, self.screen_width, self.grid_size):
                pygame.draw.line(self.background_image, COLOR_BLACK,
                                 (x, 0), (x, self.screen_height), 1)
            for y in range(0, self.screen_height, self.grid_size):
                pygame.draw.line(self.background_image, COLOR_BLACK,
                                 (0, y), (self.screen_width, y), 1)

    def add_obstacle(self, obstacle):
        """添加障碍物到地图"""
        self.obstacles.append(obstacle)

    def remove_obstacle(self, obstacle):
        """从地图移除障碍物"""
        if obstacle in self.obstacles:
            self.obstacles.remove(obstacle)

    def get_spawn_points(self):
        """获取所有可用的出生点位置"""
        if not self.spawn_points:
            # 如果没有预定义的出生点，创建一些默认的
            self.spawn_points = [
                (self.grid_size, self.grid_size),
                (self.screen_width - self.grid_size, self.grid_size),
                (self.grid_size, self.screen_height - self.grid_size),
                (self.screen_width - self.grid_size, self.screen_height - self.grid_size)
            ]
        return self.spawn_points

    def get_random_spawn_point(self):
        """随机获取一个出生点位置"""
        spawn_points = self.get_spawn_points()
        if spawn_points:
            return self.random.choice(spawn_points)
        # 如果没有出生点，返回地图中心
        return (self.screen_width // 2, self.screen_height // 2)

    def update(self):
        """更新地图状态（移除已销毁的障碍物等）"""
        # 移除已销毁的障碍物
        self.obstacles = [obs for obs in self.obstacles if not getattr(obs, 'destroyed', False)]

    def draw(self, surface):
        """在屏幕上绘制地图及所有障碍物"""
        # 绘制背景
        if self.background_image:
            surface.blit(self.background_image, (0, 0))
        else:
            surface.fill(COLOR_DARK_GREEN)

        # 绘制所有障碍物
        for obstacle in self.obstacles:
            obstacle.draw(surface)

    def load_from_file(self, filename):
        """从文件加载地图布局"""
        try:
            file_path = os.path.join(MAPS_DIR, filename)
            with open(file_path, 'r') as f:
                map_data = json.load(f)

            # 清除现有障碍物
            self.obstacles = []

            # 设置地图尺寸
            if 'width' in map_data and 'height' in map_data:
                self.width = map_data['width']
                self.height = map_data['height']
                self.screen_width = self.width * self.grid_size
                self.screen_height = self.height * self.grid_size

            # 加载障碍物
            for obstacle_data in map_data.get('obstacles', []):
                x = obstacle_data['x'] * self.grid_size
                y = obstacle_data['y'] * self.grid_size

                if obstacle_data['type'] == 'wall':
                    self.add_obstacle(WallObstacle(x, y, self.grid_size, self.grid_size))
                elif obstacle_data['type'] == 'brick':
                    self.add_obstacle(BrickObstacle(x, y, self.grid_size, self.grid_size))

            # 加载出生点
            self.spawn_points = []
            for spawn in map_data.get('spawn_points', []):
                x = spawn['x'] * self.grid_size
                y = spawn['y'] * self.grid_size
                self.spawn_points.append((x, y))

            return True
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading map: {e}")
            return False

    def generate_random_map(self, seed=None):
        """生成随机地图布局"""
        if seed is not None:
            self.random = DeterministicRandom(seed)

        # 清除现有障碍物
        self.obstacles = []

        # 创建边界墙
        for x in range(self.width):
            self.add_obstacle(WallObstacle(x * self.grid_size, 0, self.grid_size, self.grid_size))
            self.add_obstacle(WallObstacle(x * self.grid_size, (self.height - 1) * self.grid_size,
                                           self.grid_size, self.grid_size))

        for y in range(1, self.height - 1):
            self.add_obstacle(WallObstacle(0, y * self.grid_size, self.grid_size, self.grid_size))
            self.add_obstacle(WallObstacle((self.width - 1) * self.grid_size, y * self.grid_size,
                                           self.grid_size, self.grid_size))

        # 添加一些随机的墙壁和砖块
        for _ in range(self.width * self.height // 10):
            x = self.random.next_int(1, self.width - 2)
            y = self.random.next_int(1, self.height - 2)

            # 避免在出生点附近放置障碍物
            is_near_spawn = False
            for spawn_x, spawn_y in self.get_spawn_points():
                spawn_grid_x = spawn_x // self.grid_size
                spawn_grid_y = spawn_y // self.grid_size
                if abs(x - spawn_grid_x) <= 1 and abs(y - spawn_grid_y) <= 1:
                    is_near_spawn = True
                    break

            if not is_near_spawn:
                if self.random.next_bool(0.3):  # 30%的几率生成墙壁
                    self.add_obstacle(WallObstacle(x * self.grid_size, y * self.grid_size,
                                                   self.grid_size, self.grid_size))
                else:  # 70%的几率生成砖块
                    self.add_obstacle(BrickObstacle(x * self.grid_size, y * self.grid_size,
                                                    self.grid_size, self.grid_size))

        return True

    def serialize(self):
        """将地图状态序列化为字典"""
        return {
            'width': self.width,
            'height': self.height,
            'grid_size': self.grid_size,
            'obstacles': [obs.serialize() for obs in self.obstacles],
            'spawn_points': self.spawn_points
        }

    @classmethod
    def deserialize(cls, data):
        """从序列化数据创建地图"""
        map_obj = cls(data['width'], data['height'])
        map_obj.grid_size = data['grid_size']
        map_obj.screen_width = map_obj.width * map_obj.grid_size
        map_obj.screen_height = map_obj.height * map_obj.grid_size

        # 加载障碍物
        from client.game_engine.obstacle import Obstacle
        map_obj.obstacles = [Obstacle.deserialize(obs_data) for obs_data in data['obstacles']]

        # 加载出生点
        map_obj.spawn_points = data['spawn_points']

        return map_obj

    def calculate_checksum(self):
        """计算地图状态的校验和"""
        # 主要考虑障碍物的状态
        obstacles_checksums = tuple(obs.calculate_checksum() for obs in self.obstacles)
        return hash((self.width, self.height, obstacles_checksums))


# 单元测试
def test_map():
    """地图类的单元测试"""
    # 初始化pygame
    pygame.init()
    screen = pygame.display.set_mode((800, 600))

    # 确保地图目录存在
    ensure_dir(MAPS_DIR)

    # 创建测试地图文件
    test_map_data = {
        'width': 10,
        'height': 8,
        'obstacles': [
            {'x': 1, 'y': 1, 'type': 'wall'},
            {'x': 2, 'y': 1, 'type': 'brick'},
            {'x': 3, 'y': 1, 'type': 'wall'}
        ],
        'spawn_points': [
            {'x': 1, 'y': 6},
            {'x': 8, 'y': 1}
        ]
    }

    test_map_path = os.path.join(MAPS_DIR, "test_map.json")
    with open(test_map_path, 'w') as f:
        json.dump(test_map_data, f)

    # 创建地图
    game_map = Map()

    # 测试加载地图
    assert game_map.load_from_file("test_map.json")
    assert len(game_map.obstacles) == 3
    assert len(game_map.spawn_points) == 2

    # 测试随机地图生成
    game_map.generate_random_map(seed=42)
    assert len(game_map.obstacles) > 0

    # 测试更新地图（移除已销毁的障碍物）
    brick_obstacle = None
    for obs in game_map.obstacles:
        if isinstance(obs, BrickObstacle):
            brick_obstacle = obs
            break

    if brick_obstacle:
        brick_obstacle.destroyed = True
        initial_obstacle_count = len(game_map.obstacles)
        game_map.update()
        assert len(game_map.obstacles) == initial_obstacle_count - 1

    # 测试序列化和反序列化
    map_data = game_map.serialize()
    new_map = Map.deserialize(map_data)
    assert new_map.width == game_map.width
    assert new_map.height == game_map.height
    assert len(new_map.obstacles) == len(game_map.obstacles)

    # 测试绘制
    game_map.draw(screen)
    pygame.display.flip()

    # 清理测试文件
    os.remove(test_map_path)

    print("All map tests passed!")
    pygame.quit()


if __name__ == "__main__":
    test_map()