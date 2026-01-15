"""
ABAQUS后处理脚本 - 导线应变云图显示
整理自原始宏文件，提供导线应变可视化功能
"""

import displayGroupOdbToolset as dgo
from abaqus import *
from abaqusConstants import *


def display_wire_strain_contours(ply_location, max_strain=0.003):
    """
    显示导线部件的应变云图（原Macro1功能），自动获取当前视口

    Parameters
    ----------
    max_strain : float, optional
        应变云图的最大值，默认为0.003
    ply_location : str, optional
        层结果位置，可选值：'BOTTOM', 'MIDDLE', 'TOP', 'TOP_AND_BOTTOM'
        默认为'TOP_AND_BOTTOM'
    """
    # 选择导线部件实例
    leaf = dgo.LeafFromPartInstance(partInstanceName=("WIRE-1", ))
    vp_name = session.currentViewportName
    vp = session.viewports[vp_name]
    vp.odbDisplay.displayGroup.replace(leaf=leaf)

    vp = session.viewports[session.currentViewportName]
    # 设置显示为未变形轮廓
    vp.odbDisplay.display.setValues(plotState=(CONTOURS_ON_UNDEF, ))

    # 设置主变量为对数应变的最大主应变
    vp.odbDisplay.setPrimaryVariable(
        variableLabel='LE',
        outputPosition=INTEGRATION_POINT,
        refinement=(INVARIANT, 'Max. Principal')
    )

    # 设置截面点
    vp.odbDisplay.setPrimarySectionPoint(activePly="CU")

    # 根据参数设置层结果位置
    ply_location_map = {
        'BOTTOM': BOTTOM,
        'MIDDLE': MIDDLE,
        'TOP': TOP,
        'TOP_AND_BOTTOM': TOP_AND_BOTTOM
    }

    ply_result_location = ply_location_map[ply_location]

    # 设置基于层的截面点方案
    vp.odbDisplay.basicOptions.setValues(
        sectionPointScheme=PLY_BASED,
        plyResultLocation=ply_result_location,
        averagingThreshold=100
    )

    vp.odbDisplay.contourOptions.setValues(
        maxAutoCompute=OFF,
        maxValue=max_strain,
        minValue=0,
        outsideLimitsMode=SPECTRUM
    )

    # 设置视图为前视图
    vp.view.setValues(session.views['Front'])


if __name__ == "__main__":
    # 如果直接运行此脚本，显示导线应变云图
    display_wire_strain_contours(ply_location='BOTTOM')
