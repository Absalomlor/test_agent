# Mango Multi-Agent Control Tower

โครงการนี้สาธิตสถาปัตยกรรม multi-agent ที่ประกอบด้วย 3 เอเจนต์เฉพาะทาง (IC, PPN, OF) ซึ่งแต่ละตัวมี FastMCP server, ชุด Tool และ Prompt ของตนเอง แล้วถูกประสานงานด้วย Strands Orchestrator พร้อมแดชบอร์ด Streamlit สำหรับสนทนาและตรวจสอบ log แบบเรียลไทม์

## สถาปัตยกรรม
- **FastMCP servers**
  - `IC` – เครื่องมือ `get_material`, `low_materrial` สำหรับฐานข้อมูลคลังวัสดุ
  - `PPN` – เครื่องมือ `get_plan`, `get_material_use` สำหรับข้อมูลแผนงาน/การใช้วัสดุ
  - `OF` – เครื่องมือ `pretty_cash_fillform`, `pr_fillform` สำหรับใบเบิกเงินสดย่อยและใบสั่งซื้อวัสดุ
- **Mock DB (SQLite)**
  - ตาราง `ic_inventory` และ `ppn_plans` ถูก seed ด้วยข้อมูลตัวอย่าง ครอบคลุมคอลัมน์ทั้งหมดที่กำหนด
- **Strands Agents**
  - แต่ละโดเมนสร้างเป็น agent เต็มรูปแบบที่ดึง tool ผ่าน `MCPClient` และมี callback handler สำหรับบันทึกขั้นตอน
  - Orchestrator Agent ใช้ Tool-Agent pattern เพื่อเรียก agent เฉพาะทางแบบ tool ทำให้เกิด inter-agent collaboration
- **Observability**
  - `AgentLogStore` เก็บ event ตามสเตจ `input → process → tool → output` สำหรับทุก agent
  - Streamlit UI แสดงทั้งบทสนทนาและ log tableau ในแดชบอร์ดเดียว

## โครงสร้างไฟล์หลัก
```
app/
├─ agents/
│  ├─ domain_agents.py      # ตัวสร้างเอเจนต์ IC/PPN/OF + callback
│  └─ orchestrator.py       # Orchestrator agent + tool wrapper
├─ config.py                # ค่าพอร์ต, prompt, รายละเอียด agent
├─ data/
│  ├─ mock_db.py            # สร้าง/seed SQLite DB
│  └─ repository.py         # ชั้น query สำหรับ IC และ PPN
├─ mcp_servers/
│  ├─ ic_server.py          # FastMCP server + tools get_material/low_materrial
│  ├─ ppn_server.py         # FastMCP server + tools get_plan/get_material_use
│  ├─ of_server.py          # FastMCP server + tools pretty_cash_fillform/pr_fillform
│  └─ run_all_servers.py    # utility สตาร์ท server ทั้งหมดพร้อมกัน
├─ runtime/runtime.py       # รวม domain agents + orchestrator ให้เรียกใช้ง่าย
├─ telemetry/
│  ├─ log_store.py          # โครงสร้าง log event
│  └─ callbacks.py          # custom callback สำหรับ Strands
└─ ui/dashboard.py          # Streamlit dashboard (chat + log monitor)
```

## การติดตั้ง
1. สร้าง virtualenv และติดตั้ง dependency
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. คัดลอกไฟล์ `.env.example` เป็น `.env` แล้วกรอกค่า credential/การตั้งค่าของคุณ (AWS/Bedrock, โมเดล ฯลฯ)
3. สร้าง/seed DB จาก CSV ต้นทาง (`ic_data.csv`, `ppn_data.csv`):
   ```bash
   python -m app.data.mock_db
   ```
4. กำหนดค่าระบบ LLM ให้ Strands ทำงานได้ (เช่น AWS Bedrock, OpenAI, LiteLLM) ตามเอกสารใน `strand_guild1.txt`

## การตั้งค่า AWS Bedrock (ค่าเริ่มต้นของโปรเจกต์)
1. เปิดสิทธิการใช้งานโมเดลที่ต้องการใน AWS Bedrock console (ตัวอย่างนี้ใช้ `anthropic.claude-sonnet-4-20250514-v1:0`)
2. กรอกค่า AWS credential และตัวแปรที่เกี่ยวข้องในไฟล์ `.env` (อ้างอิงจาก `.env.example`) หรือใช้ `aws configure` ตามต้องการ
3. หากต้องการเปลี่ยน region หรือโมเดล ให้ตั้งค่าตัวแปรใน `.env` เพิ่มเติมก่อนรันแอป
   - `BEDROCK_REGION` หรือ `AWS_REGION` – กำหนด region ของ Bedrock (ดีฟอลต์ `us-west-2`)
   - `STRANDS_MODEL_ID` – ระบุ model ID ที่ต้องการใช้
   - `STRANDS_MODEL_TEMPERATURE` – ปรับ temperature ของโมเดล (ค่าเริ่มต้น `0.2`)
4. รันสคริปต์ตามหัวข้อถัดไปได้เลย ระบบจะสร้าง `BedrockModel` จากค่าด้านบนโดยอัตโนมัติ คุณเพียงจัดการ credential เองเท่านั้น

## โครงสร้างข้อมูล (CSV → SQLite)
- `ic_data.csv` → โหลดเข้า `ic_inventory` (`pre_event, item_whcode, c_des1, c_des2, itemcode, proj_whcode, qtybal, unitname, whcode`)
- `ppn_data.csv` → โหลดเข้า `ppn_plans` (`cost_code, c_des1=material, c_des2='', itemcode=material_code, pre_event=project_id, required_qty, start_date, task_id, task_name, unit`)
- คอลัมน์ `updated_at` ในสองไฟล์จะถูกละเว้นอัตโนมัติ
- สั่ง `python -m app.data.mock_db` เมื่อใดก็ได้เพื่อรีสร้าง `mock_data.sqlite` จาก CSV เหล่านี้

## การรันระบบ
เปิด 2 เทอร์มินัล

### เทอร์มินัล 1: FastMCP Servers
```bash
python -m app.mcp_servers.run_all_servers
```
> สคริปต์นี้จะบูต server IC/PPN/OF ที่พอร์ต `8101/8102/8103` พร้อม health log ในคอนโซล

### เทอร์มินัล 2: Streamlit Dashboard
```bash
streamlit run app/ui/dashboard.py
```
> หน้า UI จะเปิดให้พิมพ์คำถาม (ภาษาไทยหรืออังกฤษ) และเห็น log การทำงานแบบเรียลไทม์

## การใช้งาน
1. พิมพ์คำถามเกี่ยวกับคลัง วัสดุ แผนงาน หรือใบเบิกในช่อง chat
2. Orchestrator จะเลือก agent ที่เหมาะสม หรือเรียกหลาย agent หากคำสั่งซับซ้อน
3. ส่วนล่างของหน้า UI แสดง log ทุก step: ข้อความเข้า, การตัดสินใจเรียก tool, ผลลัพธ์ และ error (ถ้ามี)
4. ปุ่ม *Clear conversation & logs* ใน sidebar ใช้รีเซ็ต state เพื่อเริ่มงานใหม่

## การขยาย/ปรับแต่ง
- เพิ่ม/ปรับข้อมูลใน `ic_data.csv` หรือ `ppn_data.csv` แล้วสั่ง `python -m app.data.mock_db` เพื่อ seed ใหม่
- เปลี่ยน prompt หรือเพิ่ม agent ใหม่โดยแก้ `AGENT_SETTINGS` ใน `app/config.py`
- หากต้องการรัน Strands agent ด้วย provider อื่น ให้ดูตัวอย่างการตั้งค่าใน `strand_guild1.txt` (ส่วน Model Providers)

## การทดสอบ/ตรวจสอบ
- สั่ง `python -m app.data.mock_db` เพื่อยืนยันว่า DB ถูกสร้างและ seed แล้ว
- เรียก endpoints FastMCP ด้วยเครื่องมืออย่าง `curl http://127.0.0.1:8101/health` (เมื่อเปิด custom route เพิ่มได้)
- ติดตาม log เพิ่มเติมผ่าน terminal ที่รัน FastMCP หรือเพิ่ม observability อื่น ๆ ได้จาก Strands AgentResult ที่ `domain_agents.py`
