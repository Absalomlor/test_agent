from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional
import boto3
import pandas as pd

from app.config import (
    AGING_REPORT_PATH,
    ACTUAL_COST_PATH,
    EXPENSE_CODE_PATH,
    PPN_DATA_PATH
)

class DataRepository:
    def __init__(self) -> None:
        # --- Load DataFrames ---
        self.aging_df = self._load_csv(AGING_REPORT_PATH)
        if "diff_day" in self.aging_df.columns:
            self.aging_df["diff_day"] = pd.to_numeric(self.aging_df["diff_day"], errors="coerce").fillna(0)
            self.aging_df = self.aging_df.sort_values(by="diff_day", ascending=False)

        self.cost_df = self._load_csv(ACTUAL_COST_PATH, skiprows=3) 
        self.expense_df = self._load_csv(EXPENSE_CODE_PATH)
        self.ppn_df = self._load_csv(PPN_DATA_PATH)
        if "required_qty" in self.ppn_df.columns:
             self.ppn_df["required_qty"] = pd.to_numeric(self.ppn_df["required_qty"], errors='coerce').fillna(0)

        # Initialize Bedrock Client
        # ใช้ Region จาก Env หรือ Default เป็น us-east-1
        self.bedrock = boto3.client(
            'bedrock-runtime', 
            region_name=os.getenv("BEDROCK_REGION", "us-east-1") 
        )

        # --- Pre-calculate Expense String ---
        # เตรียมข้อมูลสำหรับ Prompt ไว้เลย จะได้ไม่ต้องวนลูปสร้างใหม่ทุกครั้งที่เรียก
        if "expens_code" in self.expense_df.columns and "expens_name" in self.expense_df.columns:
            self.expense_master_list_str = "\n".join(
                self.expense_df.apply(
                    lambda x: f"{x['expens_code']} - {x['expens_name']}", axis=1
                ).tolist()
            )
        else:
            self.expense_master_list_str = "No expense data available."

    def _load_csv(self, path, **kwargs) -> pd.DataFrame:
        try:
            return pd.read_csv(path, dtype=str, **kwargs).fillna("")
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return pd.DataFrame()

    # ... (ฟังก์ชัน Reporter และ PPN คงเดิม) ...
    def _normalize_report_name(self, name: str) -> str:
        if not name: return ""
        name_lower = name.lower()
        if "aging" in name_lower or "stock" in name_lower or "material" in name_lower:
            return "aging_stock_balance"
        if "cost" in name_lower or "actual" in name_lower or "budget" in name_lower:
            return "actual_cost"
        return name

    def get_report_names(self) -> List[str]:
        return ["aging_stock_balance", "actual_cost"]

    def get_report_columns(self, report_name: str) -> List[str]:
        std_name = self._normalize_report_name(report_name)
        if std_name == "aging_stock_balance": return list(self.aging_df.columns)
        elif std_name == "actual_cost": return list(self.cost_df.columns)
        return []

    def read_report(self, report_name: str, columns: Optional[List[str]] = None, limit: int = 20) -> List[Dict[str, Any]]:
        std_name = self._normalize_report_name(report_name)
        df = self.aging_df if std_name == "aging_stock_balance" else self.cost_df
        if columns:
            valid_cols = [c for c in columns if c in df.columns]
            if valid_cols: df = df[valid_cols]
        return df.head(limit).to_dict("records")

    def get_plan_columns(self) -> List[str]:
        return list(self.ppn_df.columns)

    def get_plan(self, query: str) -> List[Dict[str, Any]]:
        df = self.ppn_df
        mask = df.apply(lambda x: x.astype(str).str.contains(query, case=False, na=False)).any(axis=1)
        return df[mask].head(20).to_dict("records")

    def get_material_use(self) -> List[Dict[str, Any]]:
        if "c_des1" in self.ppn_df.columns and "required_qty" in self.ppn_df.columns:
            grouped = self.ppn_df.groupby("c_des1")["required_qty"].sum().reset_index()
            grouped = grouped.sort_values(by="required_qty", ascending=False)
            return grouped.head(50).to_dict("records")
        return self.ppn_df.head(20).to_dict("records")

    # --- OF Agent Tools (อัปเกรดใหม่ด้วย LLM) ---
    def phase_structure(self, text: str) -> Dict[str, Any]:
        amount_match = re.search(r'[\d,]+(\.\d{2})?', text)
        amount = 0.0
        if amount_match:
            try:
                clean_num = amount_match.group().replace(",", "")
                amount = float(clean_num)
            except: pass
        
        return {
            "date": None,
            "amount": amount,
            "description": text.strip(),
            "expense_code": "Call tool 'get_expense_code' with the description to get the AI-selected code."
        }

    def get_expense_code(self, description: str) -> List[Dict[str, str]]:
        """
        ใช้ LLM (Claude 3.7) หา expense code โดยตรงจากความหมาย
        """
        try:
            prompt = f"""
            คุณเป็นผู้เชี่ยวชาญด้านการจัดหมวดหมู่ค่าใช้จ่าย

            รายการค่าใช้จ่ายที่มี:
            {self.expense_master_list_str}

            คำอธิบาย: "{description}"

            ให้เลือกรหัสค่าใช้จ่ายที่เหมาะสมที่สุด โดยพิจารณาจากความหมายและบริบท

            ตัวอย่าง:
            - "รถไฟฟ้า" = ค่าเดินทาง (ไม่ใช่ค่าไฟฟ้า)
            - "กิน" = ค่าอาหาร
            - "ไฟฟ้า" = ค่าสาธารณูปโภค

            ตอบเฉพาะรหัส 5 ตัวเท่านั้นไม่ต้องอธิบายเพิ่มเติม เช่น F0036 หรือ G0144:
        """
            # เรียก Bedrock API
            response = self.bedrock.invoke_model(
                modelId='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
                body=json.dumps({
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 50,
                    "temperature": 0.0,
                    "anthropic_version": "bedrock-2023-05-31"
                })
            )
            
            # แกะ Response
            response_body = json.loads(response['body'].read())
            ai_code = response_body['content'][0]['text'].strip()
            
            # ค้นหาข้อมูลเต็มจากรหัสที่ AI เลือกมา
            matched_row = self.expense_df[self.expense_df['expens_code'] == ai_code]
            
            if not matched_row.empty:
                return matched_row[['expens_code', 'expens_name']].to_dict('records')
            else:
                # กรณี AI ตอบมาแต่รหัสหาไม่เจอใน CSV (Rare case)
                return [{"expens_code": ai_code, "expens_name": "AI Selected Code (Not in CSV List)"}]

        except Exception as e:
            print(f"Error calling Bedrock LLM: {e}")
            # Fallback ไปใช้วิธีเดิม (Keyword Search) ถ้า LLM มีปัญหา
            mask = self.expense_df["expens_name"].astype(str).str.contains(description, case=False, na=False)
            return self.expense_df[mask][["expens_code", "expens_name"]].head(5).to_dict("records")