# ============================================================================ #
#                         孔隙生成函数                                          #
# ============================================================================ #
"""
孔隙（圆孔）生成相关的纯计算函数，包括：
  - calculate_circle_radius: 根据孔隙率计算圆孔半径
  - generate_circles_grid_standard: 生成标准排列的圆孔网格
  - generate_circles_grid: 生成带随机偏差的圆孔网格
"""
import numpy as np


def generate_uniform_in_disk(radius):
    """
    生成在半径为radius的圆盘内均匀分布的随机点
    使用极坐标采样方法确保均匀分布
    返回: (x, y) 坐标
    """
    # 生成随机角度
    theta = np.random.uniform(0, 2*np.pi)
    # 生成随机半径（需要开根号以确保均匀分布）
    u = np.random.uniform(0, 1)
    r = radius * np.sqrt(u)

    # 转换为笛卡尔坐标
    x = r * np.cos(theta)
    y = r * np.sin(theta)

    return (x, y)


def generate_random_center(T_xi):
    """
    生成圆心的无量纲坐标偏差，服从圆盘内均匀分布
    - T_xi: 坐标偏差的截断上下限（圆形区域的半径）
    - 返回一个随机生成的无量纲坐标偏差 (xi, eta)
    """
    return generate_uniform_in_disk(T_xi)


def generate_random_diameter_deviation(T_delta):
    """
    生成直径的无量纲偏差，服从[-T_delta, T_delta]范围内的均匀分布
    - T_delta: 直径偏差的截断上下限
    - 返回一个随机生成的无量纲直径偏差 delta
    """
    delta = np.random.uniform(-T_delta, T_delta)
    return delta


def calculate_circle_radius(square_side, porosity):
    """
    根据正方形边长和孔隙率计算圆孔的半径。
    返回r: 计算得到的圆孔半径
    """
    if porosity < 0 or porosity > 0.7854:
        raise ValueError("porosity 应该在0和0.7854之间")
    area_square = square_side ** 2
    area_circle = porosity * area_square
    r = np.sqrt(area_circle / np.pi)
    return r


def generate_circles_grid_standard(n_rows, n_cols, square_side, radius):
    """
    生成标准排列（居中）的圆孔网格。

    每个圆孔位于正方形单元的中心，半径相同。

    Args:
        n_rows: 网格行数
        n_cols: 网格列数
        square_side: 正方形单元边长
        radius: 圆孔半径

    Returns:
        np.ndarray: 形状为 (n_rows, n_cols, 3) 的数组，每个元素为 [x, y, r]
    """
    circles = np.empty((n_rows, n_cols, 3))

    for i in range(n_rows):
        for j in range(n_cols):
            center_x = (j + 0.5) * square_side
            center_y = (i + 0.5) * square_side
            circles[i, j, :] = [center_x, center_y, radius]

    return circles


def generate_circles_grid(n_rows, n_cols, square_side, radius_nom, T_xi, T_delta):
    """
    生成网格中所有圆孔的坐标和半径
    - n_rows, n_cols: 网格行数和列数
    - square_side: 正方形单元边长 l
    - radius_nom: 名义圆孔半径
    - T_xi: 坐标偏差的截断上下限（圆形区域的半径）
    - T_delta: 直径偏差的截断上下限
    """
    # 使用传入的名义半径计算直径
    r_nom = radius_nom
    d_nom = 2 * r_nom

    circles = np.empty((n_rows, n_cols, 3))

    for i in range(n_rows):
        for j in range(n_cols):
            # 1. 生成无量纲随机偏差
            xi, eta = generate_random_center(T_xi)
            delta = generate_random_diameter_deviation(T_delta)

            # 2. 简化边界检查（在无量纲空间中进行）
            dimensionless_radius = r_nom / square_side + delta / 2
            if (abs(xi) + dimensionless_radius > 0.5 or
                abs(eta) + dimensionless_radius > 0.5):
                raise ValueError(f"Square ({i}, {j}) 中的圆超出正方形边界。无量纲参数: xi={xi:.3f}, eta={eta:.3f}, r'={dimensionless_radius:.3f}")

            # 3. 计算实际坐标和半径
            # 计算当前正方形中心坐标（名义位置）
            square_center_x = j * square_side + square_side/2
            square_center_y = i * square_side + square_side/2

            # 计算实际坐标偏差 (Δx, Δy)
            delta_x = xi * square_side
            delta_y = eta * square_side

            # 计算实际圆心坐标
            circle_center_x = square_center_x + delta_x
            circle_center_y = square_center_y + delta_y

            # 计算实际直径偏差 Δd
            delta_d = delta * square_side

            # 计算实际圆孔直径和半径
            actual_diameter = d_nom + delta_d
            circle_radius = actual_diameter / 2

            circles[i, j, :] = [circle_center_x, circle_center_y, circle_radius]

    return circles
