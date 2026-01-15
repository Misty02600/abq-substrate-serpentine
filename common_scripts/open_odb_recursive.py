from pathlib import Path
import tkinter as tk
from tkinter import filedialog

from abaqus import session
from abaqusConstants import *

def open_odbs_from_folder_recursively():
    """
    弹出多个文件夹选择对话框，然后递归地打开这些文件夹及其所有子文件夹下的全部ODB文件。
    """
    selected_folders = []

    print("请选择要搜索ODB文件的文件夹（可以选择多个）")
    print("选择完一个文件夹后，会询问是否继续选择下一个")

    while True:
        # 1. 创建一个隐藏的Tkinter根窗口
        try:
            root = tk.Tk()
            root.withdraw()

            # 2. 弹出文件夹选择对话框
            if not selected_folders:
                title = "请选择第1个要搜索ODB文件的文件夹"
            else:
                title = f"请选择第{len(selected_folders)+1}个文件夹（已选择{len(selected_folders)}个）"

            target_folder = filedialog.askdirectory(title=title)
        finally:
            # 确保Tkinter窗口被销毁
            if 'root' in locals() and root:
                root.destroy()

        # 3. 检查用户是否选择了文件夹
        if not target_folder:
            if not selected_folders:
                print("未选择任何文件夹，操作已取消。")
                return
            else:
                print("结束文件夹选择。")
                break

        # 避免重复添加同一个文件夹
        if target_folder not in selected_folders:
            selected_folders.append(target_folder)
            print(f"已添加文件夹: {target_folder}")
        else:
            print(f"文件夹已存在，跳过: {target_folder}")

        # 4. 询问是否继续选择
        try:
            root = tk.Tk()
            root.withdraw()

            import tkinter.messagebox as msgbox
            continue_selection = msgbox.askyesno(
                "继续选择",
                f"已选择 {len(selected_folders)} 个文件夹。\n是否继续选择更多文件夹？"
            )
        finally:
            if 'root' in locals() and root:
                root.destroy()

        if not continue_selection:
            break

    if not selected_folders:
        print("未选择任何文件夹，操作已取消。")
        return

    print(f"\n开始在 {len(selected_folders)} 个文件夹中递归搜索 .odb 文件...")
    for i, folder in enumerate(selected_folders, 1):
        print(f"  {i}. {folder}")

    # 5. 使用 pathlib.Path.rglob 进行递归搜索所有选中的文件夹
    all_odb_files = []
    for folder in selected_folders:
        root_path = Path(folder)
        odb_files_generator = root_path.rglob('*.odb')
        folder_odb_files = list(odb_files_generator)

        print(f"\n在文件夹 '{folder}' 中找到 {len(folder_odb_files)} 个 .odb 文件")
        all_odb_files.extend(folder_odb_files)

    if not all_odb_files:
        print(f"在所有指定路径下未找到任何 .odb 文件。")
        return

    total_files = len(all_odb_files)
    print(f"\n总共找到 {total_files} 个 .odb 文件，即将开始在Abaqus中打开...")

    # 6. 遍历找到的文件列表，并在Abaqus中打开
    opened_count = 0
    for i, file_path in enumerate(all_odb_files, 1):
        print(f"[{i}/{total_files}] 正在尝试打开: {file_path}")

        session.openOdb(name=str(file_path))
        print(f"  -> 成功打开: {file_path.name}")
        opened_count += 1

    print(f"\n处理完成。共成功打开 {opened_count}/{total_files} 个ODB文件。")


if __name__ == '__main__':
    open_odbs_from_folder_recursively()