# serialization.py
"""
序列化模块：用于游戏数据的序列化和反序列化
提供标准格式转换，确保网络传输的一致性
"""

import json
import pickle
import base64
from common.utils import calculate_checksum


def serialize_inputs(input_data):
    """
    将游戏输入数据序列化为可传输的字符串

    Args:
        input_data: 输入数据字典或对象

    Returns:
        序列化后的字符串
    """
    # 对于简单的输入数据，直接返回原始字典即可
    # 在更复杂的实现中，可能需要更多处理
    return input_data


def deserialize_inputs(serialized_data):
    """
    将序列化的输入数据还原为原始格式

    Args:
        serialized_data: 序列化后的数据

    Returns:
        还原后的输入数据
    """
    # 简单实现，直接返回
    return serialized_data


def serialize_game_state(game_state):
    """
    将完整游戏状态序列化为可传输的字符串

    Args:
        game_state: 游戏状态对象

    Returns:
        序列化后的字符串
    """
    # 使用 pickle 进行完整序列化，并进行 base64 编码
    try:
        pickled = pickle.dumps(game_state)
        return base64.b64encode(pickled).decode('utf-8')
    except Exception as e:
        print(f"Error serializing game state: {e}")
        return None


def deserialize_game_state(serialized_data):
    """
    将序列化的游戏状态还原为原始对象

    Args:
        serialized_data: 序列化后的字符串

    Returns:
        还原后的游戏状态对象
    """
    # 从 base64 解码并使用 pickle 反序列化
    try:
        binary_data = base64.b64decode(serialized_data.encode('utf-8'))
        return pickle.loads(binary_data)
    except Exception as e:
        print(f"Error deserializing game state: {e}")
        return None


def create_input_message(client_id, frame, inputs):
    """
    创建标准格式的输入消息

    Args:
        client_id: 客户端ID
        frame: 帧号
        inputs: 输入数据

    Returns:
        格式化的消息字典
    """
    message = {
        'type': 'input',
        'client_id': client_id,
        'frame': frame,
        'inputs': serialize_inputs(inputs),
        'checksum': calculate_checksum(inputs)
    }
    return message


def create_frame_update_message(frame, inputs, state_checksum=None):
    """
    创建帧更新消息

    Args:
        frame: 当前帧号
        inputs: 所有客户端的输入数据 {client_id: inputs}
        state_checksum: 可选的状态校验和

    Returns:
        格式化的消息字典
    """
    message = {
        'type': 'frame_update',
        'frame': frame,
        'inputs': inputs
    }

    if state_checksum is not None:
        message['state_checksum'] = state_checksum

    return message