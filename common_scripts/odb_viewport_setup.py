import inspect
from abaqus import *
from abaqusConstants import *

from abq_serp_sub.utils.abaqus_utils import current_display_info


def set_visible_edges_free():
    """
    设置当前视口的ODB显示模式为仅显示自由边

    自由边(FREE)是指不与其他单元共享的边，通常用于显示：
    - 模型的外表面边界
    - 裂纹、孔洞等不连续区域
    - 壳单元的自由边缘

    这个设置可以帮助更清晰地查看模型的外部轮廓和特征边界
    """
    # 获取当前视口
    vp = session.viewports[session.currentViewportName]

    # 检查当前是否显示ODB
    try:
        vp.odbDisplay.commonOptions.setValues(visibleEdges=FREE)
        print(f"已将视口 '{session.currentViewportName}' 的可见边设置为 FREE（仅自由边）")
    except AttributeError:
        print("错误: 当前视口未显示ODB文件，请先打开ODB文件")
    except Exception as e:
        print(f"设置失败: {e}")


if __name__ == "__main__":
    # 执行ODB视口设置
    set_visible_edges_free()
