from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.config import AGENT_SETTINGS
from app.runtime.runtime import AgentRuntime
from app.telemetry.log_store import AgentLogStore

st.set_page_config(page_title="Mango Agent Control Tower", layout="wide")


# Initialize Session State
if "agent_log_store" not in st.session_state:
    st.session_state["agent_log_store"] = AgentLogStore()

if "runtime" not in st.session_state:
    # สร้าง Runtime ใหม่เมื่อยังไม่มี หรือหลังจากถูกเคลียร์ทิ้ง
    st.session_state["runtime"] = AgentRuntime(st.session_state["agent_log_store"])
    st.session_state["chat_history"] = []

runtime: AgentRuntime = st.session_state["runtime"]
chat_history = st.session_state["chat_history"]

st.title("Mango Multi-Agent Control Tower")
st.caption("ควบคุม 3 เอเจนต์ (IC, PPN, OF) ด้วย Strands + FastMCP")

with st.sidebar:
    st.subheader("Agent Status")
    for key, settings in AGENT_SETTINGS.items():
        st.write(f"**{settings.name}** → `{settings.server_url}`")
    
    # ปุ่ม Reset ที่ปรับปรุงใหม่
    if st.button("Clear conversation & logs", type="primary"):
        # 1. สั่งปิด Connection เดิมอย่างถูกต้อง (Graceful Shutdown)
        runtime.shutdown()
        
        # 2. ลบ Runtime ออกจาก Session State เพื่อบังคับให้สร้างใหม่ในรอบหน้า
        del st.session_state["runtime"]
        
        # 3. เคลียร์ประวัติแชทและ Log
        st.session_state["chat_history"] = []
        st.session_state["agent_log_store"].clear()
        
        # 4. สั่ง Rerun เพื่อเริ่มระบบใหม่ทันที
        st.rerun()

st.divider()

# Render Chat History
for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
user_message = st.chat_input("พิมพ์คำถามเกี่ยวกับคลัง วัสดุ แผนงาน หรือใบเบิกที่นี่")
if user_message:
    chat_history.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)
    with st.chat_message("assistant"):
        with st.spinner("กำลังหาเอเจนต์ที่เหมาะสม..."):
            try:
                response_text = runtime.handle(user_message)
                st.markdown(response_text)
                chat_history.append({"role": "assistant", "content": response_text})
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาด: {e}")
                # กรณี Error ร้ายแรง อาจแนะนำให้ user กด Reset
                st.info("ลองกดปุ่ม 'Clear conversation & logs' เพื่อรีเซ็ตระบบ")

# Log Monitor
st.subheader("Agent Log Monitor")
logs = runtime.log_store.tail(300)
if logs:
    df = pd.DataFrame(logs)
    st.dataframe(
        df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "timestamp": st.column_config.TextColumn("Time", width="medium"),
            "agent": st.column_config.TextColumn("Agent", width="small"),
            "stage": st.column_config.TextColumn("Stage", width="small"),
            "message": st.column_config.TextColumn("Message", width="large"),
        }
    )
else:
    st.info("ยังไม่มี log แสดงผล")