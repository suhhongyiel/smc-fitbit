import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, date
import plotly.graph_objects as go
import time_normalization as tn
import create_graph as cgr
# 데이터베이스 연결 설정
db_url = 'mysql+pymysql://root:Korea2022!@119.67.109.156:3306/project_wd'
engine = create_engine(db_url)

def fetch_patient_data(table_name, date_column, time_column=None, start_date=None, end_date=None):
    try:
        query = f"SELECT * FROM {table_name}"
        df = pd.read_sql(query, engine)
        # 날짜 열을 다양한 형식으로 변환 후 통일
        if "수면상세" in table_name:
            df = tn.unify_sleep_date_format(df, date_column, time_column)
        else:
            df = tn.unify_sleep_date_format(df, date_column, time_column)
        if start_date and end_date:
            # datetime.date 객체를 datetime.datetime 객체로 변환
            start_date = datetime.combine(start_date, datetime.min.time())
            end_date = datetime.combine(end_date, datetime.min.time())
            if time_column:
                df = df[(df['datetime'] >= start_date) & (df['datetime'] <= end_date)]
            else:
                df = df[(df[date_column] >= start_date) & (df[date_column] <= end_date)]
        return df
    except Exception as e:
        st.error(f"Error fetching data from {table_name}: {e}")
        return None

def fetch_date_range(study_id):
    try:
        query = f"SELECT * FROM {study_id}_휴식기심박수"
        df = pd.read_sql(query, engine)
        df = tn.unify_sleep_date_format(df, 'date')
        min_date = df['date'].min()
        max_date = df['date'].max()
        return min_date, max_date, study_id
    except Exception as e:
        st.error(f"Error fetching date range: {e}")
        return None, None, None


def fill_missing_times(df, start_date, end_date):
    # 시작일과 종료일을 기준으로 모든 분 단위 시간 생성
    full_time_range = pd.date_range(start=start_date, end=end_date, freq='T')
    df_full = pd.DataFrame(full_time_range, columns=['datetime'])
    df_full = df_full.set_index('datetime')

    # 원본 데이터프레임을 datetime을 인덱스로 설정
    df = df.set_index('datetime')

    # 원본 데이터프레임을 전체 시간 범위 데이터프레임과 병합
    df_combined = df_full.join(df, how='left')

    # 누락된 값을 -1로 채우기
    df_combined['value'] = df_combined['value'].fillna(-1)

    return df_combined.reset_index()

# compliance 계산
def calculate_daily_compliance(df):
    df['date'] = df['datetime'].dt.date
    daily_compliance = df.groupby('date').apply(lambda x: (x['value'] != -1).sum() / 1440).reset_index(name='compliance')
    return daily_compliance

def calculate_sleep_summary(df):
    df['date'] = df['date'].dt.date
    daily_sleep_summary = df.groupby('date').sum().reset_index()
    return daily_sleep_summary


# def display_patient_data(start_date, end_date):
#     df_resting_hr = fetch_patient_data("smcfb_01_192_휴식기심박수", 'date', start_date=start_date, end_date=end_date)
#     df_heart_rate = fetch_patient_data("smcfb_01_192_분별심박수", 'date', 'time_min', start_date=start_date, end_date=end_date)
#     df_sleep_summary = fetch_patient_data("smcfb_01_192_수면요약", 'date', start_date=start_date, end_date=end_date)
#     # df_sleep = fetch_patient_data("smcfb_01_192_수면상세", 'date', start_date=start_date, end_date=end_date)

#     if df_resting_hr is not None and df_heart_rate is not None:
#         st.write("Resting Heart Rate Data")
#         st.write(df_resting_hr)
#         st.write("Heart Rate Data")
#         st.write(df_heart_rate)
#         st.write("Sleep Summary Data")
#         st.write(df_sleep_summary)



def display_charts(start_date, end_date, study_id):
    # study_id = 'smcfb_01_192'
    df_resting_hr = fetch_patient_data(f"{study_id}_휴식기심박수", 'date', start_date=start_date, end_date=end_date)
    df_heart_rate = fetch_patient_data(f"{study_id}_분별심박수", 'date', 'time_min', start_date=start_date, end_date=end_date)
    df_sleep_summary = fetch_patient_data(f"{study_id}_수면요약", 'date', start_date=start_date, end_date=end_date)
    sleep_data = fetch_patient_data(f"{study_id}_수면상세", 'date', 'time_stamp', start_date=start_date, end_date=end_date)


    if df_sleep_summary is not None:
        df_sleep_summary_daily = calculate_sleep_summary(df_sleep_summary)

    if df_sleep_summary is not None:
        col1, col2 = st.columns(2)
        if 'stages_deep' in df_sleep_summary.columns:
            with col1:
                fig4 = cgr.create_sleep_summary_donut_chart(df_sleep_summary)
                st.plotly_chart(fig4)
            with col2:
                fig4 = cgr.create_sleep_summary_bar_chart(df_sleep_summary_daily)
                st.plotly_chart(fig4)
        else:
            st.error("The specified columns for sleep stages do not exist in the sleep summary data.")


# normal sleep graph
    if sleep_data is not None:
        fig = cgr.create_sleep_stage_plot(sleep_data)
        st.plotly_chart(fig)



    if df_heart_rate is not None:
        df_heart_rate_filled = fill_missing_times(df_heart_rate, start_date, end_date)
        df_compliance = calculate_daily_compliance(df_heart_rate)




# # adv sleep graph
#     if df_heart_rate_filled is not None:
#         fig = cgr.create_adv_sleep_plot(sleep_data, df_heart_rate_filled)
#         st.plotly_chart(fig)


    if df_compliance is not None:
        col3, col4 = st.columns(2)
        if 'compliance' in df_compliance.columns:
            with col3:
                fig3 = cgr.create_compliance_chart(df_compliance)
                st.plotly_chart(fig3)
            with col4:
                st.write("Daily Compliance Data")
                st.write(df_compliance)
        else:
            st.error("The specified column 'compliance' does not exist in the compliance data.")






    col5, col6 = st.columns(2)
    if df_resting_hr is not None:
        if 'resting_hr' in df_resting_hr.columns:
            with col5:
                fig1, restdf = cgr.create_resting_hr_chart(df_resting_hr)
                st.plotly_chart(fig1)
            with col6:
                st.write('Resting Heart Rate Table')
                st.dataframe(restdf)
        else:
            st.error("The specified column 'resting_hr' does not exist in the resting heart rate data.")

    col7, col8 = st.columns(2)
    if df_heart_rate is not None:
        if 'value' in df_heart_rate.columns:
            with col7:
                fig2, hrdf = cgr.create_heart_rate_chart(df_heart_rate)
                st.plotly_chart(fig2)
            with col8:
                st.write('Heart Rate Table')
                st.write(hrdf)
        else:
            st.error("The specified column 'value' does not exist in the heart rate data.")
    





