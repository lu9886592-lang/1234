import streamlit as st
import numpy as np
from scipy import signal
import plotly.graph_objects as go

st.title("⚡ 高压分压器在线仿真")

# 侧边栏参数
rd = st.sidebar.slider("阻尼 Rd (Ohm)", 0, 1000, 300)
l_l = st.sidebar.slider("引线 L (uH)", 0.1, 10.0, 2.0)
cg = st.sidebar.slider("对地电容 Cg (pF)", 50, 500, 150)

# 物理仿真逻辑
# 系统传递函数 G(s) = 1 / (LCs^2 + RC s + 1)
L, C, R = l_l*1e-6, cg*1e-12, rd + 50
sys = signal.TransferFunction([1], [L*C, R*C, 1])

# 仿真时间 3微秒
t = np.linspace(0, 3e-6, 1000)
t, y = signal.step(sys, T=t)

# 绘图
fig = go.Figure(data=go.Scatter(x=t*1e6, y=y, line=dict(color='#007BFF', width=3)))
fig.update_layout(
    title="方波阶跃响应",
    xaxis_title="时间 (us)",
    yaxis_title="归一化电压",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# 计算指标
idx90 = np.where(y >= 0.9)[0][0] if any(y >= 0.9) else 0
st.write(f"📊 估算上升时间 Tr: {t[idx90]*1e9:.1f} ns")
