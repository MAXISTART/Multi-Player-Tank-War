import os


def print_file_contents(file_paths, base_path, output_file):
    """
    打印多个文件的内容，按特定格式展示

    参数:
        file_paths: 包含文件路径的列表
    """
    output = ""

    for path in file_paths:
        try:
            # 读取文件内容
            with open(os.path.join(base_path, path), 'r', encoding='utf-8') as file:
                content = file.read()

            # 按照指定格式添加到输出中
            output += f"文件名: {path}\n"
            output += f"文件内容\n"
            output += f"======================================================================\n"
            output += f"{content}\n\n"

        except FileNotFoundError:
            output += f"文件名: {path}\n"
            output += f"文件内容\n"
            output += f"======================================================================\n"
            output += f"错误: 文件不存在\n\n"

        except Exception as e:
            output += f"文件名: {path}\n"
            output += f"文件内容\n"
            output += f"======================================================================\n"
            output += f"错误: {str(e)}\n\n"

        # 使用UTF-8编码写入文件
        with open(os.path.join(base_path, output_file), 'w', encoding='utf-8') as file:
            file.write(output)


# 程序入口
def main():
    """主函数"""
    base = r"../"
    files = [
                "common/constants.py", "common/deterministic_engine.py", "common/utils.py",
                "client/game_engine/bullet.py", "client/game_engine/collision.py", "client/game_engine/map.py",
                "client/game_engine/obstacle.py", "client/game_engine/particle_system.py", "client/game_engine/tank.py",
                "client/test/test_tank_movement.py", "client/main.py"
            ]
    print_file_contents(files, base, "code_desc.txt")


if __name__ == "__main__":
    main()