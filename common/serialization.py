# common/serialization.py
"""
数据序列化模块：处理游戏对象的序列化和反序列化
"""

import json


def serialize_object(obj):
    """
    将对象序列化为字典

    Args:
        obj: 要序列化的对象

    Returns:
        序列化后的字典
    """
    if hasattr(obj, 'serialize'):
        return obj.serialize()
    elif isinstance(obj, (int, float, str, bool, list, dict, tuple)) or obj is None:
        return obj
    else:
        # 尝试将对象的__dict__序列化
        try:
            return {
                '_type': obj.__class__.__name__,
                **obj.__dict__
            }
        except:
            return f"<non-serializable: {type(obj).__name__}>"


def deserialize_object(data, class_map=None):
    """
    从字典反序列化对象

    Args:
        data: 序列化后的字典
        class_map: 类名到类对象的映射

    Returns:
        反序列化后的对象
    """
    if not class_map:
        # 默认空映射
        class_map = {}

    if isinstance(data, dict) and '_type' in data:
        type_name = data['_type']
        if type_name in class_map:
            cls = class_map[type_name]
            # 创建对象
            instance = cls.__new__(cls)
            # 移除类型信息
            obj_dict = {k: deserialize_object(v, class_map)
                        for k, v in data.items() if k != '_type'}
            # 设置属性
            instance.__dict__.update(obj_dict)
            return instance
        return data  # 未知类型，保持字典形式

    elif isinstance(data, list):
        return [deserialize_object(item, class_map) for item in data]

    elif isinstance(data, dict):
        return {k: deserialize_object(v, class_map) for k, v in data.items()}

    else:
        return data  # 基本类型直接返回