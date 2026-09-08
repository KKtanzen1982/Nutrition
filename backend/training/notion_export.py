"""
訓練排程同步到 Notion
================================================

把訓練排程寫成 Notion 資料庫裡的一筆一筆 page（標題 + 日期屬性，比照 Notion「行事曆」範本的欄位慣例），
訓練項目明細（動作/組數次數或時長）寫進 page 內文，跟資料庫本身有哪些屬性欄位無關，一定看得到。

內文用「每組一行 to-do」而不是把整個動作濃縮成一行文字：運動中途如果力竭、需要臨時調整某一組的
重量或次數，只要點進那一行改掉尾端那個數字就好，不用整行重打，減少中途要停下來輸入的時間。

日期只寫日期本身（不含時間）——訓練排程本來就沒有時間欄位，硬塞一個時間只是誤導。

需要在 backend/.env 設定：
- NOTION_TOKEN：在 https://www.notion.so/my-integrations 建立 integration 拿到的 token（新版是 ntn_ 開頭，不用再加 secret_ 前綴）
- NOTION_DATABASE_ID：要寫入的 Notion 資料庫 ID，且該資料庫要「分享」給上面這個 integration
- NOTION_TITLE_PROPERTY（選填，預設 "Name"）：資料庫裡標題欄位的名稱
- NOTION_DATE_PROPERTY（選填，預設 "Date"）：資料庫裡日期欄位的名稱，型別要是 Notion 的 Date
- NOTION_CALENDAR_PROPERTY（選填）：資料庫裡用來勾選「顯示在行事曆」的 checkbox 欄位名稱，
  有設定的話每筆同步都會預設勾選；資料庫沒有這個欄位就不要設定，設定了但欄位不存在會同步失敗
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionNotConfiguredError(Exception):
    pass


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _event_title(program_name: str, day_label: Optional[str]) -> str:
    return f"{program_name} · {day_label}" if day_label else program_name


def _todo_block(text: str) -> Dict:
    return {
        "object": "block",
        "type": "to_do",
        "to_do": {"rich_text": [{"type": "text", "text": {"content": text}}], "checked": False},
    }


def _exercise_blocks(detail: Dict) -> List[Dict]:
    """健身房動作展開成一組一行 to-do（方便中途力竭時只改那一組的數字）；
    瑜珈/拉伸這類以時長為主的動作就一行帶過。"""
    name = detail.get("exercise_name") or ""
    sets = detail.get("sets")
    reps = detail.get("reps")
    weight = detail.get("weight_kg")
    duration = detail.get("duration_min")

    if sets and reps:
        lines = []
        for i in range(1, sets + 1):
            line = f"{name} · 第{i}組 · {reps}下"
            if weight:
                line += f" · {weight}kg"
            lines.append(line)
        return [_todo_block(line) for line in lines]

    if duration:
        return [_todo_block(f"{name} · {duration}分鐘")]

    return [_todo_block(name)] if name else []


def _page_children(exercise_type: str, duration_min: Optional[int], details: List[Dict]) -> List[Dict]:
    summary = exercise_type + (f" · {duration_min}分鐘" if duration_min else "")
    blocks = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]},
        }
    ]
    for detail in details:
        blocks.extend(_exercise_blocks(detail))
    return blocks


def push_schedule_entries(entries: List[Dict]) -> Dict:
    """把訓練排程寫入 Notion 資料庫，每筆一個 page，訓練項目明細放在 page 內文。
    entries 每筆需要：scheduled_date, program_name, day_label, exercise_type, duration_min, details（明細清單）"""
    token = os.getenv("NOTION_TOKEN")
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not token or not database_id:
        raise NotionNotConfiguredError("尚未設定 NOTION_TOKEN / NOTION_DATABASE_ID，請先在 backend/.env 設定")

    title_property = os.getenv("NOTION_TITLE_PROPERTY", "Name")
    date_property = os.getenv("NOTION_DATE_PROPERTY", "Date")
    calendar_property = os.getenv("NOTION_CALENDAR_PROPERTY")

    created = 0
    failed: List[Dict] = []

    with httpx.Client(timeout=15.0) as client:
        for entry in entries:
            # 驗證格式用，實際寫進 Notion 的日期只留 YYYY-MM-DD，不帶時間
            datetime.strptime(entry["scheduled_date"], "%Y-%m-%d")

            properties = {
                title_property: {"title": [{"text": {"content": _event_title(entry["program_name"], entry.get("day_label"))}}]},
                date_property: {"date": {"start": entry["scheduled_date"]}},
            }
            if calendar_property:
                properties[calendar_property] = {"checkbox": True}

            payload = {
                "parent": {"database_id": database_id},
                "properties": properties,
                "children": _page_children(entry.get("exercise_type", ""), entry.get("duration_min"), entry.get("details") or []),
            }
            res = client.post(f"{NOTION_API_BASE}/pages", headers=_headers(token), json=payload)
            if res.status_code >= 300:
                failed.append({"schedule_id": entry.get("id"), "detail": res.text})
            else:
                created += 1

    return {"created": created, "failed": failed}
