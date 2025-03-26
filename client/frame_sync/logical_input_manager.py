# client/frame_sync/logical_input_manager.py

class LogicalInputManager:
    def __init__(self):
        self.client_inputs = {}  # {client_id: 合并后的输入}
        self.default_input = {'movement': 'stop', 'shoot': False}

    def merge_inputs(self, client_id, inputs_list):
        """合并客户端的多个输入"""
        # 如果客户端没有输入列表，不处理
        if not inputs_list or len(inputs_list) == 0:
            print(f"[LogicalInput] No inputs to merge for client {client_id}")
            return

        # 创建默认的空输入
        merged_input = self.default_input.copy()

        # 按照时序逐个应用输入，后面的可能覆盖前面的
        for input_data in inputs_list:
            # 对于移动，直接使用最后一个非stop的指令
            if input_data.get('movement', 'stop') != 'stop':
                merged_input['movement'] = input_data['movement']
                print(f"[LogicalInput] Client {client_id} movement updated to: {merged_input['movement']}")

            # 对于射击，如果任何一个输入包含射击，则最终结果就是射击
            if input_data.get('shoot', False):
                merged_input['shoot'] = True
                print(f"[LogicalInput] Client {client_id} shoot set to: {merged_input['shoot']}")

        # 将合并后的输入保存到客户端输入映射
        self.client_inputs[client_id] = merged_input
        print(f"[LogicalInput] Merged input for client {client_id}: {merged_input}")

    def set_input_frame(self, input_frame_data):
        """设置一个帧的输入数据
        input_frame_data格式: {client_id: [inputs1, inputs2, ...]}
        """
        print(f"[LogicalInput] Setting input frame with {len(input_frame_data)} clients")

        for client_id, inputs_list in input_frame_data.items():
            print(f"[LogicalInput] Processing {len(inputs_list)} inputs for client {client_id}")
            self.merge_inputs(client_id, inputs_list)

    def set_non_input(self):
        """清空input"""
        self.client_inputs = {}

    def get_client_input(self, client_id):
        """获取特定客户端的合并输入"""
        if client_id in self.client_inputs:
            return self.client_inputs[client_id]
        else:
            return self.default_input.copy()  # 返回默认空输入的副本