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


if "agent_log_store" not in st.session_state:
    st.session_state["agent_log_store"] = AgentLogStore()

if "runtime" not in st.session_state:
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
    if st.button("Clear conversation & logs"):
        chat_history.clear()
        runtime.reset_logs()
        st.success("Reset complete", icon="✅")

st.divider()

for message in chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_message = st.chat_input("พิมพ์คำถามเกี่ยวกับคลัง วัสดุ แผนงาน หรือใบเบิกที่นี่")
if user_message:
    chat_history.append({"role": "user", "content": user_message})
    with st.chat_message("user"):
        st.markdown(user_message)
    with st.chat_message("assistant"):
        with st.spinner("กำลังหาเอเจนต์ที่เหมาะสม..."):
            response_text = runtime.handle(user_message)
        st.markdown(response_text)
    chat_history.append({"role": "assistant", "content": response_text})

st.subheader("Agent Log Monitor")
logs = runtime.log_store.tail(300)
if logs:
    df = pd.DataFrame(logs)
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("ยังไม่มี log แสดงผล")
