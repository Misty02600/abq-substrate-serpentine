from abaqus import mdb
from abaqusConstants import OFF

def write_all_jobs_to_inp():
    """
    遍历当前MDB中的所有作业，并为每个作业生成INP文件。
    """
    if not mdb.jobs:
        print("警告: MDB中没有找到任何作业，无法生成INP文件。")
        return

    print(f"开始为MDB中的 {len(mdb.jobs)} 个作业生成INP文件...")

    for job_name, job in mdb.jobs.items():
        try:
            print(f"  - 正在为作业 '{job_name}' 生成INP文件...")
            job.writeInput(consistencyChecking=OFF)
            print(f"    - INP文件 '{job_name}.inp' 生成成功。")
        except Exception as e:
            print(f"    - 为作业 '{job_name}' 生成INP文件时出错: {e}")

    print("\n所有作业的INP文件生成完成。")

if __name__ == '__main__':
    write_all_jobs_to_inp()
