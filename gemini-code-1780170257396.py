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
# 클래스 이름 및 영양성분 DB
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
col1, col2 = st.columns(2)
with col1:
    gender = st.selectbox("성별", ["남", "여"])
    age = st.number_input("나이", min_value=1, max_value=100, value=20)
with col2:
    height = st.number_input("키(cm)", min_value=100, max_value=250, value=170)
    weight = st.number_input("몸무게(kg)", min_value=30, max_value=200, value=70)

goal = st.selectbox("목표", ["다이어트", "유지", "벌크업"])

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

st.subheader("🎯 오늘 목표")
st.code(f"칼로리: {round(target_calorie)} kcal | 탄수화물: {
