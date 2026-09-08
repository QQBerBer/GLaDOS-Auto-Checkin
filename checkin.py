import os
import json
import time
import random
import requests

CHECKIN_URL = "https://glados.cloud/api/user/checkin"
STATUS_URL = "https://glados.cloud/api/user/status"
POINTS_URL = "https://glados.cloud/api/user/points"  # 新增：总积分接口

HEADERS_BASE = {
    "origin": "https://glados.cloud",
    "referer": "https://glados.cloud/console/checkin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "content-type": "application/json;charset=UTF-8",
}
PAYLOAD = {"token": "glados.cloud"}
TIMEOUT = 10


def push_telegram(bot_token: str, chat_id: str, title: str, content: str):
    """推送消息到 Telegram Bot"""
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = f"{title}\n\n{content}"
    # Telegram 单条消息上限 4096 字符，做截断避免发送失败。
    if len(text) > 4000:
        text = text[:3990] + "..."
    data = {
        "chat_id": chat_id,
        "text": text,
    }
    try:
        resp = requests.post(url, json=data, timeout=TIMEOUT)
        if resp.status_code == 200 and safe_json(resp).get("ok"):
            print("✅ Telegram 推送成功")
        else:
            print(f"⚠️ Telegram 推送失败: HTTP {resp.status_code} | {resp.text}")
    except Exception as e:
        print(f"⚠️ Telegram 推送异常: {e}")


def push_all(bot_token: str, chat_id: str, title: str, content: str):
    """推送到 Telegram（如果已配置）"""
    if bot_token and chat_id:
        push_telegram(bot_token, chat_id, title, content)
    else:
        print("⚠️ 未配置 Telegram 推送，请在 Secrets 中配置 TG_BOT_TOKEN 和 TG_CHAT_ID")


def safe_json(resp):
    try:
        return resp.json()
    except Exception:
        return {}


def main():
    bot_token = os.getenv("TG_BOT_TOKEN", "")
    chat_id = os.getenv("TG_CHAT_ID", "")
    cookies_env = os.getenv("COOKIES", "")
    cookies = [c.strip() for c in cookies_env.split("&") if c.strip()]

    if not cookies:
        push_all(bot_token, chat_id, "GLaDOS 签到", "❌ 未检测到 COOKIES")
        return

    session = requests.Session()
    ok = fail = repeat = 0
    lines = []

    for idx, cookie in enumerate(cookies, 1):
        headers = dict(HEADERS_BASE)
        headers["cookie"] = cookie
        email = "unknown"
        points = "-"       # 本次签到获得积分
        total_points = "-" # 账号总积分（新增）
        days = "-"

        try:
            # 1. 执行签到
            r = session.post(
                CHECKIN_URL,
                headers=headers,
                data=json.dumps(PAYLOAD),
                timeout=TIMEOUT,
            )
            j = safe_json(r)
            msg = j.get("message", "")
            msg_lower = msg.lower()

            if "got" in msg_lower:
                ok += 1
                points = j.get("points", "-")
                status = "✅ 成功"
            elif "repeat" in msg_lower or "already" in msg_lower:
                repeat += 1
                status = "🔁 已签到"
            else:
                fail += 1
                status = "❌ 失败"

            # 2. 查询账号状态（剩余天数、邮箱）
            s = session.get(STATUS_URL, headers=headers, timeout=TIMEOUT)
            sj = safe_json(s).get("data") or {}
            email = sj.get("email", email)
            if sj.get("leftDays") is not None:
                days = f"{int(float(sj['leftDays']))} 天"

            # 3. 查询账号总积分（新增步骤）
            p = session.get(POINTS_URL, headers=headers, timeout=TIMEOUT)
            pj = safe_json(p)
            if pj.get("points") is not None:
                total_points = f"{int(float(pj['points']))}"

        except Exception:
            fail += 1
            status = "❌ 异常"

        # 输出行加入总积分
        lines.append(f"{idx}. {email} | {status} | 本次+{points} | 总积分:{total_points} | 剩余:{days}")
        time.sleep(random.uniform(1, 2))

    title = f"GLaDOS 签到完成 ✅{ok} ❌{fail} 🔁{repeat}"
    content = "\n".join(lines)
    print(content)
    
    push_all(bot_token, chat_id, title, content)


if __name__ == "__main__":
    main()
