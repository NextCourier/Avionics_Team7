##########################################
# 遥控器/代码控制模式切换模块
# 用于切换飞控的控制源（遥控器/代码）
# Author: Custom
##########################################
from pymavlink import mavutil
import threading
import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import time

# 全局控制模式状态
CONTROL_MODE = "remote"  # remote:遥控器控制, code:代码控制
mode_lock = threading.Lock()


class ControlModeController:
    def __init__(self, mav):
        self.mav = mav
        self.current_mode = "remote"  # 初始为遥控器控制

    def switch_control_mode(self, target_mode):
        """
        切换飞控控制模式
        :param target_mode: 目标模式 ("remote" 或 "code")
        :return: 切换是否成功
        """
        if not self.mav:
            raise ValueError("MAVLink连接未初始化")

        if target_mode not in ["remote", "code"]:
            raise ValueError("目标模式必须是 'remote' 或 'code'")

        try:
            with mode_lock:
                if target_mode == "code":
                    # 切换为代码控制：禁用RC输入，启用MAVLink指令控制
                    # 1. 设置飞控模式为MANUAL（确保基础控制）
                    self.mav.mav.set_mode_send(
                        self.mav.target_system,
                        mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
                        0  # ArduCopter MANUAL模式值，PX4可根据实际调整
                    )
                    # 2. 发送参数禁用RC_OVERRIDE，启用MAVLink直接控制
                    self._set_param("RC_OVERRIDE", 0)  # 0=禁用RC覆盖，代码直接控制
                    self.current_mode = "code"
                    print("控制模式已切换为：代码控制")

                else:
                    # 切换为遥控器控制：启用RC输入，禁用代码强制控制
                    self._set_param("RC_OVERRIDE", 1)  # 1=启用RC覆盖，优先遥控器
                    self.current_mode = "remote"
                    print("控制模式已切换为：遥控器控制")

            return True
        except Exception as e:
            print(f"切换控制模式失败: {e}")
            return False

    def _set_param(self, param_name, value):
        """设置飞控参数"""
        self.mav.mav.param_set_send(
            self.mav.target_system,
            self.mav.target_component,
            param_name.encode('utf-8'),
            value,
            mavutil.mavlink.MAV_PARAM_TYPE_REAL32
        )
        # 等待参数设置确认
        time.sleep(0.1)

    def get_current_mode(self):
        """获取当前控制模式"""
        with mode_lock:
            return self.current_mode


def add_control_mode_switch_to_ui(ui_parent, control_mode_controller):
    """
    向UI添加控制模式切换开关
    :param ui_parent: UI父容器（如sidebar_frame）
    :param control_mode_controller: ControlModeController实例
    """
    # 模式状态变量
    mode_var = tk.StringVar(value=f"当前模式：{control_mode_controller.get_current_mode()}")

    # 切换按钮
    def toggle_mode():
        current_mode = control_mode_controller.get_current_mode()
        target_mode = "code" if current_mode == "remote" else "remote"
        success = control_mode_controller.switch_control_mode(target_mode)
        if success:
            mode_var.set(f"当前模式：{target_mode}")
            mode_button.configure(
                text=f"切换为遥控器控制" if target_mode == "code" else f"切换为代码控制"
            )
            messagebox.showinfo("成功", f"已切换为{['代码', '遥控器'][target_mode == 'remote']}控制模式")
        else:
            messagebox.showerror("失败", "模式切换失败，请检查飞控连接")

    # UI组件
    ctk.CTkLabel(
        ui_parent, textvariable=mode_var,
        font=ctk.CTkFont(size=14)
    ).grid(row=4, column=0, padx=20, pady=5)

    mode_button = ctk.CTkButton(
        ui_parent,
        text=f"切换为代码控制" if control_mode_controller.get_current_mode() == "remote" else "切换为遥控器控制",
        command=toggle_mode
    )
    mode_button.grid(row=5, column=0, padx=20, pady=5)

    return mode_var, mode_button


# 单独测试用
if __name__ == "__main__":
    # 初始化MAVLink连接
    mav = mavutil.mavlink_connection('udp:0.0.0.0:14550')
    mav.wait_heartbeat()
    print(f"心跳包接收成功 - 系统ID: {mav.target_system}, 组件ID: {mav.target_component}")

    # 初始化模式控制器
    mode_controller = ControlModeController(mav)

    # 测试切换
    mode_controller.switch_control_mode("code")
    print(f"当前模式: {mode_controller.get_current_mode()}")

    mode_controller.switch_control_mode("remote")
    print(f"当前模式: {mode_controller.get_current_mode()}")