# 필요한 라이브러리를 가져옵니다.
import os
import logging
from datetime import date, datetime, timedelta
import requests
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import atexit

# --- 기본 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()
seoul_tz = pytz.timezone('Asia/Seoul')


# --- 핵심 기능 함수 ---

def get_google_creds():
    """Railway 환경 변수 또는 로컬 파일에서 구글 인증 정보를 가져오는 함수"""
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    creds_json_str = os.getenv('GOOGLE_CREDENTIALS_JSON')
    if creds_json_str:
        logging.info("Railway 환경 변수에서 구글 인증 정보를 로드합니다.")
        try:
            creds_json = json.loads(creds_json_str)
            return ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
        except json.JSONDecodeError:
            logging.error("Railway의 GOOGLE_CREDENTIALS_JSON 변수가 올바른 JSON 형식이 아닙니다!")
            raise
    elif os.path.exists('credentials.json'):
        logging.info("로컬 credentials.json 파일에서 구글 인증 정보를 로드합니다.")
        return ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    else:
        raise FileNotFoundError("구글 인증 정보를 찾을 수 없습니다.")

def get_menu_from_sheet(column_index: int, day_offset: int = 0):
    """구글 시트에서 특정 날짜(오늘/내일)의 메뉴 이미지 URL을 가져오는 함수"""
    try:
        creds = get_google_creds()
        client = gspread.authorize(creds)
        sheet = client.open(os.getenv('GOOGLE_SHEET_NAME')).sheet1
        
        target_date = date.today() + timedelta(days=day_offset)
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        cell = sheet.find(target_date_str, in_column=1)
        if not cell:
            logging.info(f"{target_date_str} 날짜의 메뉴가 시트에 없습니다.")
            return None
            
        image_url = sheet.cell(cell.row, column_index).value
        if image_url:
            logging.info(f"{target_date_str}의 메뉴 이미지 URL을 찾았습니다 (열 {column_index}): {image_url}")
            return image_url
        else:
            logging.info(f"{target_date_str}의 메뉴가 비어있습니다 (열 {column_index}).")
            return None
    except Exception as e:
        logging.error(f"구글 시트에서 메뉴를 가져오는 중 오류: {e}")
        return None

def get_weekly_menu():
    """[최적화] 이번 주(월-금) 메뉴 전체를 가져와 마크다운 표로 만드는 함수"""
    try:
        creds = get_google_creds()
        client = gspread.authorize(creds)
        sheet = client.open(os.getenv('GOOGLE_SHEET_NAME')).sheet1
        
        # 시트 전체 데이터를 한 번에 가져와서 처리 (API 호출 최소화)
        all_data = sheet.get_all_records()
        
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        weekly_menu_data = []

        for i in range(5): # 월(0) ~ 금(4)
            day = start_of_week + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            day_name = ["월", "화", "수", "목", "금"][i]
            
            # 가져온 데이터에서 오늘 날짜에 해당하는 행을 찾습니다.
            row_data = next((row for row in all_data if row.get('Date') == day_str), None)
            
            if row_data:
                lunch = f"[메뉴 보기]({row_data['LunchImageURL']})" if row_data.get('LunchImageURL') else "미등록"
                dinner = f"[메뉴 보기]({row_data['DinnerImageURL']})" if row_data.get('DinnerImageURL') else "미등록"
            else:
                lunch, dinner = "미등록", "미등록"
            
            weekly_menu_data.append(f"| **{day_name}** ({day.day}) | {lunch} | {dinner} |")
            
        return "\n".join(weekly_menu_data)
    except Exception as e:
        logging.error(f"주간 메뉴 조회 중 오류: {e}")
        return None

def send_scheduled_meal_message(webhook_url: str, meal_type: str):
    """(스케줄용) 만족도 투표 버튼이 포함된 식사 알림 메시지를 전송하는 함수"""
    if not webhook_url: return
    
    if meal_type == 'lunch': column, message = 2,  "🍚 오늘의 점심 메뉴입니다! :chef_kirby: 오늘도 맛있게 먹고 힘내보자구..👍"
    elif meal_type == 'dinner': column, message = 3, "🌙 오늘의 저녁 메뉴입니다! :chef_kirby:  7,800원의 행복!✨"
    else: return

    image_url = get_menu_from_sheet(column_index=column)
    
    if image_url:
        today_str = date.today().strftime("%Y-%m-%d")
        app_url = os.getenv('YOUR_APP_URL')
        
        actions = []
        if app_url:
            actions = [
                {"id": "rateGood", "name": "👍 좋았어요!", "integration": {"url": f"{app_url}/vote", "context": {"meal_type": meal_type, "date": today_str, "rating": "good"}}},
                {"id": "rateBad", "name": "👎 별로였어요", "integration": {"url": f"{app_url}/vote", "context": {"meal_type": meal_type, "date": today_str, "rating": "bad"}}}
            ]

        payload = {'text': message, 'attachments': [{"fallback": "메뉴 이미지", "image_url": image_url, "actions": actions}]}
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


# --- Flask 앱 및 라우팅 설정 ---

app = Flask(__name__)

@app.route('/')
def home():
    return "🍽️ 식사 메뉴 알림 봇이 실행 중입니다. 🚀"

@app.route('/command', methods=['POST'])
def handle_command():
    """Mattermost 슬래시 명령어를 처리하는 함수"""
    data = request.form
    command_token = data.get('token')
    command_text = data.get('text').strip()
    
    expected_token = os.getenv('MATTERMOST_COMMAND_TOKEN')
    if not expected_token or command_token != expected_token:
        return jsonify({'text': '에러: 인증 토큰이 잘못되었습니다.'}), 401
    
    # --- 주간 메뉴 명령어 처리 ---
    if command_text == '!주간메뉴':
        weekly_table_content = get_weekly_menu()
        if weekly_table_content:
            table_header = "| 요일 | 점심 | 저녁 |\n|:---:|:---:|:---:|\n"
            full_table = f"### 📅 이번 주 메뉴 요약\n" + table_header + weekly_table_content
            response_payload = {"response_type": "in_channel", "text": full_table}
        else:
            response_payload = {"response_type": "ephemeral", "text": "주간 메뉴를 불러오는 데 실패했습니다. 😥"}
        return jsonify(response_payload)

    # --- 오늘/내일 메뉴 명령어 처리 ---
    day_offset = 0
    command_base = command_text
    if '내일' in command_text:
        day_offset = 1
        command_base = command_text.replace('내일', '').strip()
        message_prefix = "📅 내일"
    else:
        message_prefix = "🍚 오늘"

    if '점심' in command_base: column, meal_name = 2, "점심"
    elif '저녁' in command_base: column, meal_name = 3, "저녁"
    else:
        help_text = ("명령어를 확인해주세요! 👀\n"
                     "`!점심`, `!저녁`: 오늘 메뉴\n"
                     "`!내일점심`, `!내일저녁`: 내일 메뉴\n"
                     "`!주간메뉴`: 이번 주 메뉴 요약")
        return jsonify({"response_type": "ephemeral", "text": help_text})

    image_url = get_menu_from_sheet(column_index=column, day_offset=day_offset)
    
    if image_url:
        response_payload = {"response_type": "in_channel", "text": f"{message_prefix} {meal_name} 메뉴입니다!", "attachments": [{"fallback": "메뉴 이미지", "image_url": image_url}]}
    else:
        response_payload = {"response_type": "ephemeral", "text": f"아직 {message_prefix} {meal_name} 메뉴가 등록되지 않았어요! 😅"}
    return jsonify(response_payload)

@app.route('/vote', methods=['POST'])
def handle_vote():
    """만족도 투표 버튼 클릭을 처리하는 함수"""
    data = request.json
    context = data.get('context', {})
    meal_date, meal_type, rating, user_name = context.get('date'), context.get('meal_type'), context.get('rating'), data.get('user_name')

    if not all([meal_date, meal_type, rating, user_name]):
        return jsonify({"update": {"message": "오류: 투표 정보가 부족합니다."}}), 400

    try:
        creds = get_google_creds()
        client = gspread.authorize(creds)
        sheet = client.open(os.getenv('GOOGLE_SHEET_NAME')).sheet1

        cell = sheet.find(meal_date, in_column=1)
        if not cell:
            return jsonify({"update": {"message": "오류: 해당 날짜의 메뉴를 찾을 수 없습니다."}})

        col_to_update = 4 if meal_type == 'lunch' else 5
        current_votes = sheet.cell(cell.row, col_to_update).value or ""
        
        if user_name in current_votes:
             return jsonify({"update": {"message": f"{user_name}님, 이미 투표하셨어요! 😉"}})

        new_vote = f"👍({user_name})" if rating == "good" else f"👎({user_name})"
        sheet.update_cell(cell.row, col_to_update, (current_votes + " " + new_vote).strip())

        return jsonify({"update": {"message": f"{user_name}님, 소중한 피드백 감사합니다! 🥳"}})
    except Exception as e:
        logging.error(f"투표 처리 중 오류: {e}")
        return jsonify({"update": {"message": "오류가 발생해 투표를 기록하지 못했습니다."}})


# --- 메인 실행 블록 ---

if __name__ == "__main__":
    scheduler = BackgroundScheduler(timezone=seoul_tz)
    incoming_webhook_url = os.getenv('MATTERMOST_WEBHOOK_URL')

    if incoming_webhook_url:
        scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=10, minute=50, args=[incoming_webhook_url, 'lunch'], id='lunch_notification')
        scheduler.add_job(send_scheduled_meal_message, 'cron', day_of_week='mon-fri', hour=16, minute=50, args=[incoming_webhook_url, 'dinner'], id='dinner_notification')
        logging.info("자동 식사 메뉴 알림이 설정되었습니다.")
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown())
    else:
        logging.warning("MATTERMOST_WEBHOOK_URL이 설정되지 않아 스케줄 알림이 비활성화되었습니다.")

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

