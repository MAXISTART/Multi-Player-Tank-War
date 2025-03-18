# frame_data.py
"""
帧数据模块：定义帧同步中使用的数据结构
"""


class InputData:
    """
    输入数据：玩家在一帧中的输入

    包含：
    - 移动指令
    - 射击指令
    - 特殊动作
    """

    def __init__(self, movement=None, shooting=False, special=None):
        """初始化输入数据"""
        pass

    def serialize(self):
        """序列化为紧凑格式"""
        pass

    @classmethod
    def deserialize(cls, data):
        """从序列化数据恢复"""
        pass

    def is_empty(self):
        """检查是否为空输入"""
        pass

    def merge(self, other_input):
        """合并其他输入数据"""
        pass


class FrameData:
    """
    帧数据：一帧中的所有玩家输入和游戏事件

    包含：
    - 帧编号
    - 所有玩家的输入
    - 帧内事件
    """

    def __init__(self, frame_number, inputs=None, events=None):
        """初始化帧数据"""
        pass

    def add_input(self, player_id, input_data):
        """添加玩家输入"""
        pass

    def get_input(self, player_id):
        """获取指定玩家的输入"""
        pass

    def add_event(self, event):
        """添加事件"""
        pass

    def serialize(self):
        """序列化为网络传输格式"""
        pass

    @classmethod
    def deserialize(cls, data):
        """从序列化数据恢复"""
        pass

    def is_complete(self, expected_players):
        """检查是否包含所有预期玩家的输入"""
        pass

    def get_missing_players(self, expected_players):
        """获取缺少输入的玩家列表"""
        pass


class ChecksumData:
    """
    校验和数据：存储和比较游戏状态校验和

    包含：
    - 帧编号
    - 校验和值
    - 玩家ID
    """

    def __init__(self, frame_number, checksum, player_id):
        """初始化校验和数据"""
        pass

    def serialize(self):
        """序列化为网络传输格式"""
        pass

    @classmethod
    def deserialize(cls, data):
        """从序列化数据恢复"""
        pass

    def equals(self, other_checksum):
        """比较两个校验和是否相等"""
        pass


# 单元测试
def test_frame_data():
    """帧数据模块的单元测试"""
    pass


if __name__ == "__main__":
    test_frame_data()