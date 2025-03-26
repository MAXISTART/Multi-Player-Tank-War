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
            error = ""
            error += f"文件名: {path}\n"
            error += f"文件内容\n"
            error += f"======================================================================\n"
            error += f"错误: 文件不存在\n\n"
            print(error)

        except Exception as e:
            error = ""
            error += f"文件名: {path}\n"
            error += f"文件内容\n"
            error += f"======================================================================\n"
            error += f"错误: {str(e)}\n\n"
            print(error)

        # 使用UTF-8编码写入文件
        with open(os.path.join(base_path, output_file), 'w', encoding='utf-8') as file:
            file.write(output)


def collect_all_pyfile():
    ret = []
    # 自底向上遍历目录(这样可以先处理子目录)
    for root, dirs, files in os.walk("../", topdown=False):
        # 跳过.git文件夹及其子文件夹
        if '.git' in root.split(os.sep):
            continue

        if "build_utils" in root or "test_utils" in root:
            # 跳过 build_utils 文件夹
            continue

        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                res = file_path.replace("../", "").replace("\\", "/")
                print(res)
                ret.append(res)
    return ret

# 程序入口
def main():
    """主函数"""
    files = collect_all_pyfile()
    base = r"../"
    print_file_contents(files, base, "code_desc.txt")


if __name__ == "__main__":
    main()