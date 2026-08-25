"""
BLOCK_5: 共用的非同步任務暫存區

BLOCK_5_meal_plan_api.py（生成推薦）和 BLOCK_5_adjustment_api.py（方案 B 重推整天）
都會建立 job 並透過 GET /meal-plans/jobs/{job_id}/status 查詢，
所以兩邊必須用同一個字典，否則其中一邊建立的 job 永遠查不到（會回 404）。

開發用；生產環境應該換成資料庫或 Celery/Redis。
"""

jobs_cache: dict = {}
