# collision.py
"""
碰撞检测模块：处理游戏中的所有碰撞检测
"""

from common.utils import distance
from common.deterministic_engine import DeterministicPhysics


class CollisionSystem:
    """
    碰撞系统：处理游戏中的所有碰撞检测

    主要功能：
    - 坦克与障碍物碰撞检测
    - 坦克与坦克碰撞检测
    - 子弹与障碍物碰撞检测
    - 子弹与坦克碰撞检测
    """

    @staticmethod
    def check_tank_obstacle_collision(tank, obstacles):
        """检测坦克与障碍物的碰撞"""
        for obstacle in obstacles:
            if obstacle.destroyed:
                continue

            if DeterministicPhysics.check_collision(tank.rect, obstacle.rect):
                return True, obstacle

        return False, None

    @staticmethod
    def check_tank_tank_collision(tank, other_tanks):
        """检测坦克与其他坦克的碰撞"""
        for other_tank in other_tanks:
            if other_tank.tank_id == tank.tank_id:  # 不与自己碰撞
                continue

            if DeterministicPhysics.check_collision(tank.rect, other_tank.rect):
                return True, other_tank

        return False, None

    @staticmethod
    def check_bullet_obstacle_collision(bullet, obstacles):
        """检测子弹与障碍物的碰撞"""
        for obstacle in obstacles:
            if obstacle.destroyed:
                continue

            if DeterministicPhysics.check_collision(bullet.rect, obstacle.rect):
                return True, obstacle

        return False, None

    @staticmethod
    def check_bullet_tank_collision(bullet, tanks):
        """检测子弹与坦克的碰撞"""
        for tank in tanks:
            if tank.tank_id == bullet.owner_id:  # 子弹不与发射者碰撞
                continue

            if DeterministicPhysics.check_collision(bullet.rect, tank.rect):
                return True, tank

        return False, None

    @staticmethod
    def check_all_collisions(tanks, bullets, obstacles):
        """检测所有可能的碰撞"""
        results = []

        # 检测坦克与障碍物的碰撞
        for tank in tanks:
            collision, obstacle = CollisionSystem.check_tank_obstacle_collision(tank, obstacles)
            if collision:
                results.append(("tank_obstacle", tank, obstacle))

        # 检测坦克与坦克的碰撞
        for i, tank1 in enumerate(tanks):
            for tank2 in tanks[i + 1:]:  # 避免重复检测
                if DeterministicPhysics.check_collision(tank1.rect, tank2.rect):
                    results.append(("tank_tank", tank1, tank2))

        # 检测子弹与障碍物的碰撞
        for bullet in bullets:
            if not bullet.active:
                continue

            collision, obstacle = CollisionSystem.check_bullet_obstacle_collision(bullet, obstacles)
            if collision:
                results.append(("bullet_obstacle", bullet, obstacle))
                bullet.active = False  # 子弹碰撞后消失

        # 检测子弹与坦克的碰撞
        for bullet in bullets:
            if not bullet.active:
                continue

            collision, tank = CollisionSystem.check_bullet_tank_collision(bullet, tanks)
            if collision:
                results.append(("bullet_tank", bullet, tank))
                bullet.active = False  # 子弹碰撞后消失

        return results


# 单元测试
def test_collision():
    """碰撞系统的单元测试"""

    # 创建一个简单的障碍物类来测试
    class TestObstacle:
        def __init__(self, x, y, width, height):
            self.rect = (x, y, width, height)
            self.destroyed = False

    # 创建一个简单的坦克类来测试
    class TestTank:
        def __init__(self, x, y, width, height, tank_id):
            self.rect = (x, y, width, height)
            self.tank_id = tank_id

    # 创建一个简单的子弹类来测试
    class TestBullet:
        def __init__(self, x, y, radius, owner_id):
            self.rect = (x - radius, y - radius, radius * 2, radius * 2)
            self.owner_id = owner_id
            self.active = True

    # 创建测试对象
    obstacle = TestObstacle(100, 100, 50, 50)
    tank1 = TestTank(200, 200, 40, 40, "tank1")
    tank2 = TestTank(250, 200, 40, 40, "tank2")
    bullet = TestBullet(100, 100, 5, "tank1")

    # 测试坦克与障碍物碰撞
    collision, _ = CollisionSystem.check_tank_obstacle_collision(tank1, [obstacle])
    assert not collision  # 坦克不应该与障碍物碰撞

    # 移动坦克使其与障碍物碰撞
    tank1.rect = (100, 100, 40, 40)
    collision, obj = CollisionSystem.check_tank_obstacle_collision(tank1, [obstacle])
    assert collision  # 坦克应该与障碍物碰撞
    assert obj == obstacle

    # 测试坦克与坦克碰撞
    collision, obj = CollisionSystem.check_tank_tank_collision(tank1, [tank2])
    assert not collision  # 坦克不应该相互碰撞

    # 移动坦克使其相互碰撞
    tank2.rect = (120, 120, 40, 40)
    collision, obj = CollisionSystem.check_tank_tank_collision(tank1, [tank2])
    assert collision  # 坦克应该相互碰撞
    assert obj == tank2

    # 测试子弹与障碍物碰撞
    collision, obj = CollisionSystem.check_bullet_obstacle_collision(bullet, [obstacle])
    assert collision  # 子弹应该与障碍物碰撞
    assert obj == obstacle

    # 测试子弹与坦克碰撞
    bullet.rect = (200, 200, 10, 10)  # 移动子弹到坦克位置
    collision, obj = CollisionSystem.check_bullet_tank_collision(bullet, [tank1, tank2])
    assert not collision  # 子弹不应该与自己的坦克碰撞

    bullet.owner_id = "tank2"  # 改变子弹的所有者
    collision, obj = CollisionSystem.check_bullet_tank_collision(bullet, [tank1, tank2])
    assert collision  # 子弹应该与其他坦克碰撞
    assert obj == tank1

    print("All collision tests passed!")


if __name__ == "__main__":
    test_collision()