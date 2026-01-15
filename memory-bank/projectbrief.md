# Project Brief

## Project Name
ABAQUS Serpentine Interface Simulation Scripts

## Overview
本项目是一套用于 ABAQUS 有限元分析软件的 Python 脚本，用于自动化创建和分析蛇形导线与基底界面的力学行为模型。

## Core Requirements

### 功能需求
1. **模型生成**：自动创建蛇形导线（PI-Cu-PI 三层结构）和基底（实心或多孔）的 3D 有限元模型
2. **参数化建模**：支持通过配置文件批量生成不同参数组合的模型
3. **网格划分**：自动进行网格划分和布种控制
4. **边界条件**：设置加载条件、约束和接触属性
5. **后处理**：从 ODB 结果文件中提取变形数据和可拉伸性分析

### 技术要求
- 兼容 ABAQUS Python 环境（基于 Python 2.7/3.x）
- 支持 GUI 和 noGUI 模式运行
- 支持批量作业提交和管理

## Goals
- 提高蛇形导线力学仿真的建模效率
- 实现参数化扫描分析
- 自动化后处理数据提取

## Scope
- ABAQUS 模型创建脚本
- 配置文件解析和处理
- ODB 后处理脚本
- INP 文件生成和修改

## Success Criteria
- 能够根据配置文件自动生成完整的 ABAQUS 模型
- 支持多孔和实心基底两种类型
- 能够批量提取仿真结果数据
