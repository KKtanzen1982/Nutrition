"""
飲食管理系統 - Block 2 & 3 完整測試

運行方式:
    python test_all_blocks.py
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

def test_users():
    """測試用戶管理"""
    print_section("Block 2: 用戶管理測試")
    
    # 創建用戶
    print("🧪 創建測試用戶")
    user_data = {
        "name": "測試用戶",
        "gender": "女",
        "age": 28,
        "height_cm": 165,
        "primary_goal": "減脂",
        "activity_level": "中度"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/users", json=user_data, timeout=5)
        if response.status_code == 201:
            user = response.json()
            print_success(f"用戶創建成功 (ID: {user['id']})")
            return user['id']
        else:
            print_error(f"創建失敗: {response.status_code}")
            return None
    except Exception as e:
        print_error(f"異常: {str(e)}")
        return None

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
        "details": [
            {
                "exercise_name": "胸部推舉",
                "sets": 4,
                "reps": "10-8-6-4",
                "weight_kg": 60.0
            }
        ]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/exercise-sessions", json=exercise_data, timeout=5)
        if response.status_code == 201:
            session = response.json()
            print_success(f"運動會話新增成功 (ID: {session['id']})")
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
        "step_count": 8500
    }
    
    try:
        response = requests.post(f"{BASE_URL}/daily-steps", json=steps_data, timeout=5)
        if response.status_code == 201:
            steps = response.json()
            print_success(f"步數記錄新增成功 (ID: {steps['id']})")
        else:
            print_error(f"新增失敗: {response.status_code}")
    except Exception as e:
        print_error(f"異常: {str(e)}")

def main():
    print(f"\n{YELLOW}飲食管理系統 - Block 2 & 3 完整測試{RESET}\n")
    
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
    
    # 運行測試
    user_id = test_users()
    test_weight(user_id)
    test_exercise(user_id)
    test_steps(user_id)
    
    print_section("✨ 所有測試完成 ✨")
    print_success("所有功能測試已完成！")

if __name__ == "__main__":
    main()
