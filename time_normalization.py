# 데이터에대한 가능한 날짜 형식과 시간데이터들에 대한 Normalization , Generalization 진행

from datetime import datetime, date
import pandas as pd

def parse_date(date_str):
    # 가능한 날짜 형식을 모두 나열합니다.
    date_formats = [
        '%Y-%m-%d',  # 2023-08-22
        '%y/%d/%Y',  # 23/22/2023
        '%m/%d/%Y',  # 06/09/2023
        '%Y/%m/%d',  # 2023/06/09
        '%d/%m/%Y',  # 09/06/2023
        '%d-%m-%Y',  # 09-06-2023
    ]
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    return None  # 날짜 형식에 맞지 않으면 None 반환

# 시간 데이터 변환 함수 정의
def normalize_time(time_str):
    try:
        if pd.isna(time_str) or time_str in ['-1', '-1.0']:
            return '00:00:00'
        if 'AM' in time_str or 'PM' in time_str:
            return pd.to_datetime(time_str, format='%I:%M:%S %p').strftime('%H:%M:%S')
        parts = time_str.split(':')
        if len(parts) == 2:  # mm:ss.0 형식
            minutes, seconds = parts
            seconds = seconds.split('.')[0]
            return f"00:{minutes}:{seconds}"
        elif len(parts) == 3:  # hh:mm:ss.0 형식
            hours, minutes, seconds = parts
            seconds = seconds.split('.')[0]
            return f"{hours}:{minutes}:{seconds}"
    except Exception as e:
        print(f"Error converting time: {e}")
        return '00:00:00'

def unify_sleep_date_format(df, date_column, time_column=None):
    df[date_column] = df[date_column].apply(parse_date)
    df = df.dropna(subset=[date_column])
    if time_column:
        df[time_column] = df[time_column].apply(normalize_time)
        df['datetime'] = pd.to_datetime(df[date_column].dt.strftime('%Y-%m-%d') + ' ' + df[time_column])
        df = df.dropna(subset=['datetime'])
        df = df.sort_values(by='datetime').reset_index(drop=True)

    return df


def unify_date_format(df, date_column, time_column=None):
    df[date_column] = df[date_column].apply(parse_date)
    df = df.dropna(subset=[date_column])  # None 값을 가진 행을 제거
    if time_column:
        df[time_column] = df[time_column].replace(['-1', '-1.0'], '00:00:00')  # -1 값을 00:00:00으로 대체
        # df['datetime'] = df.apply(lambda row: datetime.combine(row[date_column], datetime.strptime(row[time_column], '%H:%M:%S').time()) if row[time_column] != '-1' else None, axis=1)
        df['datetime'] = df.apply(lambda row: datetime.combine(row[date_column], datetime.strptime(row[time_column], '%H:%M:%S').time()), axis=1)

        df = df.dropna(subset=['datetime'])
        df = df.sort_values(by='datetime').reset_index(drop=True)
    else:
        df[date_column] = df[date_column].dt.strftime('%Y-%m-%d')  # 원하는 날짜 형식으로 통일
        df[date_column] = pd.to_datetime(df[date_column])  # 다시 datetime 형식으로 변환
    return df
