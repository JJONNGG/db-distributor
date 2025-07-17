# streamlit 기반 DB 자동 분배기 앱

import streamlit as st
import pandas as pd
import datetime
import os

st.set_page_config(
    page_title="에픽스 H&L 디비 자동 분배기",
    layout="wide",
    page_icon="📦"
)

# 로고 이미지 삽입 (같은 폴더에 logo.png 파일이 존재해야 함)
st.image("logo.png", width=150)

st.title("📦 에픽스 H&L 디비 자동 분배기")

st.markdown("""
엑셀 파일에서 **담당자별 상품 오더율**을 불러와, 상품별 총 수량을 기준으로 분배 수량을 자동 계산합니다.
""")

max_per_person = st.number_input("한 사람당 최대 분배 수량 (전체 상품 합계 기준)", min_value=1, value=12)
회차명 = st.text_input("회차명을 입력하세요 (예: 1차, 2차 오후 등)", value="1차")

st.header("📂 회차별 비율 파일 업로드")
uploaded_file = st.file_uploader("상담원별 상품 오더율 파일 업로드", type=["xlsx"])

상품정보 = []
상품_이름_맵 = {
    "삼성 혈당": "C",
    "삼성 쾌변": "D",
    "삼성 메가": "E",
    "원광 침향": "F",
    "일양 뼈": "G"
}
상품수 = len(상품_이름_맵)

st.header("📦 상품별 총 수량 입력")
for 상품명 in 상품_이름_맵.keys():
    수량 = st.number_input(f"{상품명} 총 수량", key=f"수량_{상품명}", value=100)
    상품정보.append({"이름": 상품명, "총수량": 수량})

if uploaded_file is not None:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = df.columns.astype(str)
        df = df.rename(columns={
            df.columns[1]: "담당자",
            df.columns[2]: "삼성 혈당",
            df.columns[3]: "삼성 쾌변",
            df.columns[4]: "삼성 메가",
            df.columns[5]: "원광 침향",
            df.columns[6]: "일양 뼈"
        })

        for col in ["삼성 혈당", "삼성 쾌변", "삼성 메가", "원광 침향", "일양 뼈"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        분배표 = pd.DataFrame()
        미분배수량 = {}

        for 상품 in 상품정보:
            이름 = 상품["이름"]
            총수량 = 상품["총수량"]

            temp = df[["담당자", 이름]].copy()
            temp = temp.rename(columns={이름: "오더율"})
            temp["분배비율"] = temp["오더율"] / temp["오더율"].sum()
            temp[이름] = temp["분배비율"] * 총수량
            temp[이름] = temp[이름].round(1)

            if 분배표.empty:
                분배표 = temp[["담당자", 이름]].copy()
            else:
                분배표 = pd.merge(분배표, temp[["담당자", 이름]], on="담당자", how="outer")

        분배표 = 분배표.fillna(0)

        # 담당자별 전체 합계 구해서 제한 초과 시 비율대로 차감
        분배표["총합계"] = 분배표[list(상품_이름_맵.keys())].sum(axis=1)
        초과자 = 분배표[분배표["총합계"] > max_per_person].copy()

        for idx, row in 초과자.iterrows():
            비율 = row[list(상품_이름_맵.keys())] / row[list(상품_이름_맵.keys())].sum()
            수정분배 = 비율 * max_per_person
            for 상품 in 상품_이름_맵.keys():
                분배표.loc[idx, 상품] = round(수정분배[상품], 1)

        # 미분배 수량 계산
        미분배행 = {"담당자": "미분배 수량"}
        for 상품 in 상품정보:
            이름 = 상품["이름"]
            분배합 = 분배표[이름].sum()
            남은 = round(상품["총수량"] - 분배합, 1)
            미분배행[이름] = 남은
        미분배행["총합계"] = "-"
        분배표 = pd.concat([분배표, pd.DataFrame([미분배행])], ignore_index=True)

        st.header("✅ 최종 분배표")
        st.dataframe(분배표, use_container_width=True)

        save_folder = "간편_비율_분배결과"
        os.makedirs(save_folder, exist_ok=True)
        today = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        save_name = f"{save_folder}/상품분배_{회차명}_{today}.xlsx"
        분배표.to_excel(save_name, index=False)

        with open(save_name, "rb") as f:
            st.download_button("📥 엑셀 다운로드", data=f.read(), file_name=os.path.basename(save_name))

        st.success(f"📦 결과 파일이 저장되었습니다: {save_name}")

    except Exception as e:
        st.error(f"처리 중 오류 발생: {e}")
else:
    st.info("엑셀 파일을 업로드하고 상품 수량을 입력하면 분배가 계산됩니다.")
