export interface UserProfile {
  id: number
  name: string
  gender: string
  age: number
  height_cm: number
  primary_goal: string
  activity_level: string
  email?: string | null
  phone?: string | null
  notes?: string | null
  last_menstrual_date?: string | null
  menstrual_cycle_length_days?: number | null
  menstrual_cycle_irregular?: boolean
  menstrual_luteal_phase_start_offset_days?: number
  menstrual_luteal_phase_adjustment_calories?: number
  menstrual_premenstrual_adjustment_calories?: number
  manual_calories_target?: number | null
}

export type UpdateUserPayload = Partial<Omit<UserProfile, 'id'>>

export interface NutritionTargets {
  user_id: number
  bmr: number
  tdee: number
  goal_adjusted_calories: number
  menstrual_phase: string
  menstrual_adjusted_calories: number
  manual_override: boolean
  daily_calories_target: number
  daily_protein_g: number
  protein_g: number
  carbs_g: number
  fat_g: number
}

export interface DietaryPreference {
  user_id: number
  allergies?: string | null
  restrictions?: string | null
  preferences?: string | null
}

export type UpdateDietaryPreferencePayload = Partial<Omit<DietaryPreference, 'user_id'>>

export interface WeightGoal {
  user_id: number
  target_weight_kg: number | null
  target_date: string | null
  active_daily_deficit_kcal: number | null
  deficit_calculated_at: string | null
  deficit_calculated_weight_kg: number | null
}

export interface UpdateWeightGoalPayload {
  target_weight_kg?: number | null
  target_date?: string | null
}

export interface GoalHistoryEntry {
  goal_type: string
  target_value: number
  previous_value: number | null
  set_date: string
  achieved: boolean | null
  achievement_date: string | null
}

export interface WeightRecord {
  id: number
  date: string
  weight_kg: number
  body_fat_percent: number | null
  notes: string | null
}

export interface CreateWeightRecordPayload {
  user_id: number
  date: string
  weight_kg: number
  body_fat_percent?: number | null
  notes?: string | null
}

export type UpdateWeightRecordPayload = Partial<Omit<CreateWeightRecordPayload, 'user_id' | 'date'>>

export interface ExerciseDetail {
  exercise_name: string
  sets: number | null
  reps: string | null
  weight_kg: number | null
  duration_min?: number | null
  notes: string | null
  exercise_item_id?: number | null
  yoga_stretch_item_id?: number | null
}

export interface ExerciseSession {
  id: number
  date: string
  exercise_type: string
  duration_min: number | null
  intensity: string | null
  calories_burned?: number | null
  notes?: string | null
  details?: ExerciseDetail[]
}

export interface CreateExerciseDetailPayload {
  exercise_name: string
  sets?: number | null
  reps?: string | null
  weight_kg?: number | null
  duration_min?: number | null
  exercise_item_id?: number | null
  yoga_stretch_item_id?: number | null
}

export interface CreateExerciseSessionPayload {
  user_id: number
  date: string
  exercise_type: string
  duration_min: number
  notes?: string | null
  details?: CreateExerciseDetailPayload[]
}

export interface UpdateExerciseSessionPayload {
  date?: string
  exercise_type?: string
  duration_min?: number
  notes?: string | null
  details?: CreateExerciseDetailPayload[]
}

export interface WorkoutTemplateDetail {
  id: number
  template_id: number
  exercise_name: string
  sets: number | null
  reps: string | null
  weight_kg: number | null
  duration_min?: number | null
  notes: string | null
  order: number
  exercise_item_id?: number | null
  yoga_stretch_item_id?: number | null
}

export interface WorkoutTemplate {
  id: number
  user_id: number
  template_name: string
  description: string | null
  exercise_type: string
  duration_min: number | null
  details: WorkoutTemplateDetail[]
  created_at: string
  updated_at: string
}

export interface CreateWorkoutTemplateDetailPayload {
  exercise_name: string
  sets?: number | null
  reps?: string | null
  weight_kg?: number | null
  duration_min?: number | null
  exercise_item_id?: number | null
  yoga_stretch_item_id?: number | null
}

export interface CreateWorkoutTemplatePayload {
  user_id: number
  template_name: string
  description?: string | null
  exercise_type: string
  duration_min?: number | null
  details?: CreateWorkoutTemplateDetailPayload[]
}

export interface UpdateWorkoutTemplatePayload {
  template_name?: string
  description?: string | null
  exercise_type?: string
  duration_min?: number | null
  details?: CreateWorkoutTemplateDetailPayload[]
}

// ==================== 訓練計畫 + 月曆排程 (BLOCK_8 子系統二) ====================

export interface TrainingProgramDay {
  id: number
  program_id: number
  day_number: number
  day_label: string | null
  workout_template_id: number
  template: WorkoutTemplate
}

export interface TrainingProgram {
  id: number
  user_id: number
  program_name: string
  day_count: number
  description: string | null
  created_at: string
  days: TrainingProgramDay[]
}

export interface CreateTrainingProgramDayPayload {
  day_number: number
  day_label?: string | null
  exercise_type: string
  duration_min?: number | null
  details?: CreateWorkoutTemplateDetailPayload[]
}

export interface CreateTrainingProgramPayload {
  user_id: number
  program_name: string
  description?: string | null
  days: CreateTrainingProgramDayPayload[]
}

export interface TrainingScheduleEntry {
  id: number
  user_id: number
  program_day_id: number
  scheduled_date: string
  status: '已排程' | '已完成' | '已跳過'
  actual_exercise_session_id: number | null
  volume_adjustment_pct: number | null
  day_label: string | null
  workout_template_id: number
  program_id: number
  program_name: string
}

export interface CreateTrainingSchedulePayload {
  program_day_id: number
  scheduled_date: string
}

export interface UpdateTrainingSchedulePayload {
  scheduled_date?: string
  status?: '已排程' | '已完成' | '已跳過'
}

export interface TrainingTarget {
  category: string
  weekly_target_count: number
}

export interface CategoryProgress {
  category: string
  actual_count: number
  target_count: number
  met: boolean
  this_week_volume?: number
  last_week_volume?: number
  volume_met?: boolean
}

export interface WeeklyProgress {
  week_start: string
  week_end: string
  categories: CategoryProgress[]
}

export interface DailyStepsRecord {
  id: number
  date: string
  step_count: number
  notes: string | null
}

export interface CreateDailyStepsPayload {
  user_id: number
  date: string
  step_count: number
  notes?: string | null
}

export interface UpdateDailyStepsPayload {
  step_count?: number
  notes?: string | null
}

export type MealType = 'breakfast' | 'lunch' | 'afternoon_snack' | 'dinner'

export interface MealDetail {
  id: number
  meal_type: MealType
  assigned_user_id: number
  recipe_id: number
  recipe_name: string
  recipe_category?: string | null
  serving_weight_g: number
  calories: number
  protein_g: number
  carbs_g: number
  fat_g: number
  fiber_g?: number | null
}

export interface DayMeals {
  date: string
  meals: MealDetail[]
}

export interface MealPlanDetail {
  id: number
  plan_date: string
  user_id_a: number
  user_id_b: number
  user_a_daily_calories_target: number
  user_b_daily_calories_target: number
  user_a_menstrual_phase: string
  user_b_menstrual_phase: string
  plan_status: string
  days: DayMeals[]
}

export type FixedMealType = 'breakfast' | 'afternoon_snack'

export interface FixedMealPreference {
  id: number
  user_id: number
  meal_type: FixedMealType
  recipe_id: number
  recipe_name: string | null
}

export interface ExcludedRecipe {
  id: number
  recipe_id: number
  recipe_name: string | null
}

export interface FavoriteRecipe {
  id: number
  user_id: number
  recipe_id: number
  recipe_name: string | null
}

export interface SoupDayPreference {
  days: number[] // 0=週一...6=週日
}

export interface PrepDish {
  recipe_id: number
  recipe_name: string
  total_weight_g: number
  servings: number
}

export interface BentoPrepSession {
  prep_date: string
  for_dates: string[]
  rice_dishes: PrepDish[]
  rice_cups_to_cook: number
  rice_cook_batches: number[]
  other_staple_dishes: PrepDish[]
  veg_dishes: PrepDish[]
  steps: string[]
  meat_batch?: PrepDish[] | null
}

export interface PrepDayMeal {
  cook_fresh: PrepDish[]
  reheat_from_batch: PrepDish[]
}

export interface PrepDayCard {
  date: string
  weekday_label: string
  prep_session: BentoPrepSession | null
  dinner: PrepDayMeal | null
  lunch_fresh: PrepDayMeal | null
  lunch_is_bento: boolean
}

export interface PrepPlan {
  week_start_date: string
  rice_cup_assumption_g: number
  days: PrepDayCard[]
}

export interface AddDishPayload {
  meal_date: string
  meal_type: MealType
  recipe_id: number
  user_id?: number | null
}

export interface RebalanceDayPayload {
  meal_date: string
}

export interface GenerateMealPlanPayload {
  week_start_date: string
  user_id_a: number
  user_id_b: number
}

export interface ReplaceMealPayload {
  meal_id: number
  new_recipe_id: number
}

export interface RegenerateDayPayload {
  meal_date: string
}

export interface SearchAndReplacePayload {
  meal_id: number
  new_recipe_id: number
  search_query?: string
}

export interface AdjustServingWeightPayload {
  meal_id: number
  new_serving_weight_g: number
}

export interface ConfirmMealPlanResponse {
  success: boolean
  plan_id: number
  shopping_list_id: number
  message?: string
}

export interface RecipeSearchResult {
  id: number
  recipe_name: string
  category: string
  base_weight_g: number
  cost_level: string
  total_calories_kcal?: number | null
  protein_g?: number | null
  carbs_g?: number | null
  fat_g?: number | null
}

export interface ShoppingListItem {
  id: number
  ingredient_id: number
  ingredient_name: string
  quantity_needed_g: number
  unit: string
  purchase_location_id: number | null
  cost_level: string | null
  needs_restocking: boolean
  assigned_user_id: number | null
  notes: string | null
  is_purchased: boolean
  purchased_at: string | null
}

export interface ShoppingListItemGroup {
  category: string
  items: ShoppingListItem[]
}

export interface ShoppingListDetail {
  list_id: number
  status: string
  list_date: string
  week_start_date: string
  created_from_plan_id: number | null
  total_items: number
  items_by_location: Record<string, ShoppingListItemGroup[]>
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CreateShoppingListItemPayload {
  ingredient_id: number
  quantity_needed_g: number
  unit?: string
  purchase_location_id?: number | null
  assigned_user_id?: number | null
  notes?: string | null
}

export type UpdateShoppingListItemPayload = Partial<Omit<CreateShoppingListItemPayload, 'ingredient_id'>>

export interface ShoppingListHistoryEntry {
  id: number
  shopping_list_id: number
  item_changes: string | null
  status_log: string | null
  archived_at: string
  notes: string | null
}

export interface ShoppingListHistoryPage {
  history: ShoppingListHistoryEntry[]
  total: number
}

export interface PaginatedResult<T> {
  total: number
  page: number
  limit: number
  items: T[]
}

export interface IngredientStock {
  id: number
  ingredient_id: number
  current_quantity_g: number
  min_threshold_g: number | null
  unit: string
  last_purchased_at: string | null
  notes: string | null
}

export interface Ingredient {
  id: number
  ingredient_name: string
  category: string
  unit: string
  calories_per_100g: number | null
  protein_per_100g: number | null
  carbs_per_100g: number | null
  fat_per_100g: number | null
  fiber_per_100g: number | null
  preferred_purchase_location: string | null
  needs_stock_tracking: boolean
  created_at: string
  stock: IngredientStock | null
}

export interface IngredientSearchResult {
  id: number
  ingredient_name: string
  category: string
  unit: string
  calories_per_100g: number | null
  protein_per_100g: number | null
  carbs_per_100g: number | null
  fat_per_100g: number | null
  fiber_per_100g: number | null
  needs_stock_tracking: boolean
}

export interface LowStockIngredient {
  ingredient_id: number
  ingredient_name: string
  category: string
  current_quantity_g: number
  min_threshold_g: number
  unit: string
  last_purchased_at: string | null
  deficit_g: number
}

export interface CreateIngredientPayload {
  ingredient_name: string
  category: string
  unit?: string
  calories_per_100g?: number | null
  protein_per_100g?: number | null
  carbs_per_100g?: number | null
  fat_per_100g?: number | null
  fiber_per_100g?: number | null
  preferred_purchase_location?: string | null
  needs_stock_tracking?: boolean
}

export type UpdateIngredientPayload = Partial<CreateIngredientPayload>

export interface UpdateIngredientStockPayload {
  current_quantity_g?: number
  min_threshold_g?: number | null
  unit?: string
  notes?: string | null
}

export interface RecipeIngredientEntry {
  id: number
  recipe_id: number
  ingredient_id: number
  quantity_g: number
  unit: string
  notes: string | null
  ingredient: IngredientSearchResult | null
}

export interface RecipeStep {
  id: number
  recipe_id: number
  version: number
  step_number: number
  step_description: string
  is_current: boolean
  created_at: string
}

export interface RecipeNutrition {
  id: number
  recipe_id: number
  total_calories_kcal: number | null
  protein_g: number | null
  carbs_g: number | null
  fat_g: number | null
  fiber_g: number | null
  calculated_at: string
}

export interface RecipeDetail {
  id: number
  recipe_name: string
  category: string
  base_weight_g: number
  cost_level: string
  is_active: boolean
  created_at: string
  last_updated_at: string
  ingredients: RecipeIngredientEntry[]
  steps: RecipeStep[]
  nutrition: RecipeNutrition | null
}

export interface RecipeListEntry {
  id: number
  recipe_name: string
  category: string
  base_weight_g: number
  cost_level: string
  is_active: boolean
  created_at: string
  nutrition: RecipeNutrition | null
}

export interface CreateRecipeIngredientPayload {
  ingredient_id: number
  quantity_g: number
  unit?: string
  notes?: string | null
}

export interface CreateRecipeStepPayload {
  step_number: number
  step_description: string
}

export interface CreateRecipePayload {
  recipe_name: string
  category: string
  base_weight_g: number
  cost_level: string
  ingredients: CreateRecipeIngredientPayload[]
  steps: CreateRecipeStepPayload[]
}

export interface UpdateRecipePayload {
  recipe_name?: string
  category?: string
  base_weight_g?: number
  cost_level?: string
  is_active?: boolean
}

export interface PurchaseLocation {
  id: number
  location_name: string
  description: string | null
  priority_order: number
  is_active: boolean
}

export interface CreatePurchaseLocationPayload {
  location_name: string
  description?: string | null
  priority_order?: number
}

export type UpdatePurchaseLocationPayload = Partial<CreatePurchaseLocationPayload> & { is_active?: boolean }

export interface IngredientLocationPreference {
  id: number
  ingredient_id: number
  preferred_location_id: number
  location_name: string
  priority: number
  notes: string | null
}

export interface IngredientLocationPreferenceItem {
  preferred_location_id: number
  priority: number
  notes?: string | null
}

export interface SetIngredientLocationPreferencePayload {
  preferences: IngredientLocationPreferenceItem[]
}

export type ExerciseItemType = 'gym' | 'yoga_stretch'

export interface ExerciseLibraryItem {
  id: number
  item_name: string
  category: string
  muscle_group: string | null
  equipment: string | null
  default_sets: number | null
  default_reps: string | null
  description: string | null
  is_active: boolean
}

export interface YogaStretchLibraryItem {
  id: number
  item_name: string
  type: string
  duration_min: number | null
  difficulty: string | null
  description: string | null
}

export type ExerciseItemLibraryEntry = ExerciseLibraryItem | YogaStretchLibraryItem

export interface UpdateExerciseLibraryItemPayload {
  category?: string
  muscle_group?: string | null
  equipment?: string | null
  default_sets?: number | null
  default_reps?: string | null
  duration_min?: number | null
  difficulty?: string | null
  description?: string | null
}

export interface ExerciseItemVolumePoint {
  date: string
  volume: number
}

export interface CreateExerciseLibraryItemPayload {
  type: ExerciseItemType
  item_name: string
  description?: string | null
  category?: string
  muscle_group?: string | null
  equipment?: string | null
  default_sets?: number | null
  default_reps?: string | null
  yoga_type?: string
  duration_min?: number | null
  difficulty?: string | null
}

export interface NutritionCalculationResult {
  recipe_id: number
  recipe_name: string
  base_weight_g: number
  total_calories_kcal: number
  protein_g: number
  carbs_g: number
  fat_g: number
  fiber_g: number
  calculated_at: string
}
