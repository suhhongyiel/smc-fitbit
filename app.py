import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from dateutil import parser
import pandas as pd
import io
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from fpdf import FPDF
from matplotlib.backends.backend_pdf import PdfPages
# import MatplotlibReportGenerator as mrg
import matplotlib.dates as mdates
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
import utils
import function
from datetime import datetime
from matplotlib.backends.backend_pdf import PdfPages

import matplotlib.gridspec as gridspec
import data_display

st.set_page_config(layout="wide")

# 세션 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# 로그인 정보
actual_email = "email"
actual_password = "password"

# 로그인 폼
def login():
    placeholder = st.empty()
    with placeholder.form("login"):
        st.markdown("#### Enter your credentials")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
    
    if submit:
        if email == actual_email and password == actual_password:
            st.session_state.logged_in = True
            placeholder.empty()
            st.experimental_rerun()  # 로그인 성공 시 페이지 새로고침
        else:
            st.session_state.logged_in = False
            st.error("Login failed")

# SQL 쿼리 실행
@st.cache
def get_study_ids():
    query = "SELECT DISTINCT study_ID FROM fitbit_device_list;"

    db_url = 'mysql+pymysql://root:Korea2022!@119.67.109.156:3306/project_wd'
    engine = create_engine(db_url)

    try:
        with engine.connect() as connection:
            result = connection.execute(text(query))
            study_ids = [row[0] for row in result]
        return study_ids
    except SQLAlchemyError as e:
        st.error(f"Error fetching study IDs: {e}")
        return []

# 메인 페이지
def page_about():
    st.title("환자 데이터베이스")
    # Study ID 목록 가져오기
    study_id = get_study_ids()
    st.write(study_id)
    # 사용자가 선택할 수 있도록 셀렉트박스 위젯 생성
    selected_study_id = st.selectbox('Select Study ID', study_id)

    min_date, max_date, id = data_display.fetch_date_range(selected_study_id)

    if min_date and max_date:
        start_date, end_date = st.date_input("데이터 기간 선택", [min_date, max_date], min_value=min_date, max_value=max_date, key="data_date_range")
        start_date = start_date[0] if isinstance(start_date, list) else start_date
        end_date = end_date[1] if isinstance(end_date, list) else end_date
        
        data_display.display_charts(start_date, end_date, id)
    
    # 링크로 이동하는 버튼 추가
    if st.button("테스트 서버로 이동"):
        js = "window.open('https://testingserver.streamlit.app/')"  # JavaScript 코드
        html = f'<script>{js}</script>'
        st.markdown(html, unsafe_allow_html=True)


# 메인 함수
def main():
    if st.session_state.logged_in:
        page_about()  # 로그인 성공 시 메인 페이지 표시
    else:
        login()  # 로그인 폼 표시

if __name__ == '__main__':
    main()