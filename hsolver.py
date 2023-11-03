import requests, os, string, random, asyncio, json, time, jwt, nest_asyncio
from pyppeteer_ghost_cursor import path
from pyppeteer import launch
from PIL import Image, ImageOps
import numpy as np
from keras.models import load_model


class HcaptchaSolver:
    def __init__(self, session):
        nest_asyncio.apply()
        self.session = session
        self.labels = self._load_labels()
        self.model = load_model('keras_model.h5')
        self.repetition = 5
        self.size = (224, 224)

    @staticmethod
    def _load_labels(filename='./labels.txt'):
        with open(filename, 'r', encoding='UTF8') as file:
            return {i: label.strip().split(" ")[1] for i, label in enumerate(file.readlines())}

    def _request(self, method, url, data=None, json=None, headers=None, use_proxy=True):
        session = self.session if use_proxy else requests.session()
        attempts = 3
        while attempts <= 3:
            try:
                return session.request(method, url, data=data, json=json, headers=headers)
            except:
                attempts += 1
        else:
            return False

    async def _get_hsw(self, response):
        url = jwt.decode(response, options={"verify_signature": False})['l']
        version = url.split("https://newassets.hcaptcha.com/c/")[1]
        hsw_content = self._request('GET', url + "/hsw.js").text
        attempts = 3
        for _ in range(attempts):
            try:
                browser = await launch({"headless": True}, handleSIGINT=False, handleSIGTERM=False, handleSIGHUP=False)
                page = await browser.newPage()
                await page.addScriptTag({'content': hsw_content})
                result = await page.evaluate(f'hsw("{response}")')
                await browser.close()
                return result, version
            except:
                try:
                    await browser.close()
                except:
                    continue
        return None, None

    def solve(self, site_key, host):
        start_coords = {'x': 100, 'y': 100}
        end_coords = {'x': 600, 'y': 700}
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        headers = {
            'Authority': "hcaptcha.com",
            'Accept': "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Content-Type": "application/x-www-form-urlencoded",
            'Origin': "https://newassets.hcaptcha.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "User-Agent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.70 Whale/3.13.131.27 Safari/537.36'
        }

        for _ in range(self.repetition):
            try:
                timestamp = int(time.time() * 1000 + random.uniform(30, 120))

                response = self._request('GET', f'https://hcaptcha.com/checksiteconfig?host={host}&sitekey={site_key}&sc=1&swa=1', headers=headers)
                if not response or response.status_code != 200:
                    continue

                mouse_movements = [[int(p['x']), int(p['y']), int(time.time() * 1000 + random.uniform(2000, 5000))] for p in path(start_coords, end_coords)]
                hsw_val, version_val = loop.run_until_complete(self._get_hsw(response.json()['c']['req']))
                if not hsw_val:
                    continue

                task_payload = {
                    'sitekey': site_key,
                    'host': host,
                    'hl': 'ko',
                    'motionData': json.dumps({
                        'st': timestamp,
                        'dct': timestamp,
                        'mm': mouse_movements
                    }),
                    'n': hsw_val,
                    'v': version_val,
                    'c': json.dumps(response.json()['c'])
                }
                task_response = self._request('POST', f"https://hcaptcha.com/getcaptcha?s={site_key}", data=task_payload, headers=headers)

                if not task_response or task_response.status_code != 200:
                    continue

                task_response_data = task_response.json()
                topic = task_response_data['requester_question']['ko']
                task_key = task_response_data['key']

                answers = {}
                local_files = [img for img in os.listdir(f'./imgs')]

                for img_task in task_response_data['tasklist']:
                    while True:
                        filename = "".join([random.choice(string.ascii_lowercase + string.digits) for _ in range(random.randint(5, 10))])
                        if not filename + ".png" in local_files:
                            break

                    img_key = img_task['task_key']
                    resp = self._request('GET', img_task['datapoint_uri'], use_proxy=False)
                    if not resp:
                        continue

                    with open(f'./imgs/{filename}.png', 'wb') as f:
                        f.write(resp.content)

                    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
                    image = Image.open(f'./imgs/{filename}.png')
                    image = ImageOps.fit(image, self.size, Image.ANTIALIAS)
                    data[0] = (np.asarray(image).astype(np.float32) / 127.0) - 1
                    prediction = self.model.predict(data)
                    max_index = prediction[0].argmax()
                    label = self.labels[max_index]

                    if 0.5 >= prediction[0][max_index] or label not in topic:
                        answers[img_key] = 'false'
                    else:
                        answers[img_key] = 'true'

                verification_payload = {
                    'job_mode': task_response_data['request_type'],
                    "answers": answers,
                    "serverdomain": host,
                    "sitekey": site_key,
                    "motionData": json.dumps({
                        'st': timestamp,
                        'dct': timestamp,
                        'mm': mouse_movements
                    }),
                    "n": hsw_val,
                    "v": version_val,
                    "c": json.dumps(response.json()['c'])
                }

                verification_response = self._request('POST', f"https://hcaptcha.com/checkcaptcha/{task_key}?s={site_key}", json=verification_payload, headers=headers)

                if not verification_response:
                    continue

                if verification_response.json().get("generated_pass_UUID", None) is not None:
                    return verification_response.json()['generated_pass_UUID']
                else:
                    continue
            except:
                continue
        return False


if __name__ == "__main__":
    session = requests.session()
    # Optional: Update with proxy details if needed
    # session.proxies.update({"http": "proxy_address", 'https': "proxy_address"})

    print(HcaptchaSolver(session).solve('site_key', 'host'))  # Ex.'4c672d35-0701-42b2-88c3-78380b0db560', 'discord.com'
