import datetime
import json
import os
import sys
import time

import requests

from email_utils import send_email

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


def get_images_for_entry(entry: dict) -> list:
    """新形式(images: [...])と旧形式(image: "...")の両方に対応"""
    if not entry:
        return []
    if entry.get("images"):
        return entry["images"]
    if entry.get("image"):
        return [entry["image"]]
    return []


def create_media_container(base: str, access_token: str, image_url: str,
                            caption: str = None, is_carousel_item: bool = False) -> str:
    params = {
        "image_url": image_url,
        "access_token": access_token,
    }
    if caption is not None:
        params["caption"] = caption
    if is_carousel_item:
        params["is_carousel_item"] = "true"
    res = requests.post(f"{base}/media", params=params, timeout=30)
    res.raise_for_status()
    return res.json()["id"]


def publish_container(base: str, access_token: str, creation_id: str) -> dict:
    res = requests.post(
        f"{base}/media_publish",
        params={"creation_id": creation_id, "access_token": access_token},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def post_images(account_id: str, access_token: str, image_urls: list, caption: str) -> dict:
    """1枚なら通常投稿、2枚以上ならカルーセル投稿として送る"""
    base = f"https://graph.instagram.com/v21.0/{account_id}"

    if len(image_urls) == 1:
        creation_id = create_media_container(base, access_token, image_urls[0], caption=caption)
        return publish_container(base, access_token, creation_id)

    # カルーセル: まず各画像を子コンテナとして作成
    child_ids = []
    for url in image_urls:
        child_id = create_media_container(base, access_token, url, is_carousel_item=True)
        child_ids.append(child_id)
        time.sleep(1)  # APIへの連続リクエストを避けるための小休止

    # 親コンテナ(カルーセル本体)を作成して公開
    parent_res = requests.post(
        f"{base}/media",
        params={
            "media_type": "CAROUSEL",
            "caption": caption,
            "children": ",".join(child_ids),
            "access_token": access_token,
        },
        timeout=30,
    )
    parent_res.raise_for_status()
    parent_id = parent_res.json()["id"]
    return publish_container(base, access_token, parent_id)


def wait_for_video_ready(base: str, access_token: str, creation_id: str,
                          max_attempts: int = 30, interval_seconds: int = 10) -> None:
    """リール(動画)のサーバー側処理が完了するまで待つ"""
    for _ in range(max_attempts):
        res = requests.get(
            f"https://graph.instagram.com/v21.0/{creation_id}",
            params={"fields": "status_code", "access_token": access_token},
            timeout=30,
        )
        res.raise_for_status()
        status = res.json().get("status_code")
        if status == "FINISHED":
            return
        if status == "ERROR":
            raise RuntimeError("動画の処理中にエラーが発生しました(status_code=ERROR)")
        time.sleep(interval_seconds)
    raise TimeoutError("動画の処理が時間内に完了しませんでした")


def post_reel(account_id: str, access_token: str, video_url: str, caption: str) -> dict:
    """動画(リール)を投稿する"""
    base = f"https://graph.instagram.com/v21.0/{account_id}"
    res = requests.post(
        f"{base}/media",
        params={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": access_token,
        },
        timeout=30,
    )
    res.raise_for_status()
    creation_id = res.json()["id"]
    wait_for_video_ready(base, access_token, creation_id)
    return publish_container(base, access_token, creation_id)


def main() -> None:
    today = get_today_key()
    today_label = DAY_LABELS_JP[today]
    schedule = load_schedule()
    entry = schedule.get(today)
    video_filename = (entry or {}).get("video", "").strip() if entry else ""
    images = get_images_for_entry(entry)

    if not video_filename and not images:
        print(f"{today_label} の投稿予定は登録されていません。スキップします。")
        return

    account_id = os.environ["IG_ACCOUNT_ID"]
    access_token = os.environ["IG_ACCESS_TOKEN"]
    github_repo = os.environ["GITHUB_REPO"]  # 例: "your-name/instagram-weekly-poster"
    caption = entry.get("caption", "")

    try:
        if video_filename:
            video_url = f"https://raw.githubusercontent.com/{github_repo}/main/week/{video_filename}"
            result = post_reel(account_id, access_token, video_url, caption)
            send_email(
                subject=f"[Instagram自動投稿] {today_label}のリール投稿が完了しました",
                body=(
                    f"リール投稿が完了しました。\n\n"
                    f"動画: {video_filename}\n"
                    f"キャプション: {caption}\n"
                    f"投稿ID: {result.get('id')}"
                ),
            )
            print("リール投稿成功:", result)
        else:
            image_urls = [
                f"https://raw.githubusercontent.com/{github_repo}/main/week/{fn}" for fn in images
            ]
            result = post_images(account_id, access_token, image_urls, caption)
            kind = f"カルーセル({len(images)}枚)" if len(images) > 1 else "画像1枚"
            send_email(
                subject=f"[Instagram自動投稿] {today_label}の投稿が完了しました",
                body=(
                    f"投稿が完了しました({kind})。\n\n"
                    f"画像: {', '.join(images)}\n"
                    f"キャプション: {caption}\n"
                    f"投稿ID: {result.get('id')}"
                ),
            )
            print("投稿成功:", result)
    except Exception as e:  # noqa: BLE001
        media_desc = f"動画: {video_filename}" if video_filename else f"画像: {', '.join(images)}"
        send_email(
            subject=f"[Instagram自動投稿] {today_label}の投稿に失敗しました",
            body=(
                f"投稿でエラーが発生しました。\n\n"
                f"エラー内容:\n{e}\n\n"
                f"{media_desc}\n"
                f"キャプション: {caption}"
            ),
        )
        print("投稿失敗:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
