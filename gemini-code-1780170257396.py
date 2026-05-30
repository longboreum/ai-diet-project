import streamlit as st
import tensorflow as tf
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# =====================================
# 모델 불러오기 (캐싱을 적용하여 새로고침 시 속도 저하 방지)
# =====================================
MODEL_PATH = "food_model.h5"

@st.cache_resource
def load_my_model():
    return tf.keras.models.load_model(MODEL_PATH)

try:
    model = load_my_model()
except Exception as e:
    st.error(f"모델 파일을 찾을 수 없거나 불러오는데 실패했습니다: {e}")

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
# 클래스 이름
# =====================================
class_names = [
    "bibimbap", "chicken_wings", "donuts", "dumplings", "fried_rice",
    "hamburger", "ice_cream", "omelette", "pho", "pizza",
    "ramen", "spaghetti", "sushi", "tacos", "waffles"
]

# =====================================
# 영양성분 DB
# =====================================
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

# 식사 등록을 안전하게 처리하기 위한 콜백(Callback) 함수 정의
def on_register_click(info, m_type):
    st.session_state.total_kcal += info["kcal"]
    st.session_state.total_protein += info["protein"]
    st.session_state.total_carb += info["carb"]
    st.session_state.total_fat += info["fat"]
    st.session_state.foods.append((m_type, info["name"]))
    if m_type == "야식":
        st.session_state.night_count += 1

# =====================================
# 제목
# =====================================
st.title("🍱 AI 식단 관리 서비스")

# =====================================
# 사용자 정보
# =====================================
gender = st.selectbox("성별", ["남", "여"])
age = st.number_input("나이", min_value=1, max_value=100, value=20)
height = st.number_input("키(cm)", min_value=100, max_value=250, value=170)
weight = st.number_input("몸무게(kg)", min_value=30, max_value=200, value=70)
goal = st.selectbox("목표", ["다이어트", "유지", "벌크업"])

# =====================================
# 목표 칼로리 계산
# =====================================
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
target_carb = (target_calorie - target_protein * 4 - target_fat * 9) / 4

st.subheader("오늘 목표")
st.write("목표 칼로리 :", round(target_calorie), "kcal")
st.write("목표 단백질 :", round(target_protein), "g")
st.write("목표 탄수화물 :", round(target_carb), "g")
st.write("목표 지방 :", round(target_fat), "g")

# =====================================
# 식사 종류
# =====================================
meal_type = st.selectbox("식사 종류", ["아침", "점심", "저녁", "야식"])

# =====================================
# 음식 업로드 및 예측
# =====================================
st.header("음식 사진 업로드")
uploaded_file = st.file_uploader("사진 선택", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, width=350)

    # 이미지 전처리 및 채널 예외 처리 (RGBA -> RGB)
    img = image.resize((224, 224))
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    pred_idx = np.argmax(prediction)
    food_name = class_names[pred_idx]
    confidence = prediction[0][pred_idx] * 100
    info = food_info[food_name]

    st.success(f"예측 음식 : {info['name']}")
    st.write(f"신뢰도 : {confidence:.2f}%")

    st.subheader("영양 정보")
    st.write("식사 종류 :", meal_type)
    st.write("칼로리 :", info["kcal"], "kcal")
    st.write("탄수화물 :", info["carb"], "g")
    st.write("단백질 :", info["protein"], "g")
    st.write("지방 :", info["fat"], "g")

    # 🔥 중요: 새로고침 시 데이터 증발을 막기 위해 'on_click' 콜백 함수 구조로 변경
    st.button(
        "식사 등록", 
        on_click=on_register_click, 
        args=(info, meal_type)
    )

# =====================================
# 누적 현황
# =====================================
st.header("오늘 식단 현황")
st.write("식사 기록 :", st.session_state.foods)
st.write("총 섭취 칼로리 :", st.session_state.total_kcal, "kcal")

remain = target_calorie - st.session_state.total_kcal
st.write("남은 칼로리 :", round(remain), "kcal")
st.write("총 단백질 :", st.session_state.total_protein, "g")
st.write("총 탄수화물 :", st.session_state.total_carb, "g")
st.write("총 지방 :", st.session_state.total_fat, "g")
st.write("야식 횟수 :", st.session_state.night_count, "회")

# =====================================
# 추천 음식
# =====================================
st.header("추천 음식")

protein_ratio = st.session_state.total_protein / max(target_protein, 1)
carb_ratio = st.session_state.total_carb / max(target_carb, 1)
fat_ratio = st.session_state.total_fat / max(target_fat, 1)

candidates = []

if protein_ratio < carb_ratio and protein_ratio < fat_ratio:
    st.write("현재 가장 부족한 영양소 : 단백질")
    for food, info in food_info.items():
        score = info["protein"] / info["kcal"]
        candidates.append((score, info["name"]))
elif carb_ratio < fat_ratio:
    st.write("현재 가장 부족한 영양소 : 탄수화물")
    for food, info in food_info.items():
        score = info["carb"] / info["kcal"]
        candidates.append((score, info["name"]))
else:
    st.write("현재 가장 부족한 영양소 : 지방")
    for food, info in food_info.items():
        score = info["fat"] / info["kcal"]
        candidates.append((score, info["name"]))

candidates.sort(reverse=True)
st.subheader("추천 음식 TOP3")
for score, food in candidates[:3]:
    st.write("•", food)

# =====================================
# 하루 평가
# =====================================
st.header("오늘 평가")

if st.button("오늘 평가 보기"):
    score = 100
    cal_diff = abs(target_calorie - st.session_state.total_kcal)

    if cal_diff > 800: score -= 30
    elif cal_diff > 500: score -= 20
    elif cal_diff > 300: score -= 10

    if st.session_state.total_protein < target_protein * 0.8: score -= 10
    if st.session_state.total_fat > target_fat * 1.3: score -= 10
    if st.session_state.total_carb > target_carb * 1.3: score -= 10

    score = max(score, 0)
    
    # 🔥 수정: 같은 점수나 같은 칼로리라도 매일 기록이 누적될 수 있도록 중복 제거 로직(if not in) 삭제
    st.session_state.weekly_scores.append(score)
    st.session_state.weekly_calories.append(st.session_state.total_kcal)

    st.subheader(f"오늘 점수 : {score}점")
    if score >= 90:
        st.success("매우 우수한 식단입니다.")
    elif score >= 70:
        st.info("양호한 식단입니다.")
    else:
        st.warning("식단 개선이 필요합니다.")

# =====================================
# 주간 평가
# =====================================
st.header("주간 평가")

if len(st.session_state.weekly_scores) > 0:
    weekly_avg = sum(st.session_state.weekly_scores) / len(st.session_state.weekly_scores)
    st.write("주간 평균 점수 :", round(weekly_avg, 1), "점")

    if weekly_avg >= 90:
        st.success("매우 우수한 식습관입니다.")
    elif weekly_avg >= 70:
        st.info("양호한 식습관입니다.")
    else:
        st.warning("식습관 개선이 필요합니다.")

if st.session_state.night_count >= 3:
    st.warning("야식 섭취가 3회 이상입니다.")

# =====================================
# 주간 칼로리 그래프
# =====================================
if len(st.session_state.weekly_calories) > 0:
    st.subheader("주간 칼로리 그래프")
    
    fig, ax = plt.subplots()
    days = list(range(1, len(st.session_state.weekly_calories) + 1))
    
    ax.plot(
        days,
        st.session_state.weekly_calories,
        marker="o"
    )
    
    # 🔥 수정: 데이터 개수가 적을 때 x축 눈금에 0.96 같은 소수점이 생기는 현상 방지
    ax.set_xticks(days)
    ax.set_xlabel("Day")
    ax.set_ylabel("Calories")
    
    st.pyplot(fig)

# =====================================
# 초기화
# =====================================
if st.button("하루 초기화"):
    st.session_state.total_kcal = 0
    st.session_state.total_protein = 0
    st.session_state.total_carb = 0
    st.session_state.total_fat = 0
    st.session_state.foods = []
    st.session_state.night_count = 0
    st.session_state.weekly_scores = []
    st.session_state.weekly_calories = []
    st.rerun()
