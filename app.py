import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="1200kV精密全要素仿真", layout="wide")
st.title("⚡ 高压冲击测量系统：全要素自动建模仿真")

# --- 2. 侧边栏：电压等级与源设置 ---
st.sidebar.header("🚀 1. 电压等级与方波源")
kv_level = st.sidebar.selectbox("选择分压器电压等级 (kV)", [200, 400, 800, 1200, 2400], index=3)

# 理想/不理想源切换
source_mode = st.sidebar.toggle("使用理想方波源", value=False)
r_src = 0.00
tr_src_ns = 0.00
if not source_mode:
    r_src = st.sidebar.number_input("源内阻 (Ω)", value=50.00, step=0.01, format="%.2f")
    tr_src_ns = st.sidebar.number_input("源原生上升时间 (ns)", value=20.00, step=0.01, format="%.2f")

# 预设物理尺寸
if kv_level == 200: h_init, d_init, r1_init = 1.20, 0.40, 2000.00
elif kv_level == 400: h_init, d_init, r1_init = 2.50, 0.60, 4000.00
elif kv_level == 800: h_init, d_init, r1_init = 4.50, 0.90, 8000.00
elif kv_level == 1200: h_init, d_init, r1_init = 6.50, 1.25, 10000.00
else: h_init, d_init, r1_init = 12.00, 2.20, 20000.00

st.sidebar.divider()
st.sidebar.header("📏 2. 物理几何尺寸")
h_total = st.sidebar.number_input("分压器总高度 H (m)", value=h_init, step=0.01, format="%.2f")
d_ring = st.sidebar.number_input("均压环直径 D (m)", value=d_init, step=0.01, format="%.2f")
l_wire = st.sidebar.number_input("高压引线长度 Lw (m)", value=5.00, step=0.01, format="%.2f")

st.sidebar.header("🔌 3. 电路核心参数")
r1 = st.sidebar.number_input("高压臂电阻 R1 (Ω)", value=r1_init, step=0.01, format="%.2f")
r2 = st.sidebar.number_input("低压臂电阻 R2 (Ω)", value=10.00, step=0.01, format="%.2f")
r_damp_ext = st.sidebar.number_input("引线串联阻尼 (Ω)", value=150.00, step=0.01, format="%.2f")

st.sidebar.header("📦 4. 末端 RLC 补偿与测量")
lp_end = st.sidebar.number_input("末端并联电感 Lp (μH)", value=0.00, step=0.01, format="%.2f")
cp_end = st.sidebar.number_input("末端并联电容 Cp (pF)", value=0.00, step=0.01, format="%.2f")
rs = st.sidebar.number_input("首端匹配电阻 Rs (Ω)", value=50.00, step=0.01, format="%.2f")
rt = st.sidebar.selectbox("示波器输入阻抗 (Ω)", [1000000.0, 50.0], index=1)

# --- 3. 核心物理计算逻辑 ---
def run_ultimate_sim():
    # A. 自动计算寄生电容 Cg
    eps0 = 8.854187e-12
    cg_pf = (2 * np.pi * eps0 * h_total) / (np.log(4 * h_total / d_ring) - 1) * 1e12 * 1.15
    
    # B. 自动计算全回路电感 L (引线 + 本体)
    mu0 = 4 * np.pi * 1e-7
    path = l_wire + h_total
    l_loop_uh = 0.2 * path * (np.log(2 * path / (d_ring/2)) - 0.75)
    
    # C. 汇总系统动态参数
    # 总电感：回路电感 + 末端补偿电感
    L_sys = (l_loop_uh + lp_end) * 1e-6
    # 总电容：寄生电容 + 末端补偿电容
    C_sys = (cg_pf + cp_end) * 1e-12
    # 总阻尼：源内阻 + 引线阻尼 + 首端匹配 + (示波器负载)
    r_total_sys = r_src + r_damp_ext + rs + (50.0 if rt == 50.0 else 0)
    
    # D. 建立二阶响应模型
    sys = signal.TransferFunction([1], [L_sys * C_sys, r_total_sys * C_sys, 1])
    t = np.linspace(0, 5e-6, 5000)
    t, y = signal.step(sys, T=t)
    
    # E. 实际测量变比 K
    r2_eff = (r2 * rt) / (r2 + rt)
    k_actual = (r1 + r2_eff) / r2_eff
    
    return t, y, cg_pf, l_loop_uh, k_actual

t_v, y_v, cg_res, l_res, k_res = run_ultimate_sim()

# --- 4. 仪表盘与指标 ---
c1, c2, c3, c4 = st.columns(4)
try:
    idx10 = np.where(y_v >= 0.1)[0][0]
    idx90 = np.where(y_v >= 0.9)[0][0]
    tr_divider_ns = (t_v[idx90] - t_v[idx10]) * 1e9
    # 合成总上升时间 (考虑方波源)
    tr_total_ns = np.sqrt(tr_divider_ns**2 + tr_src_ns**2)
    c1.metric("合成上升时间 Tr", f"{tr_total_ns:.2f} ns")
except:
    c1.metric("上升时间 Tr", "N/A")

c2.metric("计算寄生电容 Cg", f"{cg_res:.2f} pF")
c3.metric("全回路电感 L", f"{l_res:.2f} μH")
c4.metric("测量变比 K", f"{k_res:.2f}")

# --- 5. 波形展示 ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_v*1e6, y=y_v, name='仿真响应', line=dict(color='#00D4FF', width=2.5)))
fig.add_hline(y=1.0, line_dash="dash", line_color="white", opacity=0.3)
fig.update_layout(xaxis_title="时间 (μs)", yaxis_title="pu", template="plotly_dark", height=600)
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 仿真状态：{'非理想源模式' if not source_mode else '理想源模式'}。已自动关联 H={h_total:.2f}m 与 Lw={l_wire:.2f}m 的回路特性。")
