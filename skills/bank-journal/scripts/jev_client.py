"""TypeSafe AI の JEV（System One モデル）を呼び出す最小限のクライアント。

公式SDK（typesafe-sdk）と同じ HTTP API（POST /v1/systemone）を、追加ライブラリなしで使う。
APIキーは環境変数 TYPESAFE_API_KEY、またはスキルフォルダの jev_config.json の "api_key" に置く。
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"
CONFIG_PATH = Path(__file__).resolve().parent.parent / "jev_config.json"


class JevUnavailable(Exception):
    pass


class JevClient:
    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL, model: str = DEFAULT_MODEL, timeout: float = 10.0):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    @classmethod
    def from_environment(cls) -> "JevClient | None":
        config = {}
        if CONFIG_PATH.exists():
            config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        key = (os.environ.get("TYPESAFE_API_KEY") or config.get("api_key") or "").strip()
        if not key:
            return None
        return cls(
            key,
            base_url=os.environ.get("TYPESAFE_BASE_URL") or config.get("base_url") or DEFAULT_BASE_URL,
            model=os.environ.get("TYPESAFE_DEFAULT_MODEL") or config.get("model") or DEFAULT_MODEL,
        )

    def choice(self, state, instructions: str, criteria: dict[str, str]) -> dict:
        """選択肢から1つ選ばせる。戻り値は {"choice", "confidence", "probabilities"}。"""
        body = {
            "state": state,
            "model": self.model,
            "questions": {"answer": {"type": "choice", "instructions": instructions, "criteria": criteria}},
        }
        answer = self._post(body)["answers"]["answer"]
        if answer.get("type") != "choice" or answer.get("choice") not in criteria:
            raise JevUnavailable(f"JEVの応答が想定外です: {answer}")
        return answer

    def _post(self, body: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + "/v1/systemone",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        last_error = None
        for _ in range(2):  # 通信エラー時に1回だけ再試行
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:200]
                if e.code in (401, 403):
                    raise JevUnavailable(f"JEVのAPIキーが無効か、利用権限がありません（HTTP {e.code}）: {detail}")
                last_error = f"HTTP {e.code}: {detail}"
                if e.code < 500 and e.code != 429:
                    break
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = str(e)
        raise JevUnavailable(f"JEVに接続できません: {last_error}")
