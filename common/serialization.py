# serialization.py
"""
序列化模块：处理数据的序列化和反序列化
"""

import json
import pickle
import gzip
import base64


class Serializer:
    """
    序列化器：处理数据的序列化和反序列化

    主要功能：
    - 将对象序列化为字节
    - 将字节反序列化为对象
    - 支持不同的序列化格式
    """

    @staticmethod
    def serialize_json(obj):
        """将对象序列化为JSON字符串"""
        return json.dumps(obj)

    @staticmethod
    def deserialize_json(json_str):
        """将JSON字符串反序列化为对象"""
        return json.loads(json_str)

    @staticmethod
    def serialize_binary(obj):
        """将对象序列化为二进制格式"""
        return pickle.dumps(obj)

    @staticmethod
    def deserialize_binary(binary_data):
        """将二进制数据反序列化为对象"""
        return pickle.loads(binary_data)

    @staticmethod
    def serialize_game_state(game_state):
        """序列化游戏状态"""
        # 简化游戏状态，只保留必要信息
        state = {
            'tanks': [tank.serialize() for tank in game_state.get('tanks', [])],
            'bullets': [bullet.serialize() for bullet in game_state.get('bullets', [])],
            'obstacles': [obstacle.serialize() for obstacle in game_state.get('obstacles', [])],
            'map': game_state.get('map').serialize() if 'map' in game_state else None,
            'frame': game_state.get('frame', 0),
            'time': game_state.get('time', 0)
        }
        return Serializer.serialize_json(state)

    @staticmethod
    def deserialize_game_state(data):
        """反序列化游戏状态"""
        state = Serializer.deserialize_json(data)
        # 注意：这里需要从序列化数据重建完整的游戏对象
        # 在实际实现中，可能需要导入特定的类
        return state

    @staticmethod
    def serialize_player_input(player_input):
        """序列化玩家输入"""
        # 简化输入数据，优化大小
        input_data = {
            'movement': player_input.get('movement'),
            'shooting': player_input.get('shooting', False),
            'special': player_input.get('special')
        }
        return Serializer.serialize_json(input_data)

    @staticmethod
    def deserialize_player_input(data):
        """反序列化玩家输入"""
        return Serializer.deserialize_json(data)

    @staticmethod
    def compress(data):
        """压缩序列化数据"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        compressed = gzip.compress(data)
        return base64.b64encode(compressed).decode('ascii')

    @staticmethod
    def decompress(compressed_data):
        """解压序列化数据"""
        decoded = base64.b64decode(compressed_data)
        decompressed = gzip.decompress(decoded)
        try:
            return decompressed.decode('utf-8')
        except UnicodeDecodeError:
            return decompressed  # 返回二进制数据


# 单元测试
def test_serialization():
    """序列化模块的单元测试"""
    # 测试JSON序列化
    test_obj = {'name': 'Tank', 'position': [100, 200], 'health': 100}
    json_str = Serializer.serialize_json(test_obj)
    deserialize_obj = Serializer.deserialize_json(json_str)
    assert deserialize_obj == test_obj

    # 测试二进制序列化
    binary_data = Serializer.serialize_binary(test_obj)
    deserialized_obj = Serializer.deserialize_binary(binary_data)
    assert deserialized_obj == test_obj

    # 测试压缩功能
    large_data = "x" * 1000  # 创建一个大字符串
    compressed = Serializer.compress(large_data)
    decompressed = Serializer.decompress(compressed)
    assert decompressed == large_data

    # 测试玩家输入序列化
    player_input = {'movement': [1, 0], 'shooting': True, 'special': None}
    input_str = Serializer.serialize_player_input(player_input)
    deserialized_input = Serializer.deserialize_player_input(input_str)
    assert deserialized_input == player_input

    print("All serialization tests passed!")


if __name__ == "__main__":
    test_serialization()