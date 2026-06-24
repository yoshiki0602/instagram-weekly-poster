import datetime
import json
import os
import sys

import requests

from email_utils import send_email

GRAPH_API_VERSION = "v20.0"
DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_LABELS_JP = {
    "mon": "月曜日", "tue": "火曜日", "wed": "水曜日", "thu": "木曜日",
    "fri": "金曜日", "sat": "土曜日", "sun": "日曜日",
}


def get_today_key() -> str:
    return DAY_KEYS[datetime.datetime.now().weekday()]


def load_schedule() -> dict:
    schedule_path = os.path.join(os.path.dirname(__file__), "week", "schedule.json")
    with open(schedule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def post_image(account_id: str, access_token: str, image_url: str, caption: str) -> dict:
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{account_id}"

    # 1. メディアコンテナを作成
    media_res = requests.post(
        f"{base}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    media_res.raise_for_status()
    creation_id = media_res.json()["id"]

    # 2. コンテナを公開
    publish_res = requests.post(
        f"{base}/media_publish",
        params={
            "creation_id": creation_id,
            "access_token": access_token,
        },
        timeout=30,
    )
    publish_res.raise_for_status()
    return publish_res.json()


def main() -> None:
    today = get_today_key()
    today_label = DAY_LABELS_JP[today]
    schedule = load_schedule()
    entry = schedule.get(today)

    if not entry or not entry.get("image"):
        print(f"{today_label} の投稿予定は登録されていません。スキップします。")
        return

    account_id = os.environ["IG_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    github_repo = os.environ["GITHUB_REPO"]  # 例: "your-name/instagram-weekly-poster"

    filename = entry["image"]
    caption = entry.get("caption", "")
    image_url = f"https://raw.githubusercontent.com/{github_repo}/main/week/{filename}"

    try:
        result = post_image(account_id, access_token, image_url, caption)
        send_email(
            subject=f"[Instagram自動投稿] {today_label}の投稿が完了しました",
            body=(
                f"投稿が完了しました。\n\n"
                f"画像: {filename}\n"
                f"キャプション: {caption}\n"
                f"投稿ID: {result.get('id')}"
            ),
        )
        print("投稿成功:", result)
    except Exception as e:  # noqa: BLE001
        send_email(
            subject=f"[Instagram自動投稿] {today_label}の投稿に失敗しました",
            body=(
                f"投稿でエラーが発生しました。\n\n"
                f"エラー内容:\n{e}\n\n"
                f"画像: {filename}\n"
                f"キャプション: {caption}\n"
                f"画像URL: {image_url}"
            ),
        )
        print("投稿失敗:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
