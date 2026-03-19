import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="1200kV分压器专业仿真", layout="wide")
st.title("⚡ 高压冲击测量系统：全要素专业仿真")

# --- 2. 侧边栏：分压器结构 ---
st.sidebar.header("📏 1. 分压器主体 (R1/R2)")
r_high = st.sidebar.number_input("高压臂电阻 R1 (Ω)", value=10000.0)
r_low = st.sidebar.number_input("低压臂电阻 R2 (Ω)", value=10.0)
h = st.sidebar.slider("分压器高度 H (m)", 0.5, 12.0, 6.5)
d_ring = st.sidebar.slider("均压环直径 D (m)", 0.1, 2.5, 1.2)

st.sidebar.header("🔌 2. 测量电缆与匹配")
cable_len = st.sidebar.slider("测量电缆长度 (m)", 1, 100, 20)
z0 = st.sidebar.selectbox("电缆特性阻抗 Z0 (Ω)", [50, 75], index=0)
rs = st.sidebar.slider("首端匹配电阻 Rs (Ω)", 0, 100, 50, help="应等于Z0以消除反射")
rt_scope = st.sidebar.selectbox("末端匹配/示波器阻抗 (Ω)", [1e6, 50], index=1)

st.sidebar.header("➰ 3. 寄生参数与补偿")
l_lead = st.sidebar.slider("引线电感 L (μH)", 0.1, 20.0, 5.0)
r_damp = st.sidebar.slider("高压线串联阻尼 (Ω)", 0, 500, 100)
cp_end = st.sidebar.slider("末端补偿电容 Cp (pF)", 0, 1000, 0)

# --- 3. 核心计算逻辑 ---
def run_pro_sim():
    # 物理常数计算 Cg
    eps0 = 8.854e-12
    cg_pf = (2 * np.pi * eps0 * h) / (np.log(4 * h / d_ring) - 1) * 1e12 * 1.15
    
    # 模拟传输线延时 (假设波速 0.7c)
    tau = cable_len / (3e8 * 0.7)
    
    # 集中参数简化模型
    L = l_lead * 1e-6
    C = (cg_pf + cp_end) * 1e-12
    # 总阻尼
    r_total = r_damp + rs + (z0 if rt_scope == 50 else 0)
    
    sys = signal.TransferFunction([1], [L*C, r_total*C, 1])
    t = np.linspace(0, 4e-6, 4000)
    t, y = signal.step(sys, T=t)
    
    # 模拟反射叠加 (如果首末端不匹配)
    gamma_s = (rs - z0) / (rs + z0)
    gamma_r = (rt_scope - z0) / (rt_scope + z0)
    
    # 在 2*tau 时间点引入反射扰动
    reflection_idx = np.where(t > 2*tau)[0]
    if len(reflection_idx) > 0 and abs(gamma_s * gamma_r) > 0.01:
        y[reflection_idx] += y[reflection_idx] * gamma_s * gamma_r * 0.2
        
    # 计算实际分压比 (考虑示波器并联)
    r2_eff = (r_low * rt_scope) / (r_low + rt_scope)
    ratio = (r_high + r2_eff) / r2_eff
    
    return t, y, cg_pf, ratio

t_p, y_p, cg_calc, final_ratio = run_pro_sim()

# --- 4. 结果展示 ---
c1, c2, c3 = st.columns(3)
# 指标计算
try:
    idx10 = np.where(y_p >= 0.1)[0][0]
    idx90 = np.where(y_p >= 0.9)[0][0]
    tr = (t_p[idx90] - t_p[idx10]) * 1e9
    c1.metric("上升时间 (Tr)", f"{tr:.1f} ns")
except:
    c1.metric("上升时间 (Tr)", "检测中")

c2.metric("实际分压比", f"{final_ratio:.1f} : 1")
c3.metric("对地电容 (Cg)", f"{cg_calc:.1f} pF")

# 绘图
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_p*1e6, y=y_p, name='示波器输出波形', line=dict(color='#FF4B4B', width=3)))
fig.update_layout(xaxis_title="时间 (μs)", yaxis_title="归一化电压", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 调试建议：调节'电缆长度'。如果 Rs 不等于 {z0}Ω，你会看到波形在 {cable_len/105:.1f}μs 处出现反射阶梯。")
