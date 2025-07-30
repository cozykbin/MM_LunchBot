# 필요한 라이브러리를 가져옵니다.
import os
import logging
from datetime import date, datetime
import requests
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 기본 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
seoul_tz = pytz.timezone('Asia/Seoul')


# --- 핵심 기능 함수 ---

def get_google_creds():
    """Railway 변수 또는 로컬 파일에서 구글 인증 정보를 가져오는 함수"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    creds_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json_str:
        logging.info("Railway 환경 변수에서 구글 인증 정보를 로드합니다.")
        try:
            creds_json = json.loads(creds_json_str)
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        except json.JSONDecodeError:
            logging.error("Railway의 GOOGLE_CREDENTIALS_JSON 변수가 올바른 JSON 형식이 아닙니다! 값을 다시 확인해주세요.")
            raise
    elif os.path.exists('credentials.json'):
        logging.info("로컬 credentials.json 파일에서 구글 인증 정보를 로드합니다.")
        return ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    else:
        raise FileNotFoundError("구글 인증 정보를 찾을 수 없습니다. Railway 변수 또는 credentials.json 파일을 확인해주세요.")

def get_menu_from_sheet(column_index: int):
    """구글 시트에서 오늘 날짜의 메뉴 이미지 URL을 가져오는 함수"""
    try:
        creds = get_google_creds()
        client = gspread.authorize(creds)
        
        sheet_name = os.getenv('GOOGLE_SHEET_NAME')
        if not sheet_name:
            logging.error("GOOGLE_SHEET_NAME이 .env 파일 또는 Railway 변수에 설정되지 않았습니다!")
            return None

        sheet = client.open(sheet_name).sheet1
        today_str = date.today().strftime("%Y-%m-%d")
        
        cell = sheet.find(today_str, in_column=1)
        if not cell:
            logging.info(f"{today_str} 날짜의 메뉴가 시트에 없습니다.")
            return None
            
        image_url = sheet.cell(cell.row, column_index).value
        if image_url:
            logging.info(f"오늘의 메뉴 이미지 URL을 찾았습니다 (열 {column_index}): {image_url}")
            return image_url
        else:
            logging.info(f"오늘의 메뉴가 비어있습니다 (열 {column_index}).")
            return None

    except Exception as e:
        logging.error(f"구글 시트에서 메뉴를 가져오는 중 오류가 발생했습니다: {e}")
        return None

def send_meal_message(webhook_url: str, meal_type: str):
    """메뉴를 가져와서 Mattermost로 식사 알림 메시지를 전송하는 통합 함수 (봇 이름/사진 기능 추가)"""
    if not webhook_url:
        logging.error("MATTERMOST_WEBHOOK_URL이 .env 파일 또는 Railway 변수에 설정되지 않았습니다!")
        return
    
    if meal_type == 'lunch':
        column = 2
        message = "🍚 오늘의 점심 메뉴입니다! 맛있게 드세요!"
    elif meal_type == 'dinner':
        column = 3
        message = "🌙 오늘의 저녁 메뉴입니다! 7,800원의 행복!"
    else:
        return

    image_url = get_menu_from_sheet(column_index=column)
    
    if image_url:
        # 기본 메시지 payload
        payload = {
            'text': message,
            'attachments': [{
                "fallback": f"오늘의 {meal_type} 메뉴 이미지입니다. Mattermost에서 확인해주세요.",
                "image_url": image_url
            }]
        }
        
        # .env 또는 Railway 변수에서 봇 이름과 아이콘 URL을 가져옵니다.
        bot_username = os.getenv('BOT_USERNAME')
        bot_icon_url = os.getenv('BOT_ICON_URL')
        
        if bot_username:
            payload['username'] = bot_username
        if bot_icon_url:
            payload['icon_url'] = bot_icon_url
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logging.info(f"{meal_type} 메뉴 메시지 전송 성공!")
        except requests.exceptions.RequestException as e:
            logging.error(f"{meal_type} 메뉴 메시지 전송 중 오류가 발생했습니다: {e}")
    else:
        logging.info(f"전송할 오늘의 {meal_type} 메뉴가 없습니다.")


# --- 메인 실행 블록 ---

if __name__ == "__main__":
    app = Flask(__name__)
    scheduler = BackgroundScheduler(timezone=seoul_tz)
    webhook_url = os.getenv('MATTERMOST_WEBHOOK_URL')

    # 점심 알림 스케줄 (오전 11시 30분)
    scheduler.add_job(
        send_meal_message, 'cron', day_of_week='mon-fri', hour=11, minute=30,
        args=[webhook_url, 'lunch'], id='lunch_notification'
    )
    logging.info("점심 메뉴 알림이 매주 월-금 11:30에 설정되었습니다.")

    # 저녁 알림 스케줄 (오후 5시 30분)
    scheduler.add_job(
        send_meal_message, 'cron', day_of_week='mon-fri', hour=15, minute=59,
        args=[webhook_url, 'dinner'], id='dinner_notification'
    )
    logging.info("저녁 메뉴 알림이 매주 월-금 17:30에 설정되었습니다.")

    scheduler.start()

    @app.route('/')
    def home():
        return "점심/저녁 메뉴 알림 봇이 실행 중입니다."

    import atexit
    atexit.register(lambda: scheduler.shutdown())
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
