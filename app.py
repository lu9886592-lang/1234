import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="高压精密仿真", layout="wide")
st.title("⚡ 高压冲击测量系统：精密数值仿真 (1200kV 级)")

# --- 2. 侧边栏：精密参数录入 ---
st.sidebar.header("📏 1. 分压器主体参数")
r_high = st.sidebar.number_input("高压臂电阻 R1 (Ω)", value=10000.00, step=0.01, format="%.2f")
r_low = st.sidebar.number_input("低压臂电阻 R2 (Ω)", value=10.55, step=0.01, format="%.2f")
h_main = st.sidebar.number_input("分压器高度 H (m)", value=6.50, step=0.01, format="%.2f")
d_ring = st.sidebar.number_input("均压环直径 D (m)", value=1.25, step=0.01, format="%.2f")

st.sidebar.divider()
st.sidebar.header("🔌 2. 测量电缆与匹配 (精确匹配)")
cable_len = st.sidebar.number_input("测量电缆长度 (m)", value=25.00, step=0.10, format="%.2f")
z0_cable = st.sidebar.number_input("电缆特性阻抗 Z0 (Ω)", value=50.00, step=0.01, format="%.2f")
r_match_s = st.sidebar.number_input("首端匹配电阻 Rs (Ω)", value=50.00, step=0.01, format="%.2f")
r_scope = st.sidebar.selectbox("示波器输入阻抗 (Ω)", [1000000.00, 50.00], index=1)

st.sidebar.divider()
st.sidebar.header("➰ 3. 寄生参数与回路阻尼")
l_loop = st.sidebar.number_input("回路引线电感 L (μH)", value=4.85, step=0.01, format="%.2f")
r_damp_ext = st.sidebar.number_input("高压线串联阻尼 (Ω)", value=120.00, step=0.10, format="%.2f")
r_ferrite_eff = st.sidebar.number_input("磁珠等效电阻 (Ω)", value=85.50, step=0.01, format="%.2f")

# --- 3. 核心物理计算 ---
def run_precision_sim():
    # 1. 结构电容 Cg 精密计算
    eps0 = 8.854187e-12
    # 考虑邻近效应系数 1.15
    cg_pf = (2 * np.pi * eps0 * h_main) / (np.log(4 * h_main / d_ring) - 1) * 1e12 * 1.15
    
    # 2. 传输线延时 (单位: 秒)
    # 典型同轴电缆传播速度为 0.7c
    v_p = 3e8 * 0.7
    t_delay = cable_len / v_p
    
    # 3. 建立二阶等效电路模型
    L_total = l_loop * 1e-6
    C_total = cg_pf * 1e-12
    # 串联总阻尼：高压线阻尼 + 磁珠 + 首端匹配
    # 注意：如果示波器是50欧，它在电缆末端吸收能量
    r_total_ser = r_damp_ext + r_ferrite_eff + r_match_s
    
    # 传递函数：V_out / V_in
    sys = signal.TransferFunction([1], [L_total * C_total, r_total_ser * C_total, 1])
    t = np.linspace(0, 5e-6, 5000)
    t, y = signal.step(sys, T=t)
    
    # 4. 模拟不匹配导致的反射 (多次反射叠加)
    rho_s = (r_match_s - z0_cable) / (r_match_s + z0_cable)
    rho_r = (r_scope - z0_cable) / (r_scope + z0_cable)
    
    # 反射修正逻辑
    reflection_mask = t > 2 * t_delay
    if np.any(reflection_mask) and abs(rho_s * rho_r) > 0.001:
        y[reflection_mask] += (rho_s * rho_r) * 0.15 * np.sin(2 * np.pi * (1/(2*t_delay)) * t[reflection_mask])

    # 5. 计算分压比 (考虑示波器负载效应)
    r2_parallel = (r_low * r_scope) / (r_low + r_scope)
    ratio_real = (r_high + r2_parallel) / r2_parallel
    
    return t, y, cg_pf, ratio_real

t_vec, y_vec, cg_val, final_ratio = run_precision_sim()

# --- 4. 仪表盘展示 ---
c1, c2, c3 = st.columns(3)
try:
    idx10 = np.where(y_vec >= 0.1)[0][0]
    idx90 = np.where(y_vec >= 0.9)[0][0]
    tr_ns = (t_vec[idx90] - t_vec[idx10]) * 1e9
    c1.metric("上升时间 Tr (10%-90%)", f"{tr_ns:.2f} ns")
except:
    c1.metric("上升时间 Tr", "无法锁定波头")

c2.metric("实际测量变比 (K)", f"{final_ratio:.2f}")
c3.metric("计算对地电容 (Cg)", f"{cg_val:.2f} pF")

# --- 5. 交互式波形图 ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_vec*1e6, y=y_vec, name='测量端波形', line=dict(color='#1E90FF', width=2.5)))
fig.add_hline(y=1.0, line_dash="dash", line_color="#FF4500", annotation_text="理想阶跃")
fig.update_layout(
    xaxis_title="时间 (μs)",
    yaxis_title="归一化电压 (pu)",
    hovermode="x unified",
    template="plotly_white",
    height=600
)
st.plotly_chart(fig, use_container_width=True)

st.success(f"🔍 物理校验：当前电缆往返延时为 { (cable_len/(3e8*0.7)*2e9):.2f} ns。若 Rs={r_match_s}Ω 与 Z0={z0_cable}Ω 不等，波形将在此周期产生畸变。")
