# 필요한 라이브러리를 가져옵니다.
import os
import logging
from datetime import date, datetime
import requests
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, request, jsonify # request와 jsonify를 추가합니다.
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# --- 기본 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
seoul_tz = pytz.timezone('Asia/Seoul')


# --- 핵심 기능 함수 (이전과 동일) ---

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

def send_scheduled_meal_message(webhook_url: str, meal_type: str):
    """(스케줄용) 메뉴를 가져와서 Mattermost로 식사 알림 메시지를 전송하는 함수"""
    if not webhook_url:
        return
    
    # 문제가 발생했던 부분을 더 안정적인 코드로 수정했습니다.
    if meal_type == 'lunch':
        column = 2
        message = "🍚 오늘의 점심 메뉴입니다! :chef_kirby:오늘도 맛있게 먹고 힘내보자구..👍:clap_kkihyuck:"
    elif meal_type == 'dinner':
        column = 3
        message = "🌙 오늘의 저녁 메뉴입니다! :chef_kirby: 7,800원의 행복!✨:clap_kkihyuck:"
    else:
        return

    image_url = get_menu_from_sheet(column_index=column)
    
    if image_url:
        payload = {'text': message, 'attachments': [{"fallback": "메뉴 이미지", "image_url": image_url}]}
        bot_username, bot_icon_url = os.getenv('BOT_USERNAME'), os.getenv('BOT_ICON_URL')
        if bot_username: payload['username'] = bot_username
        if bot_icon_url: payload['icon_url'] = bot_icon_url
        
        try:
            requests.post(webhook_url, json=payload, timeout=10).raise_for_status()
            logging.info(f"스케줄된 {meal_type} 메뉴 메시지 전송 성공!")
        except requests.exceptions.RequestException as e:
            logging.error(f"스케줄된 {meal_type} 메뉴 메시지 전송 중 오류: {e}")
    else:
        logging.info(f"스케줄된 오늘의 {meal_type} 메뉴가 없습니다.")


# --- 메인 실행 블록 ---

if __name__ == "__main__":
    app = Flask(__name__)
    scheduler = BackgroundScheduler(timezone=seoul_tz)
    incoming_webhook_url = os.getenv('MATTERMOST_WEBHOOK_URL')

    # 1. 기존의 스케줄 알림 설정
    scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=10, minute=50, args=[incoming_webhook_url, 'lunch'], id='lunch_notification')
    scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=15, minute=5, args=[incoming_webhook_url, 'dinner'], id='dinner_notification')
    logging.info("자동 식사 메뉴 알림이 설정되었습니다.")
    scheduler.start()

    # 2. 명령어 처리를 위한 새로운 경로(route) 추가
    @app.route('/command', methods=['POST'])
    def handle_command():
        """Mattermost에서 보낸 명령어를 받아서 처리하는 함수"""
        data = request.form
        command_token = data.get('token')
        command_text = data.get('text').strip()
        
        expected_token = os.getenv('MATTERMOST_COMMAND_TOKEN')
        if not expected_token or command_token != expected_token:
            return jsonify({'text': '에러: 인증 토큰이 잘못되었습니다.'}), 401

        # 문제가 발생했던 부분을 더 안정적인 코드로 수정했습니다.
        if command_text == '!점심':
            column = 2
            message = "🍚 오늘의 점심 메뉴입니다!"
        elif command_text == '!저녁':
            column = 3
            message = "🌙 오늘의 저녁 메뉴입니다!"
        else:
            return jsonify({})

        image_url = get_menu_from_sheet(column_index=column)
        
        if image_url:
            response_payload = {
                "response_type": "in_channel",
                "text": message,
                "attachments": [{"fallback": "메뉴 이미지", "image_url": image_url}]
            }
        else:
            response_payload = {
                "response_type": "ephemeral",
                "text": f"아직 오늘의 {command_text.replace('!', '')} 메뉴가 등록되지 않았어요! 😅"
            }
            
        return jsonify(response_payload)

    @app.route('/')
    def home():
        return "점심/저녁 메뉴 알림 봇이 실행 중입니다."

    import atexit
    atexit.register(lambda: scheduler.shutdown())
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
