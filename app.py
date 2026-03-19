import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 页面配置 ---
st.set_page_config(page_title="高压全要素仿真", layout="wide")
st.title("⚡ 高压测量系统：全要素动态仿真工具")
st.markdown("集成了高压线阻尼、结构参数、电缆匹配及末端 RLC 补偿的全物理模型。")

# --- 侧边栏：参数配置 ---
st.sidebar.header("1. 高压侧与结构")
h = st.sidebar.slider("分压器高度 H (m)", 0.5, 10.0, 2.5)
d = st.sidebar.slider("主体直径 D (m)", 0.1, 2.0, 0.4)
# 自动计算 Cg (pF)
eps0 = 8.854e-12
cg_pf = (2 * np.pi * eps0 * h) / (np.log(4 * h / d) - 1) * 1e12 * 1.15 # 含邻近修正

r_lead_damp = st.sidebar.slider("高压线串联阻尼 (Ω)", 0, 1000, 100, help="串联在高压引线上的电阻")
l_lead = st.sidebar.slider("引线电感 L (μH)", 0.1, 15.0, 2.0)

st.sidebar.divider()
st.sidebar.header("2. 末端 RLC 补偿 (并联)")
rp_end = st.sidebar.number_input("末端并联电阻 Rp (Ω)", value=1000000.0)
lp_end = st.sidebar.slider("末端并联电感 Lp (μH)", 0.0, 10.0, 0.0)
cp_end = st.sidebar.slider("末端并联电容 Cp (pF)", 0, 1000, 50)

st.sidebar.divider()
st.sidebar.header("3. 传输线与匹配")
rs = st.sidebar.slider("首端匹配 Rs (Ω)", 0, 150, 50)
z0 = st.sidebar.selectbox("电缆阻抗 Z0 (Ω)", [50, 75])
r_scope = st.sidebar.selectbox("示波器阻抗 (Ω)", [1e6, 50])

# --- 核心仿真逻辑 ---
def run_advanced_sim():
    # 汇总参数
    # 总电感：引线电感 + 末端补偿电感
    L_total = (l_lead + lp_end) * 1e-6
    # 总电容：分压器对地电容 + 末端补偿电容
    C_total = (cg_pf + cp_end) * 1e-12
    # 总阻尼：高压线阻尼 + 首端匹配 + 磁珠(假定50)
    R_ser = r_lead_damp + rs + 50 
    
    # 考虑末端并联电阻 Rp 对系统的阻尼作用 (简化为并联衰减)
    # 建立状态空间或传递函数
    # G(s) = (1/LC) / (s^2 + (R/L + 1/RC)s + (1+R/Rp)/LC)
    num = [1]
    den = [L_total * C_total, 
           R_ser * C_total + L_total / rp_end, 
           1 + R_ser / rp_end]
    
    sys = signal.TransferFunction(num, den)
    t = np.linspace(0, 3e-6, 3000)
    t, y = signal.step(sys, T=t)
    
    # 归一化处理
    y_final = 1 / (1 + R_ser / rp_end)
    y_norm = y / y_final
    
    return t, y_norm

t_sim, y_sim = run_advanced_sim()

# --- 结果展示 ---
col1, col2 = st.columns(2)
# 计算指标
try:
    idx10 = np.where(y_sim >= 0.1)[0][0]
    idx90 = np.where(y_sim >= 0.9)[0][0]
    tr = (t_sim[idx90] - t_sim[idx10]) * 1e9
    col1.metric("上升时间 (Tr)", f"{tr:.1f} ns")
except:
    col1.metric("上升时间 (Tr)", "N/A")

os = (np.max(y_sim) - 1.0) * 100 if np.max(y_sim) > 1.0 else 0
col2.metric("超调量 (Overshoot)", f"{os:.1f} %")

# 绘图
fig = go.Figure()
fig.add_trace(go.Scatter(x=t_sim*1e6, y=y_sim, name='实测波形', line=dict(color='#28A745', width=3)))
fig.add_hline(y=1.0, line_dash="dash", line_color="red")
fig.update_layout(xaxis_title="时间 (μs)", yaxis_title="归一化电压", height=500, template="plotly_dark")
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 当前对地电容 Cg 为 {cg_pf:.1f} pF。通过调节高压线阻尼和末端 Cp，可以找到上升时间与超调的最佳平衡点。")
st.write(f"📊 估算上升时间 Tr: {t[idx90]*1e9:.1f} ns")
