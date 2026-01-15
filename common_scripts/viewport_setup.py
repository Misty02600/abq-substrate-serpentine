import inspect
from typing import TYPE_CHECKING

from abaqus import *
from abaqusConstants import *
import sys
from pathlib import Path

if TYPE_CHECKING:
    from abaqus.Model.Model import Model

# 添加父目录到路径
# 脚本所在目录：noGUI 里 __file__ 一定有；Run Script 时看 ② 退路
try:                                    # ① 绝大多数情况下
    SCRIPT_DIR = Path(__file__).parent.resolve()
except NameError:                       # ② 只有 GUI ▸ Run Script 才会进这里
    import os
    fname = inspect.getfile(inspect.currentframe())
    SCRIPT_DIR = Path(fname).parent.resolve() if not fname.startswith('<')\
                 else Path(os.getcwd()).resolve()

# 将父目录添加到Python路径
PARENT_DIR = SCRIPT_DIR.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

from src.utils.abaqus_utils import current_display_info


def disable_all_viewport_annotations():
    """
    关闭当前视口的所有注释和图例（自动获取当前视口）
    """
    # 设置背景为白色
    session.graphicsOptions.setValues(backgroundStyle=SOLID,
        backgroundColor='#FFFFFF')

    # 获取当前视口
    vp = session.viewports[session.currentViewportName]
    # 关闭所有视口注释选项和图例框
    vp.viewportAnnotationOptions.setValues(
        triad=OFF,
        legend=OFF,
        title=OFF,
        state=OFF,
        annotations=OFF,
        compass=OFF,
        legendBox=OFF
    )

    print("已关闭当前视口的所有注释和图例显示")


def enable_shell_thickness_rendering():
    """
    设置当前视口显示壳单元厚度渲染
    """
    # 获取当前视口
    vp = session.viewports[session.currentViewportName]
    vp.assemblyDisplay.setValues(renderShellThickness=ON)


def set_parts_geometry_refinement(model_name=None, refinement_level=EXTRA_FINE):
    """
    将指定模型或当前模型中的所有部件设置为指定的几何细化级别

    Args:
        model_name (str, optional): 模型名称，如果为None则自动检测当前模型
        refinement_level: 几何细化级别，可选值：
            - COARSE: 粗糙
            - MEDIUM: 中等
            - FINE: 精细
            - EXTRA_FINE: 超精细（默认）
    """
    # 如果没有指定模型名称，自动检测当前模型
    if model_name is None:
        # 优先从当前显示的对象获取模型名
        display_info = current_display_info()
        current_model_name = display_info.get('model_name')

        # 如果当前显示的不是模型对象或未获取到模型名，使用默认逻辑
        if not current_model_name:
            if len(mdb.models) == 1:
                current_model_name = list(mdb.models.keys())[0]
            else:
                # 优先选择非默认模型
                for name in mdb.models.keys():
                    if name != 'Model-1':
                        current_model_name = name
                        break
                else:
                    current_model_name = list(mdb.models.keys())[0]

        model_name = current_model_name

    if model_name not in mdb.models:
        available_models = list(mdb.models.keys())
        print(f"可用模型: {available_models}")
        return

    model = mdb.models[model_name]
    parts = model.parts

    if not parts:
        print(f"模型 '{model_name}' 中没有部件")
        return

    print(f"正在设置模型 '{model_name}' 中的 {len(parts)} 个部件...")

    for part in parts.values():
        part.setValues(geometryRefinement=refinement_level)


    # 刷新视图
    try:
        vp = session.viewports[session.currentViewportName]
        vp.view.fitView()
    except:
        pass


if __name__ == "__main__":
    # 关闭所有视口注释
    disable_all_viewport_annotations()

    # 启用壳单元厚度渲染
    # enable_shell_thickness_rendering()

    # 设置部件几何细化
    # set_parts_geometry_refinement(refinement_level=EXTRA_FINE)