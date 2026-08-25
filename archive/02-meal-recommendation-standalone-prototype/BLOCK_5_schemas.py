"""
BLOCK_5: Pydantic 數據模型 - 推薦和微調
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


# ==================== 列舉型別 ====================

class MealType(str, Enum):
    """餐次類型"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    AFTERNOON_SNACK = "afternoon_snack"
    DINNER = "dinner"


class MenstrualPhase(str, Enum):
    """生理期階段"""
    MENSTRUAL = "月經期"
    FOLLICULAR = "卵泡期"
    OVULATION = "排卵期"
    LUTEAL = "黃體期"
    PREMENSTRUAL = "經前期"
    NONE = "無"


class PrimaryGoal(str, Enum):
    """主要目標"""
    FAT_LOSS = "減脂"
    MUSCLE_GAIN = "增肌"
    MAINTENANCE = "維持"


class ActivityLevel(str, Enum):
    """活動等級"""
    SEDENTARY = "久坐"
    LIGHT = "輕度"
    MODERATE = "中度"
    HIGH = "高度"


class AdjustmentType(str, Enum):
    """微調類型"""
    REPLACE = "替換"
    REGENERATE_DAY = "重推整天"
    SEARCH_REPLACE = "搜尋替換"
    ADJUST_WEIGHT = "調整分量"


class JobStatusEnum(str, Enum):
    """非同步任務狀態"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CalorieCalculationMethod(str, Enum):
    """熱量計算公式"""
    HARRIS_BENEDICT = "harris_benedict"
    MIFFLIN_ST_JEOR = "mifflin_st_jeor"


# ==================== 推薦請求模型 ====================

class PreselectedMeal(BaseModel):
    """預選菜色"""
    day: str  # "Monday", "Tuesday", ...
    meal_type: MealType
    recipe_id: int


class GenerateMealPlanRequest(BaseModel):
    """生成週推薦的請求"""
    week_start_date: date
    user_a_id: int
    user_b_id: int
    calorie_calculation_method: CalorieCalculationMethod = CalorieCalculationMethod.HARRIS_BENEDICT
    user_a_preselected: Optional[List[PreselectedMeal]] = Field(default_factory=list)
    user_b_preselected: Optional[List[PreselectedMeal]] = Field(default_factory=list)


# ==================== 推薦回應模型 ====================

class MealDetail(BaseModel):
    """單個餐次詳情"""
    meal_type: MealType
    user_id: int
    user_name: str
    recipe_id: int
    recipe_name: str
    serving_weight_g: int
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None


class DayMeals(BaseModel):
    """某一天的所有餐次"""
    meal_date: date
    day_name: str  # "Monday", ...
    meals: List[MealDetail]
    day_total_calories_a: float
    day_total_calories_b: float
    day_total_protein_a: float
    day_total_protein_b: float


class NutrientSummary(BaseModel):
    """營養素統計"""
    total_calories: float
    avg_calories: float
    total_protein_g: float
    avg_protein_g: float
    total_carbs_g: float
    avg_carbs_g: float
    total_fat_g: float
    avg_fat_g: float
    total_fiber_g: Optional[float] = None


class MealPlanResponse(BaseModel):
    """週推薦的回應"""
    success: bool
    plan_id: Optional[int] = None
    week_start_date: date
    status: str = "draft"
    user_a_id: int
    user_b_id: int
    user_a_daily_calories_target: float
    user_b_daily_calories_target: float
    user_a_menstrual_phase: str
    user_b_menstrual_phase: str
    daily_details: List[DayMeals]
    nutrition_summary: Dict[str, NutrientSummary]
    recommendation_notes: Optional[str] = None
    created_at: Optional[datetime] = None


class GenerateMealPlanImmediateResponse(BaseModel):
    """立即回應（非同步）"""
    success: bool
    job_id: str
    message: str = "推薦任務已啟動，請輪詢查詢狀態"


class JobStatus(BaseModel):
    """非同步任務狀態查詢"""
    job_id: str
    status: str  # 'pending' / 'processing' / 'completed' / 'failed'
    plan_id: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ==================== 微調請求模型 ====================

class ReplaceMealRequest(BaseModel):
    """方案 A：替換單菜色"""
    meal_date: date
    meal_type: MealType
    user_id: int
    new_recipe_id: int
    reason: Optional[str] = "用戶手動替換"


class RegenerateDayRequest(BaseModel):
    """方案 B：重推整天"""
    meal_date: date
    fixed_meals: Optional[List[PreselectedMeal]] = Field(default_factory=list)


class SearchAndReplaceRequest(BaseModel):
    """方案 C：搜尋替換"""
    meal_date: date
    meal_type: MealType
    user_id: int
    search_query: str  # 用戶搜尋的菜色名稱或食材
    new_recipe_id: int


class AdjustServingWeightRequest(BaseModel):
    """方案 D：調整分量"""
    meal_date: date
    meal_type: MealType
    user_id: int
    new_serving_weight_g: int


# ==================== 微調回應模型 ====================

class UpdatedMeal(BaseModel):
    """更新後的餐次"""
    meal_date: date
    meal_type: MealType
    user_id: int
    recipe_id: int
    recipe_name: str
    serving_weight_g: int
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float


class AdjustmentResponse(BaseModel):
    """微調回應"""
    success: bool
    updated_meal: Optional[UpdatedMeal] = None
    job_id: Optional[str] = None  # 方案 B 才有
    adjustment_recorded: bool = True
    message: str = "微調成功"


# ==================== Claude 內部數據模型 ====================

class UserDataForClaude(BaseModel):
    """打包給 Claude 的用戶數據"""
    id: int
    name: str
    gender: str
    age: int
    height_cm: int
    primary_goal: str
    activity_level: str
    menstrual_phase: str
    allergies: str
    restrictions: str
    daily_calories_target: int
    daily_protein_g: int
    daily_carbs_g: int
    daily_fat_g: int
    this_week_exercise: Dict[str, Any]


class RecipeForClaude(BaseModel):
    """打包給 Claude 的食譜數據"""
    id: int
    name: str
    category: str
    base_weight_g: int
    cost_level: str
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: Optional[float] = None
    ingredients: List[str]
    is_vegetarian: bool
    contains_allergens: List[str]


class ClaudeRecommendationRequest(BaseModel):
    """打包給 Claude 的完整推薦請求"""
    analysis_date: str
    week_start_date: str
    user_a: UserDataForClaude
    user_b: UserDataForClaude
    user_a_preselected_meals: List[Dict[str, Any]]
    user_b_preselected_meals: List[Dict[str, Any]]
    recipe_database: List[RecipeForClaude]


class ClaudeMealRecommendation(BaseModel):
    """Claude 推薦的單個餐次"""
    day: str
    meal_type: str
    user: str  # "A" or "B"
    recipe_id: int
    recipe_name: str
    serving_weight_g: int
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    reasoning: Optional[str] = None


class ClaudeRecommendationResponse(BaseModel):
    """Claude 的推薦回應"""
    success: bool
    recommendation: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Optional[str] = None  # Claude 的原始回應


# ==================== 生理期相關模型 ====================

class MenstrualPhaseConfig(BaseModel):
    """用戶的生理期設定"""
    cycle_length_days: Optional[int] = 28
    last_menstrual_date: Optional[date] = None
    is_irregular: bool = False
    luteal_phase_start_offset_days: int = 14  # 黃體期開始的天數
    luteal_phase_adjustment_calories: int = 150  # 黃體期額外熱量
    premenstrual_adjustment_calories: int = 120  # 經前期額外熱量


class MenstrualPhaseRecommendation(BaseModel):
    """生理期飲食建議"""
    phase: str
    key_nutrients: str
    suggested_ingredients: List[str]
    calorie_adjustment: int


# ==================== 錯誤模型 ====================

class ErrorResponse(BaseModel):
    """錯誤回應"""
    success: bool = False
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
