# frame.pyw
import tkinter as tk
import json
import numpy as np
import keyboard
from threading import Thread
from time import sleep
from PIL import ImageGrab
import extract, robot, table
import os

os.system('cls')

CONFIG_FILE = "window_config.json"
config = {'mode':'black8', 'iter':1, 'goal':-1, 'run':False}

# 窗口截图 绘制
def capture_window():
    """截图窗口并保存配置"""
    root = tk.Tk()
    root.attributes("-alpha", 0.3)
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    
    start_pos = None
    
    def on_click(event):
        nonlocal start_pos
        if not start_pos:
            start_pos = (event.x_root, event.y_root)
            label.config(text="请点击窗口右下角")
        else:
            x1, y1 = start_pos
            x2, y2 = event.x_root, event.y_root
            win_cfg = {
                "x": min(x1, x2),
                "y": min(y1, y2),
                "width": abs(x2 - x1),
                "height": abs(y2 - y1)
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(win_cfg, f)
            root.destroy()

    label = tk.Label(root, text="请点击窗口左上角", font=("Arial", 16), 
                    bg="black", fg="white")
    label.place(relx=0.5, rely=0.5, anchor="center")
    root.bind("<Button-1>", on_click)
    root.bind("<Escape>", lambda e: root.destroy())
    root.mainloop()

def show_table_old():
    img = np.array(robot.grab())[:,:,:3]
    tab = extract.extract_table(img, config['mode'])
    if isinstance(tab, str):
        print(tab)
    else:
        tab = table.Table(*tab, config['mode'])
        tab.solve(-1, 2)
        tab.show()

# 重构后的路径显示功能
def show_table():
    global overlay  # 添加全局变量管理窗口
    
    # 销毁旧窗口
    try:
        if overlay.winfo_exists():
            overlay.destroy()
    except:
        pass

    try:
        with open(CONFIG_FILE) as f:
            win_cfg = json.load(f)
    except:
        print("请先按F4截图选择游戏窗口位置")
        return

    try:
        img = np.array(robot.grab())[:, :, :3]
        tab = extract.extract_table(img, config['mode'])
        if isinstance(tab, str): return
        
        # 创建新透明窗口
        overlay = tk.Toplevel()
        overlay.attributes("-topmost", True)
        overlay.overrideredirect(True)
        overlay.geometry(f"{win_cfg['width']}x{win_cfg['height']}+{win_cfg['x']}+{win_cfg['y']}")
        overlay.attributes("-transparentcolor", "white")
        
        canvas = tk.Canvas(overlay, bg='white', highlightthickness=0)
        canvas.pack(fill='both', expand=True)

        # 关闭按钮
        close_btn = tk.Button(overlay, text="X", command=overlay.destroy,
                            bg="red", fg="white", bd=0, font=("Arial", 10))
        close_btn.place(x=win_cfg['width']-30, y=10, width=20, height=20)

        # 处理球桌数据
        tab = table.Table(*tab, config['mode'])
        tab.solve(config['goal'], config['iter']+1)

        # 精确坐标转换（Only 100% DPI）
        for path in tab.paths:
            if path.frm.tp == 0 and hasattr(path, 'get_point'):
                try:
                    # 获取算法原始坐标（基于全屏坐标系）
                    screen_start_x = path.frm.y + tab.loc[1]  # 转换为屏幕x坐标
                    screen_start_y = path.frm.x + tab.loc[0]  # 转换为屏幕y坐标
                    end_point = path.get_point()
                    screen_end_x = end_point[1] + tab.loc[1]
                    screen_end_y = end_point[0] + tab.loc[0]
                    
                    # 转换为用户窗口相对坐标
                    win_x1 = (screen_start_x - win_cfg['x']) / win_cfg['width'] * win_cfg['width']
                    win_y1 = (screen_start_y - win_cfg['y']) / win_cfg['height'] * win_cfg['height']
                    win_x2 = (screen_end_x - win_cfg['x']) / win_cfg['width'] * win_cfg['width']
                    win_y2 = (screen_end_y - win_cfg['y']) / win_cfg['height'] * win_cfg['height']
                    
                    # 调试输出实际屏幕坐标
                    print(f"屏幕实际坐标: ({screen_start_x:.1f},{screen_start_y:.1f}) -> ({screen_end_x:.1f},{screen_end_y:.1f})")
                    print(f"窗口相对坐标: ({win_x1:.1f},{win_y1:.1f}) -> ({win_x2:.1f},{win_y2:.1f})")
                    
                    # 绘制路径
                    canvas.create_line(
                        win_x1, win_y1, 
                        win_x2, win_y2,
                        fill="#00FF00",
                        width=2,
                        arrow=tk.LAST,
                        arrowshape=(12, 15, 6)
                    )
                except Exception as e:
                    print(f"路径绘制异常: {str(e)}")
                    
    except Exception as e:
        print(f"显示错误: {str(e)}")

def set_info(cont):
    top.after(0, lambda: lab.config(text=cont))

def hold():
    while True:
        sleep(0.5)
        if not config['run']:
            set_info('QQ桌球瞄准器')
            continue
        img = np.array(robot.grab())[:,:,:3]
        table_obj, note = robot.analysis(img, config['mode'], config['goal'], config['iter']+1)
        if table_obj is None:
            set_info(note)
            continue
        else:
            set_info(note)
            robot.snap(table_obj, set_info)

def on_stop(): config['run'] = False
def on_start(): config['run'] = True

def on_iter():
    config['iter'] = (config['iter'] + 1)%3
    btn_iter.config(text=f'传击:{config["iter"]+1}次')

def on_mode():
    config['mode'] = 'snooker' if config['mode'] == 'black8' else 'black8'
    btn_mode.config(text=f'模式:{"斯诺克" if config["mode"]=="snooker" else "中式黑八"}')

if __name__ == '__main__':
    top = tk.Tk()
    top.attributes("-topmost", True)
    top.title('QQ桌球瞄准器')

    # Hotkeys
    keyboard.add_hotkey('F3', lambda: top.after(0, show_table))         #绘制
    keyboard.add_hotkey('F4', lambda: top.after(0, overlay.destroy))    #关闭窗口
    keyboard.add_hotkey('F5', lambda: top.after(0, capture_window))     #截图
    keyboard.add_hotkey('F6', lambda: top.after(0, on_start))           #开始

    # 界面布局
    btn_start = tk.Button(top, text="开始", command=on_start)
    btn_stop = tk.Button(top, text="暂停", command=on_stop)
    btn_iter = tk.Button(top, text="传击:2次", command=on_iter)
    btn_mode = tk.Button(top, text="模式:中式黑八", command=on_mode)
    btn_plot = tk.Button(top, text="新绘制", command=show_table)
    btn_plot_old = tk.Button(top, text="绘制", command=show_table_old)
    btn_screenshot = tk.Button(top, text="截图", command=capture_window)

    lab = tk.Label(top, text='桌球瞄准器', bg='white')
    lab.pack(side='bottom', fill='x')
    btn_start.pack(side='left')
    btn_screenshot.pack(side='left')
    btn_stop.pack(side='left')
    btn_plot_old.pack(side='left')
    btn_plot.pack(side='left')
    btn_iter.pack(side='left')
    btn_mode.pack(side='left')

    # 启动守护线程
    Thread(target=hold, daemon=True).start()
    top.mainloop()