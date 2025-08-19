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
    # (이전 send_meal_message 함수와 거의 동일)
    if not webhook_url: return
    
    if meal_type == 'lunch': column, message = 2, "# 필요한 라이브러리를 가져옵니다.
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
    # (이전 send_meal_message 함수와 거의 동일)
    if not webhook_url: return
    
    if meal_type == 'lunch': column, message = 2, "🍚 오늘의 점심 메뉴입니다! :chef_kirby: 오늘도 맛있게 먹고 힘내보자구..:clap_kkihyuck:👍"
    elif meal_type == 'dinner': column, message = 3, "🌙 오늘의 저녁 메뉴입니다!:chef_kirby: 7,800원의 행복!:clap_kkihyuck:✨"
    else: return

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
    scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=15, minute=00, args=[incoming_webhook_url, 'dinner'], id='dinner_notification')
    logging.info("자동 식사 메뉴 알림이 설정되었습니다.")
    scheduler.start()

    # 2. 명령어 처리를 위한 새로운 경로(route) 추가
    @app.route('/command', methods=['POST'])
    def handle_command():
        """Mattermost에서 보낸 명령어를 받아서 처리하는 함수"""
        # Mattermost가 보낸 데이터에서 토큰과 텍스트(명령어)를 추출합니다.
        data = request.form
        command_token = data.get('token')
        command_text = data.get('text').strip()
        
        # 보안을 위해 Mattermost에서 설정한 토큰과 일치하는지 확인합니다.
        expected_token = os.getenv('MATTERMOST_COMMAND_TOKEN')
        if not expected_token or command_token != expected_token:
            return jsonify({'text': '에러: 인증 토큰이 잘못되었습니다.'}), 401

        # 명령어에 따라 점심 또는 저녁 메뉴를 가져옵니다.
        if command_text == '!점심':
            column, message = 2, "🍚 오늘의 점심 메뉴입니다!"
        elif command_text == '!저녁':
            column, message = 3, "🌙 오늘의 저녁 메뉴입니다!"
        else:
            # 아는 명령어가 아니면 아무것도 응답하지 않습니다.
            return jsonify({})

        image_url = get_menu_from_sheet(column_index=column)
        
        # 응답할 메시지를 Mattermost가 알아듣는 JSON 형식으로 만듭니다.
        if image_url:
            response_payload = {
                "response_type": "in_channel", # 채널 전체에 보이도록 설정
                "text": message,
                "attachments": [{"fallback": "메뉴 이미지", "image_url": image_url}]
            }
        else:
            response_payload = {
                "response_type": "ephemeral", # 명령어 입력한 사람에게만 보이도록 설정
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
"
    elif meal_type == 'dinner': column, message = 3, "🌙 오늘의 저녁 메뉴입니다! 7,800원의 행복!✨"
    else: return

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
    scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=14, minute=45, args=[incoming_webhook_url, 'dinner'], id='dinner_notification')
    logging.info("자동 식사 메뉴 알림이 설정되었습니다.")
    scheduler.start()

    # 2. 명령어 처리를 위한 새로운 경로(route) 추가
    @app.route('/command', methods=['POST'])
    def handle_command():
        """Mattermost에서 보낸 명령어를 받아서 처리하는 함수"""
        # Mattermost가 보낸 데이터에서 토큰과 텍스트(명령어)를 추출합니다.
        data = request.form
        command_token = data.get('token')
        command_text = data.get('text').strip()
        
        # 보안을 위해 Mattermost에서 설정한 토큰과 일치하는지 확인합니다.
        expected_token = os.getenv('MATTERMOST_COMMAND_TOKEN')
        if not expected_token or command_token != expected_token:
            return jsonify({'text': '에러: 인증 토큰이 잘못되었습니다.'}), 401

        # 명령어에 따라 점심 또는 저녁 메뉴를 가져옵니다.
        if command_text == '!점심':
            column, message = 2, "🍚 오늘의 점심 메뉴입니다!"
        elif command_text == '!저녁':
            column, message = 3, "🌙 오늘의 저녁 메뉴입니다!"
        else:
            # 아는 명령어가 아니면 아무것도 응답하지 않습니다.
            return jsonify({})

        image_url = get_menu_from_sheet(column_index=column)
        
        # 응답할 메시지를 Mattermost가 알아듣는 JSON 형식으로 만듭니다.
        if image_url:
            response_payload = {
                "response_type": "in_channel", # 채널 전체에 보이도록 설정
                "text": message,
                "attachments": [{"fallback": "메뉴 이미지", "image_url": image_url}]
            }
        else:
            response_payload = {
                "response_type": "ephemeral", # 명령어 입력한 사람에게만 보이도록 설정
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
