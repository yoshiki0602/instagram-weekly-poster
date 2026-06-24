import json
import os

from email_utils import send_email

DAY_LABELS_JP_ORDER = [
    ("mon", "月曜日"), ("tue", "火曜日"), ("wed", "水曜日"), ("thu", "木曜日"),
    ("fri", "金曜日"), ("sat", "土曜日"), ("sun", "日曜日"),
]


def load_schedule() -> dict:
    schedule_path = os.path.join(os.path.dirname(__file__), "week", "schedule.json")
    with open(schedule_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    schedule = load_schedule()

    lines = [
        "今週の投稿予定です。内容に問題がなければそのままで大丈夫です。",
        "画像やキャプションを変更したい場合は、week/schedule.json と week/ フォルダの画像を更新して",
        "GitHubリポジトリにpushしてください(その日の自動投稿が実行される前まで反映できます)。",
        "",
    ]

    missing_days = []

    for day_key, label in DAY_LABELS_JP_ORDER:
        entry = schedule.get(day_key)
        if entry and entry.get("image"):
            caption = entry.get("caption", "")
            caption_preview = caption if len(caption) <= 40 else caption[:40] + "..."
            lines.append(f"■ {label}: {entry['image']}")
            lines.append(f"   キャプション: {caption_preview}")
        else:
            lines.append(f"■ {label}: (未登録)")
            missing_days.append(label)

    if missing_days:
        lines.append("")
        lines.append(f"※ 未登録の曜日: {', '.join(missing_days)} ※画像未設定の日は投稿がスキップされます。")

    send_email(
        subject="[Instagram自動投稿] 今週の投稿予定リマインダー",
        body="\n".join(lines),
    )
    print("リマインダーメールを送信しました。")


if __name__ == "__main__":
    main()
