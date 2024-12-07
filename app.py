from flask import Flask, render_template, request
import os
import time
from urllib.request import urlopen
import csv
import struct
from datetime import datetime, timedelta
import requests
import re  # 정규 표현식 사용을 위한 import


app = Flask(__name__)

# ===========현재 시각 기준 서울특별시 온도================
domain = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm5.php?"
obs = "obs=TA&"
tm2 = "tm2=" + datetime.now().strftime("%Y%m%d%H%M") + "&"
stn_id = "stn=108&"
option = "disp=0&help=0&"
auth = "authKey=mUwDsefKRcSMA7HnysXE6g"
# ========================================================

# ================== 3일 예보 서울특별시 ==================
domain2 = "https://apihub.kma.go.kr/api/typ01/url/fct_afs_dl.php?"
reg = "reg=11B10101&"                                              # 서울 예보구역 코드
disp2 = "disp=0&"
help2 = "help=0&"
# ========================================================


# 현재 날짜와 시간 구하기
today = datetime.now()

# 현재 시간을 기준으로 발표 시각 설정
current_hour = today.hour

if current_hour < 6:
    base_time = today.replace(hour=18, minute=0, second=0, microsecond=0) - timedelta(days=1)
elif current_hour < 18:
    base_time = today.replace(hour=6, minute=0, second=0, microsecond=0)
else:
    base_time = today.replace(hour=18, minute=0, second=0, microsecond=0)


tmfc1 = f"tmfc1={(base_time - timedelta(hours=12)).strftime('%Y%m%d%H')}&"
tmfc2 = f"tmfc2={base_time.strftime('%Y%m%d%H')}&"
# ========================================================

# ==================== 현재시각 서울특별시 온도 ====================
def get_today_weather():
    try:
        # 현재 시각
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute

        # 디렉토리와 파일 경로 설정
        directory = "today_weather"
        file_name = os.path.join(directory, "today_weather_sync.csv")

        # 디렉토리 생성
        if not os.path.exists(directory):
            os.makedirs(directory)

        # 파일이 이미 존재하는 경우 == 불필요한 요청을 줄이기 위함
        if os.path.exists(file_name):
            # 파일 생성 시간 확인
            file_creation_time = datetime.fromtimestamp(os.path.getmtime(file_name))
            file_hour = file_creation_time.hour
            file_minute = file_creation_time.minute

            # 파일이 최신 데이터인지 확인 (정각 기준)
            if file_hour == current_hour or (file_hour == current_hour - 1 and current_minute < 60):
                if file_creation_time.minute < 20 and now.minute < 20:
                    print("파일이 최신입니다. 기존 데이터를 사용합니다.")
                    return file_name, None  # 기존 파일 경로 반환

        # 새로운 요청 수행
        print("새로운 데이터를 요청합니다.")

        # 실행 시간 측정 시작
        start_time = time.time()

        # URL로부터 바이너리 데이터를 받아옴
        with urlopen(domain + obs + stn_id + option + auth) as f:
            binary_data = f.read()

        text_data = binary_data.decode('euc-kr')  # EUC-KR로 디코딩

        # 데이터 저장
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(text_data)

        # 실행 시간 측정 종료
        end_time = time.time()

        # 걸린 시간 출력
        execution_time = end_time - start_time
        return file_name, execution_time

    except Exception as e:
        print(f"Error: {e}")
        return str(e), None



def get_forecast_weather():
    try:
        # 현재 시각
        now = datetime.now()

        # 디렉토리와 파일 경로 설정
        directory = "forecast_3_weather"
        file_name = os.path.join(directory, "forecast_data.csv")

        # 디렉토리 생성
        if not os.path.exists(directory):
            os.makedirs(directory)

        # 06시 기준의 날짜
        today_6am = now.replace(hour=6, minute=0, second=0, microsecond=0)

        # 파일이 이미 존재하는 경우
        if os.path.exists(file_name):
            # 파일 생성 시간 확인
            file_creation_time = datetime.fromtimestamp(os.path.getmtime(file_name))

            # 파일이 오늘 06시 이후에 생성되었으면 요청하지 않음
            if file_creation_time >= today_6am:
                print("파일이 최신입니다. 기존 데이터를 사용합니다.")
                return file_name, None  # 기존 파일 경로 반환

        # 새로운 요청 수행
        print("새로운 데이터를 요청합니다.")

        # 실행 시간 측정 시작
        start_time = time.time()

        # URL로부터 바이너리 데이터를 받아옴
        with urlopen(domain2 + reg + tmfc1 + tmfc2 + disp2 + help2 + auth) as f:
            binary_data = f.read()
        print(domain2 + reg + tmfc1 + tmfc2 + disp2 + help2 + auth)

        # EUC-KR로 디코딩하여 텍스트 데이터로 변환
        text_data = binary_data.decode('euc-kr')

        # 데이터 저장
        with open(file_name, 'w', encoding='utf-8') as file:
            file.write(text_data)

        # 실행 시간 측정 종료
        end_time = time.time()

        # 걸린 시간 출력
        execution_time = end_time - start_time
        return file_name, execution_time

    except Exception as e:
        print(f"Error: {e}")
        return str(e), None
    

def extract_avg_temperature(data):
    """
    Extracts the average temperature from the data by parsing through the CSV content.
    """
    # Remove unnecessary tags to get the real data
    clean_data = re.sub(r'#START7777|#7777END', '', data, flags=re.DOTALL)

    # Split the data into lines and process each line
    lines = clean_data.strip().splitlines()

    temperatures = []
    
    for line in lines:
        # Skip comment lines
        if line.startswith('#') or not line.strip():
            continue
        
        # Split the line by commas
        columns = line.split(',')
        
        # Ensure there are enough columns (at least 11 for temperature data)
        if len(columns) > 10:
            avg_temperature = columns[10]  # The 11th column contains the temperature
            temperatures.append(float(avg_temperature))
    
    return temperatures


def calculate_daily_avg_temperature(current_date):
    """
    Fetches the data for the selected date and calculates the average temperature.
    """
    try:
        # Format the date for the KMA API
        tm = current_date.strftime('%Y%m%d')

        # Build the URL for fetching data
        url = f"https://apihub.kma.go.kr/api/typ01/url/kma_sfcdd.php?tm={tm}&stn=108&help=0&authKey=mUwDsefKRcSMA7HnysXE6g"
        
        # Fetch the data from the URL
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"Failed to fetch data. HTTP Status: {response.status_code}")
            return None
        
        data = response.text
        print("API 응답 데이터:", data)  # 응답 데이터 디버깅
        
        # Extract the average temperatures from the fetched data
        temperatures = extract_avg_temperature(data)
        
        if not temperatures:
            print("No temperature data found.")
            return None

        # Calculate the average temperature
        avg_temperature = sum(temperatures) / len(temperatures)
        return round(avg_temperature, 2)
    
    except Exception as e:
        print(f"Error while calculating daily average temperature: {e}")
        return None

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%d%H%M")
        formatted_date = date_obj.strftime("%Y년 %m월 %d일 %H시")
        return formatted_date
    except Exception as e:
        print(f"Error formatting date: {e}")
        return date_str



def extract_temperature(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith('#') or line == '':  # 주석이나 빈 줄은 무시
                    continue
                elif line.startswith('2024'):  # 날짜로 시작하는 유효 데이터 줄
                    parts = line.split()
                    date = parts[0]  # 날짜 정보
                    val = parts[-1]  # 마지막 값 (VAL)
                    formatted_date = format_date(date)
                    return formatted_date, float(val)
    except Exception as e:
        print(f"Error: {e}")
        None, None


def extract_forecast_data_with_period(file_name):
    try:
        with open(file_name, "r", encoding="utf-8") as f:
            lines = f.readlines()
            result = []
            for line in lines:
                if line.startswith("#") or line.strip() == "":
                    continue  # 주석 또는 빈 줄 제외
                parts = line.split()  # 공백 기준으로 나누기

                # 필요한 데이터만 포함한 행 확인 (16개 이상의 파트가 있어야 함)
                if len(parts) >= 16:
                    try:
                        NE = int(parts[4])  # 구간 번호
                        if NE >= 2:  # 구간 번호가 2 이상만 처리
                            TM_EF = parts[2]  # 발효시각
                            hour = int(TM_EF[8:10])  # 시간 추출
                            period = "오전" if hour == 0 else "오후" if hour == 12 else "기타"  # 시간대 설정

                            TA = parts[12]    # 기온
                            ST = parts[13]    # 강수확률
                            PREP = parts[15]  # 강수유무
                            WF = parts[16].strip('"')  # 예보 상태 (따옴표 제거)

                            # 결과 저장
                            result.append([f"{TM_EF[:8]} {hour:02d}:00 ({period})", TA, ST, PREP, WF])
                    except (ValueError, IndexError) as e:
                        print(f"Error processing line: {line}. Error: {e}")
            return result
    except Exception as e:
        print(f"Error reading file {file_name}: {e}")
        return []

def default_unpack_data(packed_data):                   # 기본 데이터 언패킹 방법. 입맛에 따라 바꿀 수 있음 ex) unpack_temp()
    try:
        # 패킹된 데이터를 언패킹
        (packed_value,) = struct.unpack('>Q', packed_data)
        
        # 날짜 복원
        date_packed = (packed_value >> 35) & 0x7FFFFFFFF
        year = (date_packed >> 18) + 2000
        month = (date_packed >> 14) & 0xF
        day = (date_packed >> 9) & 0x1F
        hour = (date_packed >> 4) & 0x1F
        minute = (date_packed & 0xF) << 1
        date = f"{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}"

        # 온도 복원
        temp_packed = (packed_value >> 24) & 0x7FF
        temp = (temp_packed / 10.0) - 40.0

        # 풍속 복원
        wind_speed_packed = (packed_value >> 13) & 0x7FF
        wind_speed = wind_speed_packed / 10.0

        # 풍향 복원
        wind_pos_packed = (packed_value >> 4) & 0x1FF
        wind_pos = wind_pos_packed

        # 전운량 복원
        Is_weather_packed = packed_value & 0xF
        Is_weather = Is_weather_packed

        return date, temp, wind_speed, wind_pos, Is_weather
    except Exception as e:
        print(f"데이터 언패킹 오류: {e}")
        return None, None, None, None, None
    
# 언패킹 함수
def unpack_temp(packed_data):
    try:
        # 8바이트씩 읽어 언패킹
        (packed_value,) = struct.unpack('>Q', packed_data)
        
        # 날짜 복원
        date_packed = (packed_value >> 35) & 0x7FFFFFFFF
        year = (date_packed >> 18) + 2000
        month = (date_packed >> 14) & 0xF
        day = (date_packed >> 9) & 0x1F
        hour = (date_packed >> 4) & 0x1F
        minute = (date_packed & 0xF) << 1
        date = f"{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}"

        # 온도 복원
        temp_packed = (packed_value >> 24) & 0x7FF
        temp = (temp_packed / 10.0) - 40.0

        return date, temp
    except Exception as e:
        print(f"데이터 언패킹 오류: {e}, packed_data: {packed_data}")
        return None, None

# 월별 평균 온도를 계산하는 함수
def get_monthly_avg_temperature(current_date):
    year = current_date.year
    month = current_date.month
    directory = os.path.join(os.getcwd(), 'packing', str(year))
    
    if not os.path.exists(directory):
        print(f"디렉토리 없음: {directory}")
        return None

    total_temp = 0
    count = 0

    # 월별 데이터 파일 읽기
    file_name = os.path.join(directory, f"{year}{month:02d}.bin")
    if not os.path.exists(file_name):
        print(f"파일 없음: {file_name}")
        return None

    with open(file_name, "rb") as f:
        binary_data = f.read()

        # 8바이트씩 읽어서 언패킹
        for i in range(0, len(binary_data), 8):
            packed_data = binary_data[i:i+8]
            date_str, temp = unpack_data(packed_data)
            if date_str and temp is not None:
                total_temp += temp
                count += 1

    if count == 0:
        print("온도 데이터가 없습니다.")
        return None

    avg_temp = total_temp / count
    return round(avg_temp, 2)  # 평균 온도 반환

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_weather', methods=['POST'])
def get_weather():
    file_name, execution_time = get_today_weather()
    if file_name:
        date, temperature = extract_temperature(file_name)
        if temperature is not None:
            formatted_date = format_date(date)
            return render_template('index.html', date=formatted_date, temperature=temperature, execution_time=execution_time)
    return render_template('index.html', error="Failed to get weather data")

@app.route('/get_avg_temperature', methods=['POST'])
def get_avg_temperature():
    try:
        date_str = request.form['tm']
        current_date = datetime.strptime(date_str, '%Y%m%d')
        avg_temp = calculate_daily_avg_temperature(current_date)

        if avg_temp is not None:
            formatted_date = current_date.strftime('%Y년 %m월 %d일')
            return render_template('index.html', avg_temp=avg_temp, date=formatted_date)
        else:
            return render_template('index.html', error="Failed to calculate average temperature.")
    except Exception as e:
        print(f"Error fetching average temperature: {e}")
        return render_template('index.html', error="An error occurred while fetching the data.")

@app.route('/get_forecast', methods=['POST'])
def get_forecast():
    file_name, execution_time = get_forecast_weather()
    if file_name:
        forecast_data = extract_forecast_data_with_period(file_name)
        if forecast_data:
            return render_template('index.html', forecast=forecast_data)
    return render_template('index.html', error="Failed to get forecast data")


if __name__ == '__main__':
    app.run(debug=True)