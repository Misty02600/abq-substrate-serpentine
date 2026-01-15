from abaqus import mdb
from abaqusConstants import *
import traceback


def submit_jobs_batch(batch_size: int = 1,
                      save_after_batch: bool = False) -> None:
    """Submit all jobs in the current MDB in batches.

    Args:
        batch_size (int, optional): 每批次提交的作业数量，默认为 3。
        save_after_batch (bool, optional): 若为 True，并且当前脚本
            运行于 CAE GUI 内，则每个批次完成后自动保存
            当前 .cae 文件。默认为 False.
    """
    job_names = list(mdb.jobs.keys())

    if not job_names:
        print("未检测到任何 Job，脚本结束。")
        return

    # 筛选出需要提交的作业（排除已完成的）
    pending_jobs = []
    for jname in job_names:
        job = mdb.jobs[jname]
        if job.status in (COMPLETED, TERMINATED, ABORTED):
            print(f"跳过已结束的作业: {jname}  (status = {job.status})")
        else:
            pending_jobs.append(jname)

    if not pending_jobs:
        print("所有作业都已完成，无需提交。")
        return

    total_jobs = len(pending_jobs)
    print(f"发现 {total_jobs} 个待提交作业，将以每批 {batch_size} 个的方式提交")

    # 分批处理作业
    for batch_idx in range(0, total_jobs, batch_size):
        batch_jobs = pending_jobs[batch_idx:batch_idx + batch_size]
        batch_num = batch_idx // batch_size + 1
        total_batches = (total_jobs + batch_size - 1) // batch_size

        print(f"\n开始处理第 {batch_num}/{total_batches} 批次")
        print(f"本批次作业: {', '.join(batch_jobs)}")

        # 提交本批次的所有作业
        submitted_jobs = []
        for jname in batch_jobs:
            job = mdb.jobs[jname]
            print(f"正在提交: {jname}")
            job.submit()
            submitted_jobs.append(jname)
            print(f"{jname} 提交成功")

        # 等待本批次所有作业完成
        print(f"\n等待本批次 {len(submitted_jobs)} 个作业完成...")
        for jname in submitted_jobs:
            job = mdb.jobs[jname]
            print(f"等待 {jname} 计算完成...")
            job.waitForCompletion()
            print(f"{jname} 计算完成，状态: {job.status}")

        print(f"第 {batch_num} 批次全部完成")

        if save_after_batch:
            # 仅在 GUI 会话中 save() 可用
            mdb.save()
            print("会话已保存。")

    print(f"\n=== 所有批次处理完成 ===")


if __name__ == "__main__":
    submit_jobs_batch(batch_size=4, save_after_batch=False)