import datetime
import json
import requests

from datetime import timedelta
from enum import Enum

from bs4 import BeautifulSoup as BS

import auth
from HttpClient import HttpClientSingleton
	
class Lotto645Mode(Enum):
    AUTO = 1
    MANUAL = 2
    BUY = 10 
    CHECK = 20

class Lotto645:
    BUY_URL = "https://ol.dhlottery.co.kr/olotto/game/execBuy.do"  # URL 추가
    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://ol.dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        # "Referer": "https://ol.dhlottery.co.kr/olotto/game/game645.do",
        "Referer": "https://www.dhlottery.co.kr/login.do?method=login",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def buy_lotto645(self, auth_ctrl: auth.AuthController, cnt: int, mode: Lotto645Mode, manual_numbers=None) -> dict:
        assert type(auth_ctrl) == auth.AuthController
        assert type(cnt) == int and 1 <= cnt <= 5
        assert type(mode) == Lotto645Mode

        headers = self._generate_req_headers(auth_ctrl)
        requirements = self._getRequirements(headers)

        if mode == Lotto645Mode.AUTO:
            data = self._generate_body_for_auto_mode(cnt, requirements)
        else:
            data = self._generate_body_for_manual(cnt, requirements, manual_numbers)
	
        body = self._try_buying(headers, data)
        print(f"🎯 Lotto Purchase Response: {body}")

        if "resultMsg" in body and body["resultMsg"] == "SUCCESS":
            print("✅ 로또 구매 성공!")
        else:
            print("❌ 로또 구매 실패! Response:", body)

        self._show_result(body)
        return body

    def _generate_req_headers(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        return auth_ctrl.add_auth_cred_to_headers(self._REQ_HEADERS)

    def _generate_body_for_auto_mode(self, cnt: int, requirements: list) -> dict:
        SLOTS = ["A", "B", "C", "D", "E"]
        return {
            "round": self._get_round(),
            "direct": "auto",
            "nBuyAmount": str(1000 * cnt),
            "param": json.dumps(
                [{"genType": "0", "arrGameChoiceNum": None, "alpabet": slot} for slot in SLOTS[:cnt]]
            ),
            'ROUND_DRAW_DATE': requirements[1],
            'WAMT_PAY_TLMT_END_DT': requirements[2],
            "gameCnt": cnt
        }

    def _generate_body_for_manual(self, cnt: int, requirements: list, manual_numbers: list) -> dict:
	    assert type(cnt) == int and 1 <= cnt <= 5
	
	    import random
	    SLOTS = ["A", "B", "C", "D", "E"]  # 최대 5개 슬롯
	    all_numbers = list(range(1, 46))  # 1~45까지 숫자
	
	    param_list = []
	    for i in range(cnt):
	        selected_numbers = manual_numbers[i] if manual_numbers and i < len(manual_numbers) else None
	        
	        if selected_numbers is None:
	            # 완전 자동
	            generated_numbers = random.sample(all_numbers, 6)
	        else:
	            # 반자동 (나머지 숫자 자동 생성)
	            remaining_count = 6 - len(selected_numbers)
	            available_numbers = list(set(all_numbers) - set(selected_numbers))
	            generated_numbers = selected_numbers + random.sample(available_numbers, remaining_count)
	            
	        param_list.append({
	            "genType": "1",  # 1: 수동 선택
	            "arrGameChoiceNum": generated_numbers,
	            "alpabet": SLOTS[i]
	        })
	    
	    return {
	        "round": self._get_round(),
	        "direct": requirements[0],
	        "nBuyAmount": str(1000 * cnt),
	        "param": json.dumps(param_list),
	        "ROUND_DRAW_DATE": requirements[1],
	        "WAMT_PAY_TLMT_END_DT": requirements[2],
	        "gameCnt": cnt
	    }

    def _getRequirements(self, headers: dict) -> list: 
        org_headers = headers.copy()

        headers["Referer"] ="https://ol.dhlottery.co.kr/olotto/game/game645.do"
        headers["Content-Type"] = "application/json; charset=UTF-8"
        headers["X-Requested-With"] ="XMLHttpRequest"


		#no param needed at now
        res = self.http_client.post(
            url="https://ol.dhlottery.co.kr/olotto/game/egovUserReadySocket.json", 
            headers=headers
        )
        
        direct = json.loads(res.text)["ready_ip"]
        

        res = self.http_client.post(
            url="https://ol.dhlottery.co.kr/olotto/game/game645.do", 
            headers=org_headers
        )
        html = res.text
        soup = BS(
            html, "html5lib"
        )
        draw_date = soup.find("input", id="ROUND_DRAW_DATE").get('value')
        tlmt_date = soup.find("input", id="WAMT_PAY_TLMT_END_DT").get('value')

        return [direct, draw_date, tlmt_date]

    def _get_round(self) -> str:
        res = self.http_client.get("https://www.dhlottery.co.kr/common.do?method=main")
        html = res.text
        soup = BS(
            html, "html5lib"
        )  # 'html5lib' : in case that the html don't have clean tag pairs
        last_drawn_round = int(soup.find("strong", id="lottoDrwNo").text)
        return str(last_drawn_round + 1)

    def get_balance(self, auth_ctrl: auth.AuthController) -> str: 

        headers = self._generate_req_headers(auth_ctrl)
        res = self.http_client.post(
            url="https://dhlottery.co.kr/userSsl.do?method=myPage", 
            headers=headers
        )

        html = res.text
        soup = BS(
            html, "html5lib"
        )
        balance = soup.find("p", class_="total_new").find('strong').text
        return balance
        
    def _try_buying(self, headers: dict, data: dict) -> dict:
        assert isinstance(headers, dict)
        assert isinstance(data, dict)

        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"

        res = self.http_client.post(
            "https://ol.dhlottery.co.kr/olotto/game/execBuy.do",
            headers=headers,
            data=data,
        )
        res.encoding = "utf-8"

        print("🔍 Response Status Code:", res.status_code)
        print("🔍 Response Text:", res.text[:5000])  # 처음 5000자만 출력
        try:
            response_text = res.content.decode("utf-8")  # ✅ 탭 대신 공백 4칸 적용
            return json.loads(response_text)
        except json.JSONDecodeError:
            print("❌ JSONDecodeError: 응답이 JSON 형식이 아닙니다.")
            return {"error": "Invalid response from server", "response": res.text}


    # def _try_buying(self, headers, data):
	   #  res = requests.post(self.BUY_URL, headers=headers, data=data)
	
	   #  # 응답이 JSON 형식인지 확인하기 위해 출력
	   #  print("🔍 Response Status Code:", res.status_code)
	   #  print("🔍 Response Text:", res.text[:5000])  # 처음 5000자만 출력
	
	   #  try:
	   #      return json.loads(res.text)
	   #  except json.JSONDecodeError:
	   #      print("❌ JSONDecodeError: 응답이 JSON 형식이 아닙니다.")
	   #      return {"error": "Invalid response from server", "response": res.text}

    def check_winning(self, auth_ctrl: auth.AuthController) -> dict:
        assert type(auth_ctrl) == auth.AuthController

        headers = self._generate_req_headers(auth_ctrl)

        parameters = self._make_search_date()

        data = {
            "nowPage": 1, 
            "searchStartDate": parameters["searchStartDate"],
            "searchEndDate": parameters["searchEndDate"],
            "winGrade": 2,
            "lottoId": "LO40", 
            "sortOrder": "DESC"
        }

        result_data = {
            "data": "no winning data"
        }

        try:
            res = self.http_client.post(
                "https://dhlottery.co.kr/myPage.do?method=lottoBuyList",
                headers=headers,
                data=data
            )

            html = res.text
            soup = BS(html, "html5lib")

            winnings = soup.find("table", class_="tbl_data tbl_data_col").find_all("tbody")[0].find_all("td")

            get_detail_info = winnings[3].find("a").get("href")

            order_no, barcode, issue_no = get_detail_info.split("'")[1::2]
            url = f"https://dhlottery.co.kr/myPage.do?method=lotto645Detail&orderNo={order_no}&barcode={barcode}&issueNo={issue_no}"

            response = self.http_client.get(url)

            soup = BS(response.text, "html5lib")

            lotto_results = []

            for li in soup.select("div.selected li"):
                label = li.find("strong").find_all("span")[0].text.strip()
                status = li.find("strong").find_all("span")[1].text.strip().replace("낙첨","0등")
                nums = li.select("div.nums > span")

                status = " ".join(status.split())

                formatted_nums = []
                for num in nums:
                    ball = num.find("span", class_="ball_645")
                    if ball:
                        formatted_nums.append(f"✨{ball.text.strip()}")
                    else:
                        formatted_nums.append(num.text.strip())

                lotto_results.append({
                    "label": label,
                    "status": status,
                    "result": formatted_nums
                })

            if len(winnings) == 1:
                return result_data

            result_data = {
                "round": winnings[2].text.strip(),
                "money": winnings[6].text.strip(),
                "purchased_date": winnings[0].text.strip(),
                "winning_date": winnings[7].text.strip(),
                "lotto_details": lotto_results
            }
        except:
            pass

        return result_data
    
    def _make_search_date(self) -> dict:
        today = datetime.datetime.today()
        today_str = today.strftime("%Y%m%d")
        weekago = today - timedelta(days=7)
        weekago_str = weekago.strftime("%Y%m%d")
        return {
            "searchStartDate": weekago_str,
            "searchEndDate": today_str
        }

    def _show_result(self, body: dict) -> None:
        assert type(body) == dict

        if body.get("loginYn") != "Y":
            return

        result = body.get("result", {})
        if result.get("resultMsg", "FAILURE").upper() != "SUCCESS":    
            return
