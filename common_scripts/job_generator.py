from typing import TYPE_CHECKING

from abaqus import mdb
from abaqusConstants import *

if TYPE_CHECKING:
    from abaqus.Model.Model import Model


def create_jobs_for_all_models(num_cpus=4, memory_percentage=90, enable_restart=False):
    """
    为当前MDB中的所有模型创建作业

    Args:
        num_cpus (int): CPU核心数，默认为4，用于numCpus和numDomains
        memory_percentage (int): 内存使用百分比，默认为90
        enable_restart (bool): 是否启用重启动功能，默认为False

    Returns:
        dict: 创建结果统计
    """

    # 获取所有模型名称（排除默认的Model-1）
    all_models = [name for name in mdb.models.keys() if name != 'Model-1']

    if not all_models:
        print("未找到任何模型（除默认Model-1外），脚本结束。")
        return {'created': 0, 'existing': 0, 'failed': 0}

    created_count = 0
    existing_count = 0
    failed_count = 0

    for model_name in all_models:
        try:
            # 检查作业是否已存在
            if model_name in mdb.jobs:
                print(f"作业 {model_name} 已存在，跳过创建")
                existing_count += 1
                continue

            # 检查模型是否存在
            if model_name not in mdb.models:
                print(f"警告: 模型 {model_name} 不存在，跳过作业创建")
                failed_count += 1
                continue

            # 创建作业
            print(f"正在为模型 {model_name} 创建作业...")

            job = mdb.Job(
                name=model_name,
                model=model_name,
                description=f'Analysis job for model {model_name}',
                type=ANALYSIS,
                atTime=None,
                waitMinutes=0,
                waitHours=0,
                queue=None,
                memory=memory_percentage,
                memoryUnits=PERCENTAGE,
                getMemoryFromAnalysis=True,
                explicitPrecision=SINGLE,
                nodalOutputPrecision=SINGLE,
                echoPrint=OFF,
                modelPrint=OFF,
                contactPrint=OFF,
                historyPrint=OFF,
                userSubroutine='',
                scratch='',
                resultsFormat=ODB,
                numThreadsPerMpiProcess=1,
                multiprocessingMode=DEFAULT,
                numCpus=num_cpus,
                numDomains=num_cpus,
                numGPUs=0
            )

            # 如果启用重启动功能，需要检查模型中是否设置了重启动
            if enable_restart:
                model = mdb.models[model_name]
                # 检查步骤中是否有重启动设置
                for step_name, step in model.steps.items():
                    if step_name != 'Initial' and hasattr(step, 'restart'):
                        print(f"模型 {model_name} 的步骤 {step_name} 已配置重启动")

            print(f"作业 {model_name} 创建成功")
            created_count += 1

        except Exception as e:
            print(f"创建作业 {model_name} 时出错: {str(e)}")
            failed_count += 1

    # 打印结果统计
    print(f"\n=== 作业创建完成 ===")
    print(f"总模型数: {len(all_models)}")
    print(f"新创建作业: {created_count}")
    print(f"已存在作业: {existing_count}")


if __name__ == "__main__":
    # 示例用法

    print("为所有模型创建作业")
    result = create_jobs_for_all_models(num_cpus=13, memory_percentage=90, enable_restart=False)