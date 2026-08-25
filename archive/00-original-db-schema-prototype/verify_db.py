#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飲食管理系統 - 數據庫驗證腳本
版本: 1.0
功能: 檢查數據庫完整性、統計種子數據、驗證約束
"""

import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

DB_NAME = 'nutrition_system.db'

class DatabaseVerifier:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            print(f"✗ 錯誤: 找不到數據庫文件: {self.db_path}")
            sys.exit(1)
        
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            print(f"✓ 連接數據庫成功: {self.db_path}\n")
        except sqlite3.Error as e:
            print(f"✗ 連接失敗: {e}")
            sys.exit(1)
    
    def verify_tables(self):
        """驗證所有必需的表是否存在"""
        print("=" * 70)
        print("1. 表驗證")
        print("=" * 70)
        
        expected_tables = [
            # 用戶管理
            'users', 'user_goal_history', 'dietary_preferences', 'user_sport_preferences',
            # 體重追蹤
            'weight_records',
            # 運動追蹤
            'exercise_sessions', 'exercise_details', 'exercise_item_library',
            'workout_templates', 'template_details', 'daily_steps', 'yoga_stretch_items',
            # 食材管理
            'ingredient_library', 'ingredient_stock',
            # 食譜管理
            'recipes', 'recipe_ingredients', 'recipe_steps', 'recipe_nutrition',
            # 購買管理
            'purchase_locations', 'ingredient_location_preference',
            # 週推薦和購物
            'weekly_meal_plan', 'daily_meal_detail', 'meal_adjustments',
            'shopping_list', 'shopping_list_items', 'shopping_list_history',
            # 系統
            'schema_version'
        ]
        
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        existing_tables = {row[0] for row in self.cursor.fetchall()}
        
        print(f"預期表數: {len(expected_tables)}")
        print(f"實際表數: {len(existing_tables)}\n")
        
        missing = set(expected_tables) - existing_tables
        extra = existing_tables - set(expected_tables)
        
        if missing:
            print(f"✗ 缺失表({len(missing)}):")
            for table in sorted(missing):
                print(f"  - {table}")
        
        if extra:
            print(f"⚠ 額外表({len(extra)}):")
            for table in sorted(extra):
                print(f"  - {table}")
        
        if not missing:
            print("✓ 所有必需表都已創建")
        
        return len(missing) == 0
    
    def verify_indexes(self):
        """驗證索引"""
        print("\n" + "=" * 70)
        print("2. 索引驗證")
        print("=" * 70)
        
        self.cursor.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY tbl_name"
        )
        indexes = self.cursor.fetchall()
        
        print(f"✓ 索引總數: {len(indexes)}\n")
        
        if indexes:
            index_by_table = defaultdict(list)
            for idx_name, tbl_name in indexes:
                index_by_table[tbl_name].append(idx_name)
            
            for table in sorted(index_by_table.keys()):
                idxs = index_by_table[table]
                print(f"  {table} ({len(idxs)}):")
                for idx in idxs:
                    print(f"    - {idx}")
        
        return True
    
    def verify_views(self):
        """驗證視圖"""
        print("\n" + "=" * 70)
        print("3. 視圖驗證")
        print("=" * 70)
        
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"
        )
        views = {row[0] for row in self.cursor.fetchall()}
        
        expected_views = {
            'user_latest_weight',
            'recipe_complete_info',
            'low_stock_ingredients'
        }
        
        print(f"預期視圖數: {len(expected_views)}")
        print(f"實際視圖數: {len(views)}\n")
        
        missing = expected_views - views
        if missing:
            print(f"✗ 缺失視圖:")
            for view in sorted(missing):
                print(f"  - {view}")
        else:
            print("✓ 所有視圖都已創建")
            for view in sorted(views):
                print(f"  - {view}")
        
        return len(missing) == 0
    
    def count_seed_data(self):
        """統計種子數據"""
        print("\n" + "=" * 70)
        print("4. 種子數據統計")
        print("=" * 70)
        
        stats = {}
        
        tables_to_count = [
            ('ingredient_library', '食材庫'),
            ('ingredient_stock', '食材庫存'),
            ('exercise_item_library', '訓練項目庫'),
            ('yoga_stretch_items', '瑜珈/拉伸項目庫'),
            ('purchase_locations', '購買地點庫'),
            ('recipes', '食譜庫'),
            ('recipe_steps', '食譜步驟'),
            ('users', '用戶'),
            ('weight_records', '體重記錄'),
            ('exercise_sessions', '運動會話'),
        ]
        
        for table, label in tables_to_count:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            stats[label] = count
            print(f"  {label}: {count}")
        
        return stats
    
    def verify_constraints(self):
        """驗證約束"""
        print("\n" + "=" * 70)
        print("5. 約束驗證")
        print("=" * 70)
        
        # 獲取表信息
        self.cursor.execute("PRAGMA foreign_keys=ON")
        
        constraints_ok = True
        
        # 檢查幾個關鍵的外鍵約束
        test_tables = [
            ('user_goal_history', 'user_id', 'users'),
            ('dietary_preferences', 'user_id', 'users'),
            ('weight_records', 'user_id', 'users'),
            ('exercise_sessions', 'user_id', 'users'),
            ('ingredient_stock', 'ingredient_id', 'ingredient_library'),
        ]
        
        print("檢查外鍵約束:")
        for table, fk_col, ref_table in test_tables:
            self.cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = self.cursor.fetchall()
            found = any(fk[4] == ref_table for fk in fks)
            status = "✓" if found else "✗"
            print(f"  {status} {table}.{fk_col} → {ref_table}")
            if not found:
                constraints_ok = False
        
        return constraints_ok
    
    def verify_schema_version(self):
        """驗證架構版本記錄"""
        print("\n" + "=" * 70)
        print("6. 架構版本")
        print("=" * 70)
        
        self.cursor.execute("SELECT * FROM schema_version ORDER BY created_at DESC LIMIT 1")
        version = self.cursor.fetchone()
        
        if version:
            print(f"✓ 版本: {version['version_number']}")
            print(f"  描述: {version['description']}")
            print(f"  創建於: {version['created_at']}")
            if version['applied_at']:
                print(f"  應用於: {version['applied_at']}")
            return True
        else:
            print("✗ 未找到版本信息")
            return False
    
    def verify_ingredient_details(self):
        """驗證食材營養信息"""
        print("\n" + "=" * 70)
        print("7. 食材詳細驗證")
        print("=" * 70)
        
        self.cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM ingredient_library
            GROUP BY category
            ORDER BY count DESC
        """)
        
        print("食材按分類分佈:")
        total = 0
        for row in self.cursor.fetchall():
            category, count = row
            print(f"  {category}: {count}")
            total += count
        
        print(f"\n總計: {total} 個食材")
        
        # 檢查營養信息完整性
        self.cursor.execute("""
            SELECT COUNT(*) FROM ingredient_library
            WHERE calories_per_100g IS NOT NULL
            AND protein_per_100g IS NOT NULL
            AND carbs_per_100g IS NOT NULL
            AND fat_per_100g IS NOT NULL
        """)
        
        complete_nutrition = self.cursor.fetchone()[0]
        print(f"✓ 營養信息完整的食材: {complete_nutrition}/{total}")
        
        return True
    
    def run_all_checks(self):
        """運行所有檢查"""
        print("\n" + "=" * 70)
        print("飲食管理系統 - 數據庫完整性驗證")
        print("=" * 70 + "\n")
        
        results = []
        
        results.append(("表驗證", self.verify_tables()))
        results.append(("索引驗證", self.verify_indexes()))
        results.append(("視圖驗證", self.verify_views()))
        self.count_seed_data()
        results.append(("約束驗證", self.verify_constraints()))
        results.append(("版本驗證", self.verify_schema_version()))
        self.verify_ingredient_details()
        
        # 生成報告
        print("\n" + "=" * 70)
        print("驗證報告")
        print("=" * 70)
        
        for check_name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"{status}: {check_name}")
        
        all_passed = all(passed for _, passed in results)
        
        print("\n" + "=" * 70)
        if all_passed:
            print("✓ 所有驗證通過！數據庫準備就緒。")
        else:
            print("✗ 部分驗證失敗，請檢查數據庫設置。")
        print("=" * 70 + "\n")
        
        self.conn.close()
        return all_passed
    
    def generate_summary(self):
        """生成數據庫摘要"""
        print("\n" + "=" * 70)
        print("數據庫摘要")
        print("=" * 70 + "\n")
        
        # 表統計
        self.cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
        table_count = self.cursor.fetchone()[0]
        
        # 索引統計
        self.cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
        index_count = self.cursor.fetchone()[0]
        
        # 視圖統計
        self.cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='view'")
        view_count = self.cursor.fetchone()[0]
        
        print(f"📊 數據庫結構:")
        print(f"  - 表: {table_count}")
        print(f"  - 索引: {index_count}")
        print(f"  - 視圖: {view_count}")
        
        # 數據統計
        self.cursor.execute("SELECT COUNT(*) FROM ingredient_library")
        ingredient_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM exercise_item_library")
        exercise_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM yoga_stretch_items")
        yoga_count = self.cursor.fetchone()[0]
        
        self.cursor.execute("SELECT COUNT(*) FROM purchase_locations")
        location_count = self.cursor.fetchone()[0]
        
        print(f"\n📦 種子數據:")
        print(f"  - 食材: {ingredient_count}")
        print(f"  - 訓練項目: {exercise_count}")
        print(f"  - 瑜珈/拉伸項目: {yoga_count}")
        print(f"  - 購買地點: {location_count}")
        
        print(f"\n✓ 數據庫文件: {self.db_path.absolute()}")
        print(f"✓ 文件大小: {self.db_path.stat().st_size / 1024:.2f} KB")
        
        self.conn.close()

def main():
    verifier = DatabaseVerifier(DB_NAME)
    success = verifier.run_all_checks()
    verifier.generate_summary()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
