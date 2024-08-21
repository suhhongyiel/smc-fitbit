import streamlit as st
import pandas as pd
from sqlalchemy import create_engine
from datetime import datetime, date
import plotly.graph_objects as go
import time_normalization as tn
import plotly.express as px

def create_adv_sleep_plot(sleep_df, heart_rate_df):
    # datetime 열을 datetime 형식으로 변환
    sleep_df['datetime'] = pd.to_datetime(sleep_df['datetime'])
    heart_rate_df['datetime'] = pd.to_datetime(heart_rate_df['datetime'])

    # 색상 매핑
    new_cmap = {'rem': 'red', 'light': 'blue', 'deep': 'green', 'awake': 'gray', 'restless': 'orange', 'asleep': 'purple', 'wake': 'yellow', 'missing': 'black'}
    sleep_df['sleep_stage'] = sleep_df['sleep_stage'].map({'rem': 'rem', 'light': 'light', 'deep': 'deep', 'awake': 'awake', 'restless':'restless'}).fillna('asleep')
    # 초 단위를 버리고 분 단위로 변환
    sleep_df['datetime'] = sleep_df['datetime'].dt.floor('min')
    
    # 시간 관련 계산 (분 단위로 변환)
    sleep_df['time_minutes'] = sleep_df['time_stamp'].apply(lambda x: sum(int(part) * 60 ** (1 - i) for i, part in enumerate(x.split(':'))))
    sleep_df['sleep_duration_minutes'] = sleep_df['sleep_duration'].astype(float) / 60

    # time_minutes가 0인 경우 sleep_duration_minutes도 0으로 설정
    sleep_df.loc[sleep_df['time_minutes'] == 0, 'sleep_duration_minutes'] = 0

    # 날짜를 넘어가는 경우를 처리하기 위한 데이터 확장
    expanded_rows = []
    for _, row in sleep_df.iterrows():
        start_datetime = row['datetime']
        duration_minutes = int(row['sleep_duration_minutes'])
        end_datetime = start_datetime + pd.Timedelta(minutes=duration_minutes)

        # 시작 시간부터 종료 시간까지 모든 분 생성
        current_datetime = start_datetime
        while current_datetime < end_datetime:
            expanded_rows.append({
                'datetime': current_datetime,
                'date': current_datetime.date(),
                'sleep_stage': row['sleep_stage'],
                'time_minutes': (current_datetime - current_datetime.replace(hour=0, minute=0, second=0)).total_seconds() / 60,
                'sleep_duration_minutes': 1  # 각 분마다 1분의 sleep_duration_minutes
            })
            current_datetime += pd.Timedelta(minutes=1)

    # 확장된 데이터 프레임 생성
    expanded_df = pd.DataFrame(expanded_rows)

    # 일별 각 단계별 수면시간 계산
    daily_sleep = expanded_df.groupby(['date', 'sleep_stage']).agg({'sleep_duration_minutes': 'sum'}).reset_index()
    daily_sleep_pivot = daily_sleep.pivot(index='date', columns='sleep_stage', values='sleep_duration_minutes').fillna(0)

    # 일별 각 단계별 수면시간을 표로 표시
    st.write("Daily Sleep Duration by Stage")
    st.dataframe(daily_sleep_pivot.T)

    # 심박수 데이터를 수면 데이터와 매핑
    heart_rate_df['heart_rate'] = heart_rate_df['value'].apply(lambda x: 1 if x != -1 else 0)
    heart_rate_df = heart_rate_df[['datetime', 'heart_rate']]
    full_df = pd.merge(expanded_df, heart_rate_df, on='datetime', how='outer').sort_values(by='datetime').fillna({'heart_rate': 0})

    # Compliance 계산
    def calculate_compliance(row):
        if row['heart_rate'] == 1 and row['sleep_stage'] not in ['light', 'rem', 'deep', 'awake', 'restless', 'asleep', 'rem']:
            return 'wake'
        elif row['sleep_stage'] in ['rem']:
            return 'rem'
        elif row['sleep_stage'] in ['light']:
            return 'light'
        elif row['sleep_stage'] in ['deep']:
            return 'deep'
        elif row['sleep_stage'] in ['awake']:
            return 'awake'
        elif row['sleep_stage'] in ['restless']:
            return 'restless'
        elif row['sleep_stage'] in ['asleep']:
            return 'asleep'
        elif row['heart_rate'] == 0:
            return 'missing'
        else:
            return 'wake'  # 만약 다른 상태가 있다면 이를 처리

    full_df['compliance'] = full_df.apply(calculate_compliance, axis=1)

    # 연속적인 compliance 값의 지속 시간을 time_minutes에 추가
    full_df['date_only'] = full_df['datetime'].dt.date
    full_df['sleep_duration_minutes'] = 1
    full_df = full_df.sort_values(by='datetime').reset_index(drop=True)
    # new_df = full_df.groupby(['datetime', 'compliance']).agg({'sleep_duration_minutes': 'sum'}).reset_index()
    # 새로운 데이터프레임 생성
    rows = []
    current_compliance = None
    start_time = None
    total_duration = 0

    for i, row in full_df.iterrows():
        if row['compliance'] != current_compliance:
            if current_compliance is not None:
                rows.append({
                    'datetime': start_time,
                    'compliance': current_compliance,
                    'sleep_duration_minutes': total_duration,
                    'time_duration': total_duration
                })
            current_compliance = row['compliance']
            start_time = row['datetime']
            total_duration = row['sleep_duration_minutes']
        else:
            total_duration += row['sleep_duration_minutes']

    # 마지막 행 추가
    rows.append({
        'datetime': start_time,
        'compliance': current_compliance,
        'sleep_duration_minutes': total_duration,
        'time_duration': total_duration
    })

    new_df = pd.DataFrame(rows)


    # 각 상태에 대해 데이터 포인트를 하나의 바 차트로 추가
    fig = go.Figure()

    for stage, color in new_cmap.items():
        stage_data = full_df[full_df['compliance'] == stage]
        

        fig.add_trace(go.Bar(
            x=stage_data['date_only'],
            y=stage_data['sleep_duration_minutes'],
            base=stage_data['time_minutes'],
            marker_color=color,
            name=stage,
            orientation='v',
            width=36000000  # 막대 너비를 증가
        ))

    # x축 범위를 데이터의 최소 및 최대 날짜로 설정
    min_date = full_df['datetime'].min()
    max_date = full_df['datetime'].max()

    fig.update_layout(
        title='Detailed Sleep Stages Over Time',
        xaxis_title='Date',
        yaxis_title='Time (HH:MM)',
        xaxis=dict(
            range=[min_date, max_date],
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(0, 25*60, 60)),  # 24시간을 1시간 단위로 표시 (0~24시)
            ticktext=[f'{int(t/60):02}:{int(t%60):02}' for t in range(0, 25*60, 60)],  # 분 단위를 HH:MM 형식으로 변환
            autorange='reversed',
            showgrid=True,
            zeroline=False,
            range=[24*60, 0]  # y축을 0분(00:00)에서 1440분(24:00)로 설정
        ),
        barmode='stack',
        height=800
    )
    return fig



def create_sleep_stage_plot(df):
    # datetime 열을 datetime 형식으로 변환
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['date'].dt.strftime('%Y-%m-%d')
    # 색상 매핑
    new_cmap = {'rem': 'green', 'light': 'yellow', 'deep': 'green', 'awake': 'lightblue', 'restless':'lightblue', 'asleep':'blue'}
    df['sleep_stage'] = df['sleep_stage'].map({'rem': 'rem', 'light': 'light', 'deep': 'deep', 'awake': 'awake', 'restless':'restless'}).fillna('asleep')

    # 시간 관련 계산 (분 단위로 변환)
    df['time_minutes'] = df['time_stamp'].apply(lambda x: sum(int(part) * 60 ** (1 - i) for i, part in enumerate(x.split(':'))))
    df['sleep_duration_minutes'] = df['sleep_duration'].astype(float) / 60
    df.loc[df['time_minutes'] == 0, 'sleep_duration_minutes'] = 0

    # 날짜를 넘어가는 경우를 처리하기 위한 데이터 확장
    expanded_rows = []
    for _, row in df.iterrows():
        start_datetime = row['datetime']
        duration_minutes = row['sleep_duration_minutes']
        end_datetime = start_datetime + pd.Timedelta(minutes=duration_minutes)
        
        if end_datetime.date() != start_datetime.date():
            # 날짜를 넘어가는 경우 두 개의 데이터 포인트로 나누기
            midnight = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0) + pd.Timedelta(days=1)
            duration_until_midnight = (midnight - start_datetime).total_seconds() / 60
            
            expanded_rows.append({
                'datetime': start_datetime,
                'sleep_stage': row['sleep_stage'],
                'time_minutes': row['time_minutes'],
                'sleep_duration_minutes': duration_until_midnight
            })
            expanded_rows.append({
                'datetime': midnight,
                'sleep_stage': row['sleep_stage'],
                'time_minutes': 0,
                'sleep_duration_minutes': duration_minutes - duration_until_midnight
            })
        else:
            expanded_rows.append(row.to_dict())

    # 확장된 데이터 프레임 생성
    expanded_df = pd.DataFrame(expanded_rows)


    # 일별 각 단계별 수면시간 계산
    daily_sleep = expanded_df.groupby(['date', 'sleep_stage']).agg({'sleep_duration_minutes': 'sum'}).reset_index()
    daily_sleep_pivot = daily_sleep.pivot(index='date', columns='sleep_stage', values='sleep_duration_minutes').fillna(0)

    # 일별 각 단계별 수면시간을 표로 표시
    st.write("Daily Sleep Duration by Stage")
    st.dataframe(daily_sleep_pivot.T)
    
    # 각 수면 단계에 대해 데이터 포인트를 하나의 바 차트로 추가
    fig = go.Figure()
    for stage, color in new_cmap.items():
        stage_data = expanded_df[expanded_df['sleep_stage'] == stage]
        fig.add_trace(go.Bar(
            x=stage_data['date'],
            y=stage_data['sleep_duration_minutes'],
            base=stage_data['time_minutes'],
            marker_color=color,
            name=stage,
            orientation='v',
            width=36000000  # 막대 너비를 증가
        ))    

    # x축 범위를 데이터의 최소 및 최대 날짜로 설정
    min_date = df['date'].min()
    max_date = df['date'].max()
    
    fig.update_layout(
        title='Detailed Sleep Stages Over Time',
        xaxis_title='Date',
        yaxis_title='Time (HH:MM)',
        xaxis=dict(
            range=[min_date, max_date],
            showgrid=True,
            zeroline=False
        ),
        yaxis=dict(
            tickmode='array',
            tickvals=list(range(0, 24*60, 30)),  # 24시간을 30분 단위로 표시
            ticktext=[f'{int(t/60):02}:{int(t%60):02}' for t in range(0, 24*60, 30)],  # 분 단위를 HH:MM 형식으로 변환
            autorange='reversed',
            showgrid=True,
            zeroline=False,
            range=[24*60, 0]  # y축을 0분(00:00)에서 1440분(24:00)로 설정
        ),
        barmode='stack',
        height=800
    )
    return fig

def create_resting_hr_chart(df):
    import plotly.express as px
    fig = px.line(df, x='date', y='resting_hr', title='Resting Heart Rate Over Time')


    # -1 값을 별도로 표시
    invalid_data = df[df['resting_hr'].isin([-1, -1.0, '-1', '-1.0'])]
    if not invalid_data.empty:
        fig.add_scatter(x=invalid_data['date'], y=invalid_data['resting_hr'], mode='markers', name='Invalid Data (-1)', marker=dict(color='red', size=10))
    return fig, df

def create_heart_rate_chart(df):

    fig = px.line(df, x='datetime', y='value', title='Heart Rate Over Time')
    # -1, -1.0, '-1', '-1.0' 값을 별도로 표시
    invalid_data = df[df['value'].astype(str).isin(['-1', '-1.0'])]
    if not invalid_data.empty:
        fig.add_trace(px.scatter(invalid_data, x='datetime', y='value', color_discrete_sequence=['red']).data[0])
    return fig,df

def create_compliance_chart(df):
    df['compliance'] = df['compliance'].apply(lambda x: x / 2 if x > 1.1 else x)
    fig = px.bar(df, x='date', y='compliance', title='Daily Compliance')
    fig.update_layout(yaxis=dict(tickformat=".1%"))  # 백분율로 표시
    return fig

def create_sleep_summary_donut_chart(df):
    valid_data = df[(df['stages_deep'] != -1) & (df['stages_light'] != -1) & (df['stages_rem'] != -1) & (df['stages_wake'] != -1)]
    total_stages = valid_data[['stages_deep', 'stages_light', 'stages_rem', 'stages_wake']].sum()
    fig = px.pie(names=total_stages.index, values=total_stages.values, hole=0.3, title='Sleep Stages Distribution')
    return fig

def create_sleep_summary_bar_chart(df):
    df_melted = df.melt(id_vars=['date'], value_vars=['stages_deep', 'stages_light', 'stages_rem', 'stages_wake'],
                        var_name='stage', value_name='value')
    fig = px.bar(df_melted, x='date', y='value', color='stage', title='Daily Sleep Stages Summary',
                labels={'value': 'Duration (minutes)', 'stage': 'Sleep Stage'})
    return fig

