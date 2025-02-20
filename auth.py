import copy
import requests
from HttpClient import HttpClientSingleton

class AuthController:
    _REQ_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '" Not;A Brand";v="99", "Google Chrome";v="91", "Chromium";v="91"',
        "sec-ch-ua-mobile": "?0",
        "Upgrade-Insecure-Requests": "1",
        "Origin": "https://dhlottery.co.kr",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Referer": "https://dhlottery.co.kr/",
        "Sec-Fetch-Site": "same-site",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Accept-Language": "ko,en-US;q=0.9,en;q=0.8,ko-KR;q=0.7",
    }

    _AUTH_CRED = ""


    def __init__(self):
        self.http_client = HttpClientSingleton.get_instance()

    def login(self, user_id: str, password: str):
        assert isinstance(user_id, str)
        assert isinstance(password, str)

        print(f"🔍 로그인 시도: {user_id}")

        default_auth_cred = self._get_default_auth_cred()
        print(f"🛠 기본 인증 정보: {default_auth_cred}")  # 디버깅용

        if not default_auth_cred:
            print("🚨 JSESSIONID를 가져오지 못했습니다.")
            return False

        headers = self._generate_req_headers(default_auth_cred)
        data = self._generate_body(user_id, password)

        res = self._try_login(headers, data)
    
        print(f"📡 로그인 응답 코드: {res.status_code}")
        print(f"📜 응답 헤더: {res.headers}")
        print(f"🍪 응답 쿠키: {res.cookies}")
        print(f"📝 응답 본문 (일부): {res.text[:500]}")  # 너무 긴 응답을 줄이기

        if res.status_code == 200 and "JSESSIONID" in res.cookies:
            self._update_auth_cred(res)
            print("✅ 로그인 성공!")
            return True
    
        print("❌ 로그인 실패")
        return False


    def add_auth_cred_to_headers(self, headers: dict) -> str:
        assert type(headers) == dict

        copied_headers = copy.deepcopy(headers)
        copied_headers["Cookie"] = f"JSESSIONID={self._AUTH_CRED}"
        return copied_headers

    def _get_default_auth_cred(self):
        res = self.http_client.get(
            "https://dhlottery.co.kr/gameResult.do?method=byWin&wiselog=H_C_1_1"
        )

        return self._get_j_session_id_from_response(res)

    def _get_j_session_id_from_response(self, res: requests.Response):
        assert type(res) == requests.Response

        for cookie in res.cookies:
            if cookie.name == "JSESSIONID":
                return cookie.value

        raise KeyError("JSESSIONID cookie is not set in response")

    def _generate_req_headers(self, j_session_id: str):
        assert type(j_session_id) == str

        copied_headers = copy.deepcopy(self._REQ_HEADERS)
        copied_headers["Cookie"] = f"JSESSIONID={j_session_id}"
        return copied_headers

    def _generate_body(self, user_id: str, password: str):
        assert type(user_id) == str
        assert type(password) == str

        return {
            "returnUrl": "https://dhlottery.co.kr/common.do?method=main",
            "userId": user_id,
            "password": password,
            "checkSave": "on",
            "newsEventYn": "",
        }

    def _try_login(self, headers: dict, data: dict):
        assert type(headers) == dict
        assert type(data) == dict

        res = self.http_client.post(
            "https://www.dhlottery.co.kr/userSsl.do?method=login",
            headers=headers,
            data=data,
        )
        return res

    def _update_auth_cred(self, res: requests.Response) -> None:
        assert isinstance(res, requests.Response)

        # 1️⃣ 먼저 `res.cookies`에서 찾아보기
        new_j_session_id = None
        for cookie in res.cookies:
            if cookie.name == "JSESSIONID":
                new_j_session_id = cookie.value
                break

        # 2️⃣ Set-Cookie 헤더에서도 찾아보기
        if not new_j_session_id and "Set-Cookie" in res.headers:
            import re
            match = re.search(r'JSESSIONID=([^;]+)', res.headers["Set-Cookie"])

            matches = re.findall(r'JSESSIONID=([^;]+)', res.headers.get("Set-Cookie", ""))
            if matches:
                new_j_session_id = matches[-1]  # 가장 마지막 쿠키 사용  
            # if match:
            #     new_j_session_id = match.group(1)

        if new_j_session_id:
            self._AUTH_CRED = new_j_session_id
            print(f"🔑 로그인 성공: 새로운 JSESSIONID 설정됨 → {new_j_session_id}")
        else:
            print("🚨 로그인 실패: JSESSIONID를 찾을 수 없음")


