import streamlit as st
import tensorflow as tf
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# =====================================
# 모델 불러오기 (캐싱 처리로 속도 향상)
# =====================================
@st.cache_resource
def load_food_model():
    return tf.keras.models.load_model("food_model.h5")

try:
    model = load_food_model()
except Exception as e:
    st.error(f"모델을 불러오는데 실패했습니다. 파일명을 확인하세요: {e}")

# =====================================
# 세션 초기화
# =====================================
if "total_kcal" not in st.session_state: st.session_state.total_kcal = 0
if "total_protein" not in st.session_state: st.session_state.total_protein = 0
if "total_carb" not in st.session_state: st.session_state.total_carb = 0
if "total_fat" not in st.session_state: st.session_state.total_fat = 0
if "foods" not in st.session_state: st.session_state.foods = []
if "night_count" not in st.session_state: st.session_state.night_count = 0
if "weekly_scores" not in st.session_state: st.session_state.weekly_scores = []
if "weekly_calories" not in st.session_state: st.session_state.weekly_calories = []

# =====================================
# 클래스 이름 및 영양성분 DB (기존과 동일)
# =====================================
class_names = ["bibimbap", "chicken_wings", "donuts", "dumplings", "fried_rice", "hamburger", "ice_cream", "omelette", "pho", "pizza", "ramen", "spaghetti", "sushi", "tacos", "waffles"]
food_info = {
    "bibimbap": {"name": "비빔밥", "kcal": 550, "carb": 80, "protein": 18, "fat": 12},
    "chicken_wings": {"name": "치킨윙", "kcal": 320, "carb": 8, "protein": 24, "fat": 22},
    "donuts": {"name": "도넛", "kcal": 250, "carb": 32, "protein": 3, "fat": 12},
    "dumplings": {"name": "만두", "kcal": 350, "carb": 45, "protein": 15, "fat": 12},
    "fried_rice": {"name": "볶음밥", "kcal": 700, "carb": 95, "protein": 20, "fat": 25},
    "hamburger": {"name": "햄버거", "kcal": 550, "carb": 45, "protein": 25, "fat": 30},
    "ice_cream": {"name": "아이스크림", "kcal": 210, "carb": 25, "protein": 4, "fat": 11},
    "omelette": {"name": "오믈렛", "kcal": 250, "carb": 5, "protein": 18, "fat": 17},
    "pho": {"name": "쌀국수", "kcal": 450, "carb": 65, "protein": 20, "fat": 10},
    "pizza": {"name": "피자", "kcal": 850, "carb": 90, "protein": 35, "fat": 40},
    "ramen": {"name": "라면", "kcal": 500, "carb": 75, "protein": 10, "fat": 18},
    "spaghetti": {"name": "스파게티", "kcal": 700, "carb": 85, "protein": 25, "fat": 25},
    "sushi": {"name": "초밥", "kcal": 500, "carb": 65, "protein": 25, "fat": 10},
    "tacos": {"name": "타코", "kcal": 300, "carb": 30, "protein": 12, "fat": 15},
    "waffles": {"name": "와플", "kcal": 450, "carb": 60, "protein": 8, "fat": 20}
}

st.title("🍱 AI 식단 관리 서비스")

# =====================================
# 사용자 정보 및 목표 계산
# =====================================
# [변경 1] 기본값 제거: value=None / index=None 으로 비워두고, 미입력 시 목표를 '-'로 표시
col1, col2 = st.columns(2)
with col1:
    gender = st.selectbox("성별", ["남", "여"], index=None, placeholder="선택하세요")
    age = st.number_input("나이", min_value=1, max_value=100, value=None, placeholder="입력하세요")
with col2:
    height = st.number_input("키(cm)", min_value=100, max_value=250, value=None, placeholder="입력하세요")
    weight = st.number_input("몸무게(kg)", min_value=30, max_value=200, value=None, placeholder="입력하세요")

goal = st.selectbox("목표", ["다이어트", "유지", "벌크업"], index=None, placeholder="선택하세요")

# 모든 항목이 입력되었는지 확인
info_complete = None not in (gender, age, height, weight, goal)

if info_complete:
    if gender == "남":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    maintain_calorie = bmr * 1.55
    if goal == "다이어트":
        target_calorie = maintain_calorie - 500
    elif goal == "벌크업":
        target_calorie = maintain_calorie + 500
    else:
        target_calorie = maintain_calorie

    target_protein = weight * 1.5
    target_fat = weight * 0.8
    target_carb = max((target_calorie - target_protein * 4 - target_fat * 9) / 4, 0)
else:
    target_calorie = target_carb = target_protein = target_fat = None

st.subheader("🎯 오늘 목표")
if info_complete:
    st.code(f"칼로리: {round(target_calorie)} kcal | 탄수화물: {round(target_carb)}g | 단백질: {round(target_protein)}g | 지방: {round(target_fat)}g")
else:
    st.code("칼로리: - kcal | 탄수화물: - g | 단백질: - g | 지방: - g")
    st.caption("성별·나이·키·몸무게·목표를 모두 입력하면 목표치가 계산됩니다.")

# =====================================
# 음식 업로드 및 등록 (콜백 함수 적용)
# =====================================
st.header("📸 음식 사진 업로드")
meal_type = st.selectbox("식사 종류", ["아침", "점심", "저녁", "야식"])
uploaded_file = st.file_uploader("사진 선택", type=["jpg", "jpeg", "png"])

# 버튼 클릭 시 세션 상태를 변경할 콜백 함수 정의
def register_meal(info, meal_type):
    st.session_state.total_kcal += info["kcal"]
    st.session_state.total_protein += info["protein"]
    st.session_state.total_carb += info["carb"]
    st.session_state.total_fat += info["fat"]
    st.session_state.foods.append((meal_type, info["name"]))
    if meal_type == "야식":
        st.session_state.night_count += 1
    st.success(f"✅ {info['name']}(이)가 {meal_type} 식사로 등록되었습니다!")

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 이미지", use_container_width=True)

    # 예측 프로세스
    img = image.resize((224, 224))
    if img.mode != 'RGB':  # RGBA 등 예외 처리
        img = img.convert('RGB')
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    pred_idx = np.argmax(prediction)
    food_name = class_names[pred_idx]
    confidence = prediction[0][pred_idx] * 100
    info = food_info[food_name]

    st.metric(label=f"예측 음식: {info['name']}", value=f"{confidence:.2f}% 신뢰도")

    # 영양 정보 시각화
    st.markdown(f"**📊 {info['name']} 영양 정보:** {info['kcal']} kcal (탄 {info['carb']}g / 단 {info['protein']}g / 지 {info['fat']}g)")

    # 콜백 함수를 연결하여 상태 유지 문제 해결
    st.button("🍽️ 이 식사 등록하기", on_click=register_meal, args=(info, meal_type))

# =====================================
# 누적 현황 및 추천 음식
# =====================================
st.header("📝 오늘 식단 현황")
st.write(f"**기록된 식사:** {st.session_state.foods}")

if info_complete:
    remain = target_calorie - st.session_state.total_kcal
    st.write(f"**총 섭취 칼로리:** {st.session_state.total_kcal} / {round(target_calorie)} kcal (남은 칼로리: {round(remain)} kcal)")
else:
    st.write(f"**총 섭취 칼로리:** {st.session_state.total_kcal} kcal")

# [변경 2] 추천 음식 로직: 아침/점심/저녁 중 하나라도 등록되어야 표시
main_meals_logged = any(meal in ("아침", "점심", "저녁") for meal, _ in st.session_state.foods)

if main_meals_logged and info_complete:
    protein_ratio = st.session_state.total_protein / max(target_protein, 1)
    carb_ratio = st.session_state.total_carb / max(target_carb, 1)
    fat_ratio = st.session_state.total_fat / max(target_fat, 1)

    candidates = []
    if protein_ratio <= carb_ratio and protein_ratio <= fat_ratio:
        current_lack = "단백질"
        for food, f_info in food_info.items():
            candidates.append((f_info["protein"] / max(f_info["kcal"], 1), f_info["name"]))
    elif carb_ratio <= fat_ratio:
        current_lack = "탄수화물"
        for food, f_info in food_info.items():
            candidates.append((f_info["carb"] / max(f_info["kcal"], 1), f_info["name"]))
    else:
        current_lack = "지방"
        for food, f_info in food_info.items():
            candidates.append((f_info["fat"] / max(f_info["kcal"], 1), f_info["name"]))

    candidates.sort(reverse=True)
    st.info(f"💡 현재 가장 부족한 영양소는 **{current_lack}**입니다. 추천 음식: {', '.join([c[1] for c in candidates[:3]])}")
elif main_meals_logged and not info_complete:
    st.caption("추천을 받으려면 먼저 성별·나이·키·몸무게·목표를 입력해주세요.")

# =====================================
# 하루 평가 및 주간 평가
# =====================================
st.header("💯 오늘 평가")
if st.button("오늘 하루 평가하기"):
    if not info_complete:
        st.warning("먼저 성별·나이·키·몸무게·목표를 입력해주세요.")
    else:
        score = 100
        cal_diff = abs(target_calorie - st.session_state.total_kcal)
        if cal_diff > 800: score -= 30
        elif cal_diff > 500: score -= 20
        elif cal_diff > 300: score -= 10

        if st.session_state.total_protein < target_protein * 0.8: score -= 10
        if st.session_state.total_fat > target_fat * 1.3: score -= 10
        if st.session_state.total_carb > target_carb * 1.3: score -= 10
        score = max(score, 0)

        # 중복 점수도 날짜별 누적이 되도록 조건문 제거
        st.session_state.weekly_scores.append(score)
        st.session_state.weekly_calories.append(st.session_state.total_kcal)

        st.subheader(f"오늘 나의 식단 점수: {score}점")
        if score >= 90: st.success("매우 우수한 식단입니다. 대단해요! 👍")
        elif score >= 70: st.info("양호한 식단입니다. 조금만 더 신경 써보세요! 🙂")
        else: st.warning("식단 개선이 필요합니다. 영양 균형을 맞춰보세요. ⚠️")

st.header("📅 주간 리포트")
if len(st.session_state.weekly_scores) > 0:
    weekly_avg = sum(st.session_state.weekly_scores) / len(st.session_state.weekly_scores)
    st.write(f"**주간 평균 점수:** {round(weekly_avg, 1)} 점")

    if weekly_avg >= 90: st.success("🥇 매우 우수한 식습관을 유지 중입니다.")
    elif weekly_avg >= 70: st.info("🥈 양호한 식습관입니다.")
    else: st.warning("🥉 식습관 개선이 필요합니다.")

if st.session_state.night_count >= 3:
    st.sidebar.warning(f"🚨 이번 주 야식 섭취가 {st.session_state.night_count}회입니다! 야식을 줄여주세요.")

# 주간 칼로리 그래프
if len(st.session_state.weekly_calories) > 0:
    st.subheader("📈 주간 칼로리 변화 추이")
    days = list(range(1, len(st.session_state.weekly_calories) + 1))
    fig, ax = plt.subplots()
    ax.plot(days, st.session_state.weekly_calories, marker="o", color="orange")
    # [변경 3] x축을 정수(Day 1, 2, 3...) 1단위 눈금으로 고정 (0.96 등 소수 눈금 제거)
    ax.set_xticks(days)
    ax.set_xlabel("Day")
    ax.set_ylabel("Calories (kcal)")
    st.pyplot(fig)

# 초기화 버튼
if st.button("🔄 데이터 초기화"):
    st.session_state.clear()
    st.success("모든 데이터가 초기화되었습니다.")
    st.rerun()
