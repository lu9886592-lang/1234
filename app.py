import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="高压全自动物理仿真", layout="wide")
st.title("⚡ 高压冲击系统：全自动物理参数建模仿真")

# --- 2. 侧边栏：电压等级与结构选择 ---
st.sidebar.header("🔌 1. 电压等级预设")
kv_level = st.sidebar.selectbox("选择分压器电压等级 (kV)", [200, 400, 800, 1200, 2400], index=3)

# 根据电压等级预设初始物理尺寸 (典型值)
if kv_level == 200: h_init, d_init, r1_init = 1.20, 0.40, 2000.00
elif kv_level == 400: h_init, d_init, r1_init = 2.50, 0.60, 4000.00
elif kv_level == 800: h_init, d_init, r1_init = 4.50, 0.90, 8000.00
elif kv_level == 1200: h_init, d_init, r1_init = 6.50, 1.25, 10000.00
else: h_init, d_init, r1_init = 12.00, 2.20, 20000.00

st.sidebar.divider()
st.sidebar.header("📏 2. 物理几何尺寸")
# 使用精确到小数点后两位的数字输入框
h_total = st.sidebar.number_input("分压器总高度 H (m)", value=h_init, step=0.01, format="%.2f")
d_ring = st.sidebar.number_input("均压环/主体直径 D (m)", value=d_init, step=0.01, format="%.2f")
l_wire = st.sidebar.number_input("高压引线水平长度 Lw (m)", value=5.00, step=0.01, format="%.2f")

st.sidebar.header("🔌 3. 电路核心参数")
r1 = st.sidebar.number_input("高压臂电阻 R1 (Ω)", value=r1_init, step=0.01, format="%.2f")
r2 = st.sidebar.number_input("低压臂电阻 R2 (Ω)", value=10.00, step=0.01, format="%.2f")
r_damp = st.sidebar.number_input("引线串联阻尼电阻 (Ω)", value=150.00, step=0.10, format="%.2f")

st.sidebar.header("📡 4. 测量链配置")
cable_l = st.sidebar.number_input("电缆长度 (m)", value=20.00, step=0.10, format="%.2f")
rs = st.sidebar.number_input("首端匹配电阻 Rs (Ω)", value=50.00, step=0.01, format="%.2f")
z0 = st.sidebar.number_input("电缆特性阻抗 Z0 (Ω)", value=50.00, step=0.01, format="%.2f")
rt = st.sidebar.selectbox("示波器输入阻抗 (Ω)", [1000000.0, 50.0], index=1)

# --- 3. 自动化物理建模计算 ---
def run_auto_physics_sim():
    # A. 寄生电容 Cg 计算 (基于电容分压器对地耦合模型)
    eps0 = 8.854187e-12
    # 修正公式：主要受高度和等效直径影响
    cg_pf = (2 * np.pi * eps0 * h_total) / (np.log(4 * h_total / d_ring) - 1) * 1e12 * 1.15
    
    # B. 回路电感 L 计算 (引线 + 分压器本体)
    # 基于回路面积的电感估算公式：L = 0.2 * L_total * (ln(2*L_total/r) - 0.75)
    mu0 = 4 * np.pi * 1e-7
    total_path = l_wire + h_total # 总电流路径
    eff_radius = d_ring / 2
    l_loop_uh = 0.2 * total_path * (np.log(2 * total_path / eff_radius) - 0.75)
    
    # C. 系统阻尼汇总 (修复之前的 NameError)
    # 总阻尼 = 引线阻尼 + 首端匹配 + (如果示波器是50欧，则电缆末端也贡献阻尼)
    r_total_val = r_damp + rs + (z0 if rt == 50.0 else 0)
    
    # D. 建立二阶动态系统
    L_val = l_loop_uh * 1e-6
    C_val = cg_pf * 1e-12
    
    # 传递函数
    sys = signal.TransferFunction([1], [L_val * C_val, r_total_val * C_total, 1])
    t = np.linspace(0, 5e-6, 5000)
    t, y = signal.step(sys, T=t)
    
    # E. 实际测量变比 K (考虑负载效应)
    r2_eff = (r2 * rt) / (r2 + rt)
    k_actual = (r1 + r2_eff) / r2_eff
    
    return t, y, cg_pf, l_loop_uh, k_actual

# 执行仿真
t_v, y_v, cg_res, l_res, k_res = run_auto_physics_sim()

# --- 4. 实时仪表盘展示 ---
c1, c2, c3, c4 = st.columns(4)
try:
    idx10 = np.where(y_v >= 0.1)[0][0]
    idx90 = np.where(y_v >= 0.9)[0][0]
    tr_ns = (t_v[idx90] - t_v[idx10]) * 1e9
    c1.metric("上升时间 Tr", f"{tr_ns:.2f} ns")
except:
    c1.metric("上升时间 Tr", "N/A")

c2.metric("自动估算 Cg", f"{cg_res:.2f} pF")
c3.metric("回路电感 L", f"{l_res:.2f} μH")
c4.metric("实测变比 K", f"{k_res:.2f}")

# --- 5. 波形展示 ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_v*1e6, y=y_v, name='测量端响应', line=dict(color='#00FFCC', width=2.5)))
fig.add_hline(y=1.0, line_dash="dash", line_color="white", opacity=0.3)
fig.update_layout(
    xaxis_title="时间 (μs)", 
    yaxis_title="归一化电压 (pu)", 
    template="plotly_dark", 
    height=600,
    margin=dict(l=20, r=20, t=40, b=20)
)
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 物理建模逻辑：当前回路电感是基于 {l_wire:.2f}m 引线和 {h_total:.2f}m 设备高度共同产生的磁场面积计算得出。")
