import subprocess
import json
import csv
from datetime import datetime

def get_sms_list():
    # adb 명령어를 사용하여 SMS 목록을 가져옴
    result = subprocess.run(['adb', 'shell', 'content', 'query', '--uri', 'content://sms/'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error fetching SMS list: {result.stderr}")
        return None

    # 결과를 가공하여 JSON 형식으로 변환
    sms_list = []
    for line in result.stdout.splitlines():
        sms = {}
        for item in line.split(','):
            if '=' in item:  # '=' 문자가 있는지 확인
                key, value = item.split('=')
                sms[key.strip()] = value.strip()
            else:
                # '=' 문자가 없는 경우 처리
                print(f"Invalid item: {item}")
								
        if sms.get('type') == '1':  # 'type'이 1인 경우는 받은 메시지
            sms_list.append(sms)

    if not sms_list or sms_list == [{}]:  # 리스트가 비어 있거나 [{}]인 경우 확인
        print("No items found.")
        return None  # 또는 적절한 기본값 반환

    return json.dumps(extract_sms_list(sms_list), ensure_ascii=False, indent=4)


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
            # 전화번호에서 +82를 010으로 대체
            phone_number = sms['address'].replace('+82', '010')
            writer.writerow({
                '전화번호': phone_number,
                '시간': sms['date'],
                '내용': sms['body']
            })

if __name__ == "__main__":
    sms_json = get_sms_list()
    if sms_json:
        save_sms_list_to_file(sms_json, "sms_list.csv")
        # print(sms_json)
    else:
        print("No result found.")
