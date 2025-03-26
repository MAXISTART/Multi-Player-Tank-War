# run_multiple_terminals.py
import os
import subprocess
from pathlib import Path


def run_game_batch():

    # 批处理文件路径
    bat_file_path = Path("../bats") / "run_game.bat"

    # 检查批处理文件是否存在
    if not bat_file_path.exists():
        print(f"错误: 批处理文件不存在: {bat_file_path}")
        return

    try:
        # 执行批处理文件
        print(f"正在执行批处理文件: {bat_file_path}")
        subprocess.call(str(bat_file_path), shell=True)
        print("批处理文件执行完成")

    except Exception as e:
        print(f"执行过程中出错: {e}")


if __name__ == "__main__":
    print("启动坦克大战游戏...")
    run_game_batch()