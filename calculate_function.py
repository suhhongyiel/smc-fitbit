import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, date

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