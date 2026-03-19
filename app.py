import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

# --- 1. 页面配置 ---
st.set_page_config(page_title="高压仿真对比", layout="wide")
st.title("⚡ 高压分压器：实测对比仿真工具")

# --- 2. 侧边栏：参数调节 ---
st.sidebar.header("🚀 1. 方波源设置")
source_mode = st.sidebar.toggle("使用理想方波源", value=True)
if not source_mode:
    r_source = st.sidebar.slider("源内阻 (Ω)", 0, 100, 50)
    tr_source_ns = st.sidebar.slider("源原生上升时间 (ns)", 0, 200, 50)
else:
    r_source = 0
    tr_source_ns = 0

st.sidebar.divider()
st.sidebar.header("📏 2. 结构与引线 (1200kV 典型值)")
h = st.sidebar.slider("高度 H (m)", 0.5, 15.0, 6.5)
d = st.sidebar.slider("均压环直径 D (m)", 0.1, 3.0, 1.2)
l_lead = st.sidebar.slider("引线电感 L (μH)", 0.1, 20.0, 5.0)

st.sidebar.header("🔌 3. 电路参数")
rd_int = st.sidebar.slider("内部阻尼 Rd (Ω)", 0, 1000, 150)
rs = st.sidebar.slider("首端匹配 Rs (Ω)", 0, 100, 50)

# --- 3. 核心计算逻辑 ---
def calculate_response():
    # 物理常数与 Cg 计算
    eps0 = 8.854e-12
    cg_pf = (2 * np.pi * eps0 * h) / (np.log(4 * h / d) - 1) * 1e12 * 1.15
    
    L = l_lead * 1e-6
    C = cg_pf * 1e-12
    # 总阻尼包含源内阻
    R_total = rd_int + rs + r_source
    
    # 建立二阶系统
    sys = signal.TransferFunction([1], [L * C, R_total * C, 1])
    t = np.linspace(0, 4e-6, 4000)
    t, y = signal.step(sys, T=t)
    
    return t, y, cg_pf

t, y, cg_calc = calculate_response()

# --- 4. 稳健的指标计算 (修复 NameError) ---
tr_final = "N/A"
os_pct = 0.0

try:
    # 寻找 10% 和 90% 的点
    idx10 = np.where(y >= 0.1)[0]
    idx90 = np.where(y >= 0.9)[0]
    
    if len(idx10) > 0 and len(idx90) > 0:
        # 计算分压器自身上升时间
        tr_divider_ns = (t[idx90[0]] - t[idx10[0]]) * 1e9
        # 如果非理想源，使用平方和根公式合成
        tr_final_val = np.sqrt(tr_divider_ns**2 + tr_source_ns**2)
        tr_final = f"{tr_final_val:.1f} ns"
    
    if np.max(y) > 1.0:
        os_pct = (np.max(y) - 1.0) * 100
except Exception as e:
    st.error(f"计算过程异常: {e}")

# --- 5. UI 展示 ---
c1, c2, c3 = st.columns(3)
c1.metric("合成上升时间 (Tr)", tr_final)
c2.metric("超调量 (Overshoot)", f"{os_pct:.1f} %")
c3.metric("估算对地电容 (Cg)", f"{cg_calc:.1f} pF")

fig = go.Figure()
fig.add_trace(go.Scatter(x=t*1e6, y=y, name='仿真波形', line=dict(color='#00CC96', width=3)))
fig.add_hline(y=1.0, line_dash="dash", line_color="red", opacity=0.5)
fig.update_layout(xaxis_title="时间 (μs)", yaxis_title="归一化电压", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

st.info(f"💡 提示：当前{'已考虑' if not source_mode else '未考虑'}方波源影响。实际对比 1200kV 设备时，建议开启非理想源模式并设置源内阻为 50Ω。")
