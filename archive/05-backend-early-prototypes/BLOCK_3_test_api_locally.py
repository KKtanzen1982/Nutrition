"""
Block 3: 體重和運動追蹤 - 完整測試腳本

運行方式:
    python BLOCK_3_test_api_locally.py
"""

import requests
from datetime import date

BASE_URL = "http://127.0.0.1:8000/api/v1"

# 颜色代码
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}❌ {msg}{RESET}")

def print_section(title):
    print(f"\n{YELLOW}{'='*70}{RESET}")
    print(f"{YELLOW}{title:^70}{RESET}")
    print(f"{YELLOW}{'='*70}{RESET}\n")

def test_weight(user_id):
    """測試體重管理"""
    print_section("Block 3: 體重管理測試")
    
    if not user_id:
        print_error("缺少用戶ID")
        return
    
    print("🧪 記錄體重")
    weight_data = {
        "user_id": user_id,
        "date": date.today().isoformat(),
        "weight_kg": 58.5,
        "body_fat_percent": 22.5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/weight-records", json=weight_data, timeout=5)
        if response.status_code == 201:
            record = response.json()
            print_success(f"體重記錄新增成功 (ID: {record['id']})")
            print(f"  體重: {record['weight_kg']} kg")
            print(f"  體脂: {record['body_fat_percent']}%")
        else:
            print_error(f"新增失敗: {response.status_code}")
    except Exception as e:
        print_error(f"異常: {str(e)}")

def test_exercise(user_id):
    """測試運動管理"""
    print_section("Block 3: 運動管理測試")
    
    if not user_id:
        print_error("缺少用戶ID")
        return
    
    print("🧪 創建運動會話")
    exercise_data = {
        "user_id": user_id,
        "date": date.today().isoformat(),
        "exercise_type": "健身房",
        "duration_min": 60,
        "intensity": "高",
        "calories_burned": 500,
        "details": [
            {
                "exercise_name": "胸部推舉",
                "sets": 4,
                "reps": "10-8-6-4",
                "weight_kg": 60.0
            },
            {
                "exercise_name": "肱三頭肌下壓",
                "sets": 3,
                "reps": "10",
                "weight_kg": 40.0
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/exercise-sessions", json=exercise_data, timeout=5)
        if response.status_code == 201:
            session = response.json()
            print_success(f"運動會話新增成功 (ID: {session['id']})")
            print(f"  運動類型: {session['exercise_type']}")
            print(f"  時長: {session['duration_min']} 分鐘")
            print(f"  訓練項目: {len(session['details'])} 個")
        else:
            print_error(f"新增失敗: {response.status_code}")
    except Exception as e:
        print_error(f"異常: {str(e)}")

def test_steps(user_id):
    """測試步數管理"""
    print_section("Block 3: 步數管理測試")
    
    if not user_id:
        print_error("缺少用戶ID")
        return
    
    print("🧪 記錄每日步數")
    steps_data = {
        "user_id": user_id,
        "date": date.today().isoformat(),
        "step_count": 8500,
        "calories_burned": 300.0
    }
    
    try:
        response = requests.post(f"{BASE_URL}/daily-steps", json=steps_data, timeout=5)
        if response.status_code == 201:
            steps = response.json()
            print_success(f"步數記錄新增成功 (ID: {steps['id']})")
            print(f"  步數: {steps['step_count']}")
            print(f"  消耗卡路里: {steps['calories_burned']}")
        else:
            print_error(f"新增失敗: {response.status_code}")
    except Exception as e:
        print_error(f"異常: {str(e)}")

def main():
    print(f"\n{YELLOW}Block 3: 體重和運動追蹤 - 測試{RESET}\n")
    
    # 健康檢查
    print("🧪 API 健康檢查")
    try:
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print_success("API 伺服器正在運行")
        else:
            print_error("API 返回異常狀態碼")
            return
    except:
        print_error("無法連接到 API。請確保應用已啟動")
        return
    
    # 使用現有用戶或創建新用戶
    user_id = 1  # 假設用戶 ID 為 1
    
    # 運行 Block 3 測試
    test_weight(user_id)
    test_exercise(user_id)
    test_steps(user_id)
    
    print_section("✨ Block 3 測試完成 ✨")
    print_success("所有 Block 3 功能測試完成！")

if __name__ == "__main__":
    main()
