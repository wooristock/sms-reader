import subprocess
import json
import csv
from datetime import datetime
from PyQt5 import QtWidgets, QtCore
import sys

class SMSApp(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('메시지 추출 프로그램')

        self.layout = QtWidgets.QVBoxLayout()

        self.max_count_label = QtWidgets.QLabel('최대 불러오는 개수 (최신순):')
        self.layout.addWidget(self.max_count_label)

        self.max_count_input = QtWidgets.QSpinBox()
        self.max_count_input.setMaximum(10000)
        self.max_count_input.setValue(1000)
        self.layout.addWidget(self.max_count_input)

        self.fetch_button = QtWidgets.QPushButton('메시지 불러오기')
        self.fetch_button.clicked.connect(self.fetch_sms_list)
        self.layout.addWidget(self.fetch_button)

        self.export_button = QtWidgets.QPushButton('엑셀 추출하기')
        self.export_button.clicked.connect(self.export_sms_list)
        self.layout.addWidget(self.export_button)

        self.sms_list_view = QtWidgets.QTextEdit()
        self.sms_list_view.setReadOnly(True)
        self.layout.addWidget(self.sms_list_view)

        self.setLayout(self.layout)

    def fetch_sms_list(self):
        max_count = self.max_count_input.value()
        sms_json = get_sms_list(max_count)
        if sms_json:
            formatted_sms_list = format_sms_list(sms_json)
            self.sms_list_view.setPlainText(formatted_sms_list)
            save_sms_list_to_file(sms_json, "sms_list.csv")
        else:
            self.sms_list_view.setPlainText("No result found.")

    def export_sms_list(self):
        max_count = self.max_count_input.value()
        sms_json = get_sms_list(max_count)
        if sms_json:
            save_sms_list_to_file(sms_json, "sms_list.csv")
        else:
            self.sms_list_view.setPlainText("No result found.")

def get_sms_list(max_count=1000):
    try:
        # adb가 설치되어 있는지 확인
        adb_check = subprocess.run(['adb', 'version'], capture_output=True, text=True)
        if adb_check.returncode != 0:
            raise RuntimeError("ADB가 설치되어 있지 않거나 PATH에 없습니다.")

        # 연결된 디바이스가 있는지 확인
        devices_check = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
        if devices_check.returncode != 0 or "device" not in devices_check.stdout.splitlines()[1:]:
            raise RuntimeError("연결된 디바이스가 없습니다.")

        # adb 명령어를 사용하여 SMS 목록을 가져옴
        result = subprocess.run(['adb', 'shell', 'content', 'query', '--uri', 'content://sms/'], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"SMS 목록을 가져오는 중 오류 발생: {result.stderr}")

        # 결과를 가공하여 JSON 형식으로 변환
        sms_list = []
        for line in result.stdout.splitlines():
            if len(sms_list) >= max_count:
                break
            sms = {}
            for item in line.split(','):
                if '=' in item:  # '=' 문자가 있는지 확인
                    key, value = item.split('=', 1)  # 수정: '='로 나누는 부분에서 최대 2개의 값만 분리
                    sms[key.strip()] = value.strip()
                else:
                    # '=' 문자가 없는 경우 처리
                    print(f"잘못된 항목: {item}")

            if sms.get('type') == '1':  # 'type'이 1인 경우는 받은 메시지
                sms_list.append(sms)

        if not sms_list or sms_list == [{}]:  # 리스트가 비어 있거나 [{}]인 경우 확인
            print("항목이 없습니다.")
            return None  # 또는 적절한 기본값 반환

        return json.dumps(extract_sms_list(sms_list), ensure_ascii=False, indent=2)

    except Exception as e:
        QtWidgets.QMessageBox.critical(None, "오류", f"adb 실행 실패: {str(e)}")
        return None

def extract_sms_list(sms_list):
    extracted_list = []
    for sms in sms_list:
        extracted_sms = {
            'address': sms.get('address'),
            'date': sms.get('date'),
            'body': sms.get('body')
        }
        extracted_list.append(extracted_sms)
    return extracted_list

def format_sms_list(sms_json):
    sms_list = json.loads(sms_json)
    formatted_list = ""
    for sms in sms_list:
        phone_number = sms.get('address')
        if phone_number:
            phone_number = phone_number.replace('+82', '010')
        else:
            phone_number = "Unknown"  # 주소가 없는 경우 기본값 설정

        date = datetime.fromtimestamp(int(sms['date']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        body = sms['body']
        formatted_list += f"전화번호: {phone_number} | 시간: {date} | 내용: {body}\n"
    return formatted_list

def save_sms_list_to_file(sms_list, filename):
    # JSON 문자열을 파이썬 객체로 변환
    sms_list = json.loads(sms_list)
    
    # date를 기준으로 내림차순 정렬
    sms_list.sort(key=lambda x: x['date'], reverse=True)
    
    # 가장 최근 메시지의 시간을 파일 이름으로 사용
    if sms_list:
        latest_date = sms_list[0]['date']
        filename = f"{datetime.fromtimestamp(int(latest_date)/1000).strftime('%Y%m%d_%H%M%S')}.csv"
    
    # CSV 파일로 저장
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=['전화번호', '시간', '내용'])
        writer.writeheader()
        for sms in sms_list:
            # 전화번호가 None인 경우 처리 추가
            phone_number = sms.get('address')
            if phone_number:
                phone_number = phone_number.replace('+82', '010')
            else:
                phone_number = "Unknown"  # 기본값 설정

            writer.writerow({
                '전화번호': phone_number,
                '시간': sms['date'],
                '내용': sms['body']
            })

if __name__ == "__main__":
    
    app = QtWidgets.QApplication(sys.argv)
    sms_app = SMSApp()
    sms_app.show()
    sys.exit(app.exec_())
