"""
BLOCK_4: 快速測試和使用範例
============================

此腳本演示如何使用區塊 4 的各個 API 端點。
需要先啟動 FastAPI 服務器：
  python app_main.py

然後運行此測試腳本：
  python BLOCK_4_TEST_EXAMPLES.py
"""

import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000/api"


class Block4Tester:
    """區塊 4 API 測試工具"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}
        self.created_ingredient_ids = []
        self.created_recipe_ids = []

    def print_response(self, title: str, response: requests.Response, show_body: bool = True):
        """打印 HTTP 回應"""
        print(f"\n{'='*60}")
        print(f"📌 {title}")
        print(f"{'='*60}")
        print(f"狀態碼: {response.status_code}")
        if show_body and response.text:
            try:
                print("回應:")
                print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            except:
                print("回應:")
                print(response.text)

    # ============================================================
    # 食材管理測試
    # ============================================================

    def test_create_ingredients(self):
        """建立測試食材"""
        print("\n\n" + "🔴" * 30)
        print("START: 食材管理測試")
        print("🔴" * 30)

        ingredients = [
            {
                "ingredient_name": "雞胸肉",
                "category": "肉類",
                "unit": "g",
                "calories_per_100g": 165.0,
                "protein_per_100g": 31.0,
                "carbs_per_100g": 0.0,
                "fat_per_100g": 3.6,
                "fiber_per_100g": 0.0,
                "needs_stock_tracking": True
            },
            {
                "ingredient_name": "番茄",
                "category": "蔬菜",
                "unit": "g",
                "calories_per_100g": 18.0,
                "protein_per_100g": 0.9,
                "carbs_per_100g": 3.9,
                "fat_per_100g": 0.2,
                "fiber_per_100g": 1.2,
                "needs_stock_tracking": True
            },
            {
                "ingredient_name": "義大利麵",
                "category": "穀物",
                "unit": "g",
                "calories_per_100g": 370.0,
                "protein_per_100g": 13.0,
                "carbs_per_100g": 75.0,
                "fat_per_100g": 1.1,
                "fiber_per_100g": 3.0,
                "needs_stock_tracking": True
            },
            {
                "ingredient_name": "橄欖油",
                "category": "調味料",
                "unit": "ml",
                "calories_per_100g": 884.0,
                "protein_per_100g": 0.0,
                "carbs_per_100g": 0.0,
                "fat_per_100g": 100.0,
                "fiber_per_100g": 0.0,
                "needs_stock_tracking": False  # 調味料不追蹤
            }
        ]

        for ingredient in ingredients:
            try:
                response = requests.post(
                    f"{self.base_url}/ingredients",
                    json=ingredient,
                    headers=self.headers
                )
                self.print_response(f"建立食材: {ingredient['ingredient_name']}", response, show_body=False)
                if response.status_code == 201:
                    self.created_ingredient_ids.append(response.json()["id"])
                    print(f"✅ 食材 ID: {response.json()['id']}")
            except Exception as e:
                print(f"❌ 錯誤: {e}")

    def test_search_ingredients(self):
        """搜尋食材"""
        print("\n" + "⭐" * 30)
        print("搜尋食材")
        try:
            response = requests.get(
                f"{self.base_url}/ingredients/search?query=雞",
                headers=self.headers
            )
            self.print_response("搜尋食材: 雞", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_list_ingredients(self):
        """列表食材"""
        try:
            response = requests.get(
                f"{self.base_url}/ingredients?category=蔬菜&page=1&limit=10",
                headers=self.headers
            )
            self.print_response("列表食材 (分類: 蔬菜)", response, show_body=False)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 找到 {data['total']} 個食材")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_update_ingredient_stock(self):
        """更新食材庫存"""
        if not self.created_ingredient_ids:
            print("⚠️ 沒有建立的食材，跳過此測試")
            return

        ingredient_id = self.created_ingredient_ids[0]
        print(f"\n⭐ 更新食材庫存 (ID: {ingredient_id})")

        stock_data = {
            "current_quantity_g": 500.0,
            "min_threshold_g": 200.0
        }

        try:
            response = requests.put(
                f"{self.base_url}/ingredients/{ingredient_id}/stock",
                json=stock_data,
                headers=self.headers
            )
            self.print_response("更新庫存", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_get_low_stock_ingredients(self):
        """取得低庫存食材"""
        print("\n⭐ 取得低庫存食材")
        try:
            response = requests.get(
                f"{self.base_url}/ingredients/low-stock",
                headers=self.headers
            )
            self.print_response("低庫存食材", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    # ============================================================
    # 食譜管理測試
    # ============================================================

    def test_create_recipe(self):
        """建立測試食譜"""
        print("\n\n" + "🟢" * 30)
        print("START: 食譜管理測試")
        print("🟢" * 30)

        if len(self.created_ingredient_ids) < 3:
            print("⚠️ 需要至少 3 個食材才能建立食譜，請先運行 test_create_ingredients()")
            return

        recipe_data = {
            "recipe_name": "番茄雞肉義大利麵",
            "category": "主食",
            "base_weight_g": 400,
            "cost_level": "低",
            "ingredients": [
                {
                    "ingredient_id": self.created_ingredient_ids[0],  # 雞胸肉
                    "quantity_g": 150,
                    "unit": "g",
                    "notes": "切成小塊"
                },
                {
                    "ingredient_id": self.created_ingredient_ids[1],  # 番茄
                    "quantity_g": 200,
                    "unit": "g",
                    "notes": "新鮮番茄"
                },
                {
                    "ingredient_id": self.created_ingredient_ids[2],  # 義大利麵
                    "quantity_g": 80,
                    "unit": "g",
                    "notes": "未煮"
                }
            ],
            "steps": [
                {
                    "step_number": 1,
                    "step_description": "將義大利麵煮至 al dente（約 8-10 分鐘）"
                },
                {
                    "step_number": 2,
                    "step_description": "雞胸肉切塊，用橄欖油快炒至半熟"
                },
                {
                    "step_number": 3,
                    "step_description": "加入新鮮番茄塊，炒 2-3 分鐘"
                },
                {
                    "step_number": 4,
                    "step_description": "將煮好的麵加入，混合均勻即可盛盤"
                }
            ]
        }

        print("\n⭐ 建立食譜")
        try:
            response = requests.post(
                f"{self.base_url}/recipes",
                json=recipe_data,
                headers=self.headers
            )
            self.print_response("建立食譜: 番茄雞肉義大利麵", response, show_body=False)
            if response.status_code == 201:
                recipe = response.json()
                self.created_recipe_ids.append(recipe["id"])
                print(f"✅ 食譜 ID: {recipe['id']}")
                print(f"✅ 自動計算的營養素:")
                print(f"   - 熱量: {recipe['nutrition']['total_calories_kcal']} kcal")
                print(f"   - 蛋白質: {recipe['nutrition']['protein_g']} g")
                print(f"   - 碳水: {recipe['nutrition']['carbs_g']} g")
                print(f"   - 脂肪: {recipe['nutrition']['fat_g']} g")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_get_recipe(self):
        """取得食譜詳情"""
        if not self.created_recipe_ids:
            print("⚠️ 沒有建立的食譜，跳過此測試")
            return

        recipe_id = self.created_recipe_ids[0]
        print(f"\n⭐ 取得食譜詳情 (ID: {recipe_id})")

        try:
            response = requests.get(
                f"{self.base_url}/recipes/{recipe_id}",
                headers=self.headers
            )
            self.print_response("食譜詳情", response, show_body=False)
            if response.status_code == 200:
                recipe = response.json()
                print(f"✅ 食譜: {recipe['recipe_name']}")
                print(f"✅ 食材數: {len(recipe['ingredients'])}")
                print(f"✅ 步驟數: {len(recipe['steps'])}")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_search_recipes(self):
        """搜尋食譜"""
        print("\n⭐ 搜尋食譜 (名稱: 番茄)")
        try:
            response = requests.get(
                f"{self.base_url}/recipes/search?query=番茄&search_by=name",
                headers=self.headers
            )
            self.print_response("搜尋食譜", response, show_body=False)
            if response.status_code == 200:
                recipes = response.json()
                print(f"✅ 找到 {len(recipes)} 個食譜")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_get_recipe_nutrition(self):
        """取得食譜營養素"""
        if not self.created_recipe_ids:
            print("⚠️ 沒有建立的食譜，跳過此測試")
            return

        recipe_id = self.created_recipe_ids[0]
        print(f"\n⭐ 取得食譜營養素 (ID: {recipe_id})")

        try:
            response = requests.get(
                f"{self.base_url}/recipes/{recipe_id}/nutrition",
                headers=self.headers
            )
            self.print_response("食譜營養素", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_get_recipe_steps(self):
        """取得食譜步驟"""
        if not self.created_recipe_ids:
            print("⚠️ 沒有建立的食譜，跳過此測試")
            return

        recipe_id = self.created_recipe_ids[0]
        print(f"\n⭐ 取得食譜步驟 (ID: {recipe_id})")

        try:
            response = requests.get(
                f"{self.base_url}/recipes/{recipe_id}/steps",
                headers=self.headers
            )
            self.print_response("食譜步驟", response, show_body=False)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 版本: {data['version']}")
                print(f"✅ 步驟數: {len(data['steps'])}")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    def test_add_recipe_steps_version(self):
        """新增食譜步驟新版本"""
        if not self.created_recipe_ids:
            print("⚠️ 沒有建立的食譜，跳過此測試")
            return

        recipe_id = self.created_recipe_ids[0]
        print(f"\n⭐ 新增食譜步驟新版本 (ID: {recipe_id})")

        new_steps = [
            {
                "step_number": 1,
                "step_description": "將義大利麵煮至 al dente（約 9-11 分鐘）"
            },
            {
                "step_number": 2,
                "step_description": "雞胸肉切塊，用橄欖油快炒至全熟"
            },
            {
                "step_number": 3,
                "step_description": "加入新鮮番茄塊和蒜末，炒 3 分鐘"
            },
            {
                "step_number": 4,
                "step_description": "將煮好的麵加入，混合均勻，加鹽調味"
            }
        ]

        try:
            response = requests.post(
                f"{self.base_url}/recipes/{recipe_id}/steps",
                json=new_steps,
                headers=self.headers
            )
            self.print_response("新增步驟新版本", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    # ============================================================
    # 購買地點測試
    # ============================================================

    def test_create_purchase_locations(self):
        """建立購買地點"""
        print("\n\n" + "🔵" * 30)
        print("START: 購買地點管理測試")
        print("🔵" * 30)

        locations = [
            {
                "location_name": "全聯超市",
                "description": "離家最近的超市",
                "priority_order": 1
            },
            {
                "location_name": "家樂福",
                "description": "大型賣場",
                "priority_order": 2
            },
            {
                "location_name": "傳統菜市場",
                "description": "新鮮蔬菜肉類",
                "priority_order": 3
            }
        ]

        print("\n⭐ 建立購買地點")
        for location in locations:
            try:
                response = requests.post(
                    f"{self.base_url}/purchase-locations",
                    json=location,
                    headers=self.headers
                )
                self.print_response(f"建立地點: {location['location_name']}", response, show_body=False)
                if response.status_code == 201:
                    print(f"✅ 地點 ID: {response.json()['id']}")
            except Exception as e:
                print(f"❌ 錯誤: {e}")

    def test_list_purchase_locations(self):
        """列表購買地點"""
        print("\n⭐ 列表購買地點")
        try:
            response = requests.get(
                f"{self.base_url}/purchase-locations",
                headers=self.headers
            )
            self.print_response("購買地點列表", response, show_body=False)
            if response.status_code == 200:
                locations = response.json()
                print(f"✅ 找到 {len(locations)} 個地點")
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    # ============================================================
    # 健康檢查
    # ============================================================

    def test_health_check(self):
        """區塊 4 健康檢查"""
        print("\n\n" + "💛" * 30)
        print("健康檢查")
        print("💛" * 30)

        try:
            response = requests.get(
                f"{self.base_url}/health/block4",
                headers=self.headers
            )
            self.print_response("BLOCK_4 狀態", response)
        except Exception as e:
            print(f"❌ 錯誤: {e}")

    # ============================================================
    # 完整測試流程
    # ============================================================

    def run_all_tests(self):
        """運行所有測試"""
        print("🚀 開始區塊 4 完整測試...\n")

        # 健康檢查
        self.test_health_check()

        # 食材測試
        self.test_create_ingredients()
        self.test_search_ingredients()
        self.test_list_ingredients()
        self.test_update_ingredient_stock()
        self.test_get_low_stock_ingredients()

        # 購買地點測試
        self.test_create_purchase_locations()
        self.test_list_purchase_locations()

        # 食譜測試
        self.test_create_recipe()
        self.test_get_recipe()
        self.test_search_recipes()
        self.test_get_recipe_nutrition()
        self.test_get_recipe_steps()
        self.test_add_recipe_steps_version()

        print("\n\n" + "✅" * 30)
        print("所有測試完成！")
        print("✅" * 30)


if __name__ == "__main__":
    print("區塊 4 - 食譜和食材管理 API 測試")
    print("=" * 60)

    tester = Block4Tester()

    try:
        tester.run_all_tests()
    except ConnectionError:
        print("\n❌ 連接錯誤：無法連接到 http://localhost:8000")
        print("請確保 FastAPI 服務器已啟動:")
        print("  python app_main.py")
