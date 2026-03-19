{\rtf1\ansi\ansicpg936\cocoartf2868
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fmodern\fcharset0 Courier-Bold;}
{\colortbl;\red255\green255\blue255;\red0\green0\blue0;}
{\*\expandedcolortbl;;\cssrgb\c0\c0\c0;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\deftab720
\pard\pardeftab720\partightenfactor0

\f0\b\fs26 \cf0 \expnd0\expndtw0\kerning0
\outl0\strokewidth0 \strokec2 import streamlit as st\
import numpy as np\
import plotly.graph_objects as go\
from scipy import signal\
\
st.set_page_config(page_title="\uc0\u20840 \u38459 \u25239 \u21305 \u37197 \u20998 \u21387 \u22120 \u20223 \u30495 ", layout="wide")\
st.title("\uc0\u9889  \u32771 \u34385 \u30005 \u32518 \u19982 \u31034 \u27874 \u22120 \u38459 \u25239 \u30340 \u20998 \u21387 \u22120 \u20223 \u30495 ")\
\
# --- \uc0\u20391 \u36793 \u26639 \u65306 \u26032 \u22686 \u38459 \u25239 \u21442 \u25968  ---\
st.sidebar.header("1. \uc0\u20256 \u36755 \u19982 \u21305 \u37197 \u21442 \u25968 ")\
z_cable = st.sidebar.selectbox("\uc0\u30005 \u32518 \u29305 \u24615 \u38459 \u25239  Z0 (\u937 )", [50, 75], index=0)\
r_s = st.sidebar.slider("\uc0\u39318 \u31471 \u21305 \u37197 \u30005 \u38459  Rs (\u937 )", 0, 100, 50, help="\u36890 \u24120 \u24212 \u31561 \u20110 Z0")\
r_scope = st.sidebar.selectbox("\uc0\u31034 \u27874 \u22120 \u36755 \u20837 \u38459 \u25239  (\u937 )", [1e6, 50], index=0, help="1M\u937 \u20026 \u39640 \u38459 , 50\u937 \u20026 \u21305 \u37197 ")\
cable_len = st.sidebar.slider("\uc0\u30005 \u32518 \u38271 \u24230  (m)", 1, 50, 20)\
\
st.sidebar.divider()\
st.sidebar.header("2. \uc0\u20998 \u21387 \u22120 \u26412 \u20307 \u21442 \u25968 ")\
rd_high = st.sidebar.slider("\uc0\u39640 \u21387 \u33218 \u38459 \u23612  Rd (\u937 )", 0, 1500, 300)\
l_lead = st.sidebar.slider("\uc0\u24341 \u32447 \u30005 \u24863  L (\u956 H)", 0.1, 10.0, 2.0)\
# \uc0\u20351 \u29992 \u20043 \u21069 \u25972 \u21512 \u30340  Cg \u35745 \u31639 \u36923 \u36753 \
h = st.sidebar.slider("\uc0\u39640 \u24230  H (m)", 0.5, 5.0, 2.5)\
cg_pf = (2 * np.pi * 8.854e-12 * h) / (np.log(4 * h / 0.4) - 1) * 1e12\
\
# --- \uc0\u26680 \u24515 \u20223 \u30495 \u36923 \u36753  (\u21547 \u21453 \u23556 \u27169 \u25311 ) ---\
def run_full_sim(rd, l_l, cg, zs, zc, zr, c_len):\
    # \uc0\u22522 \u26412  RLC \u21709 \u24212 \
    L = l_l * 1e-6\
    C = cg * 1e-12\
    # \uc0\u36825 \u37324 \u30340 \u24635 \u30005 \u38459 \u21463 \u21305 \u37197 \u30005 \u38459  Rs \u24433 \u21709 \
    R_total = rd + zs \
    \
    num = [1]\
    den = [L * C, R_total * C, 1]\
    sys = signal.TransferFunction(num, den)\
    \
    t = np.linspace(0, 3e-6, 3000)\
    t, y = signal.step(sys, T=t)\
    \
    # --- \uc0\u27169 \u25311 \u30005 \u32518 \u21453 \u23556  (\u20256 \u36755 \u32447 \u25928 \u24212 ) ---\
    # \uc0\u35745 \u31639 \u26411 \u31471 \u21453 \u23556 \u31995 \u25968  Gamma_r \u21644 \u39318 \u31471 \u21453 \u23556 \u31995 \u25968  Gamma_s\
    gamma_r = (zr - zc) / (zr + zc)\
    gamma_s = (zs - zc) / (zs + zc)\
    \
    # \uc0\u30005 \u32518 \u21333 \u31243 \u24310 \u26102  (\u20551 \u35774 \u20256 \u25773 \u36895 \u24230 \u20026  0.7c)\
    tau = c_len / (3e8 * 0.7) \
    \
    # \uc0\u21472 \u21152 \u21453 \u23556 \u27874  (\u31616 \u21270 \u27169 \u22411 \u65306 \u32771 \u34385 \u21069 \u20004 \u27425 \u21453 \u23556 )\
    y_final = np.copy(y)\
    mask_1 = t > 2*tau\
    if any(mask_1):\
        # \uc0\u31532 \u19968 \u27425 \u21453 \u23556 \u22238 \u21040 \u31034 \u27874 \u22120 \
        y_final[mask_1] += y[mask_1] * gamma_r * gamma_s\
        \
    return t, y_final\
\
t_p, y_p = run_full_sim(rd_high, l_lead, cg_pf, r_s, z_cable, r_scope, cable_len)\
\
# --- \uc0\u32472 \u22270  ---\
fig = go.Figure()\
fig.add_trace(go.Scatter(x=t_p*1e6, y=y_p, name='\uc0\u31034 \u27874 \u22120 \u23454 \u27979 \u27874 \u24418 ', line=dict(width=3, color='#17A2B8')))\
fig.update_layout(xaxis_title="\uc0\u26102 \u38388  (\u956 s)", yaxis_title="\u24402 \u19968 \u21270 \u30005 \u21387 ", height=500)\
st.plotly_chart(fig, use_container_width=True)\
\
# \uc0\u35745 \u31639 \u25351 \u26631 \
idx90 = np.where(y_p >= 0.9)[0][0] if any(y_p >= 0.9) else 0\
tr = t_p[idx90] * 1e9\
st.info(f"\uc0\u55357 \u56481  \u20272 \u31639 \u19978 \u21319 \u26102 \u38388  Tr: \{tr:.1f\} ns | \u21305 \u37197 \u29366 \u24577 \u65306 \{'\u21305 \u37197 \u33391 \u22909 ' if abs(r_s-z_cable)<5 else '\u23384 \u22312 \u21453 \u23556 '\}")}