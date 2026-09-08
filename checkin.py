import os
import json
import time
import random
import requests

# 接口域名（根据你实际使用的修改：glados.cloud / glados.space）
BASE_DOMAIN = "glados.cloud"
CHECKIN_URL = f"https://{BASE_DOMAIN}/api/user/checkin"
STATUS_URL = f"https://{BASE_DOMAIN}/api/user/status"
POINTS_URL = f"https://{BASE_DOMAIN}/api/user/points"
EXCHANGE_URL = f"https://{BASE_DOMAIN}/api/user/exchange"

# ========== 兑换配置 ==========
EXCHANGE_REQUIRED_POINTS = 500  # 触发兑换的积分门槛
EXCHANGE_PLAN = "plan100"       # 兑换的套餐标识
# ==============================

HEADERS_BASE = {
    "origin": f"https://{BASE_DOMAIN}",
    "referer": f"https://{BASE_DOMAIN}/console/checkin",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "content-type": "application/json;charset=UTF-8",
}
PAYLOAD = {"token": BASE_DOMAIN}
TIMEOUT = 10


def push_telegram(bot_token: str, chat_id: str, title: str, content: str):
    if not bot_token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    text = f"{title}\n\n{content}"
    if len(text) > 4000:
        text = text[:3990] + "..."
    data = {"chat_id": chat_id, "text": text}
    try:
        resp = requests.post(url, json=data, timeout=TIMEOUT)
        if resp.status_code == 200 and safe_json(resp).get("ok"):
            print("✅ Telegram 推送成功")
        else:
            print(f"⚠️ Telegram 推送失败: HTTP {resp.status_code} | {resp.text}")
    except Exception as e:
        print(f"⚠️ Telegram 推送异常: {e}")


def push_all(bot_token: str, chat_id: str, title: str, content: str):
    if bot_token and chat_id:
        push_telegram(bot_token, chat_id, title, content)
    else:
        print("⚠️ 未配置 Telegram 推送")


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
        points = "-"
        total_points_val = None
        total_points_str = "-"
        days = "-"
        exchange_result = "未兑换"

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

            # 2. 查询账号状态
            s = session.get(STATUS_URL, headers=headers, timeout=TIMEOUT)
            sj = safe_json(s).get("data") or {}
            email = sj.get("email", email)
            if sj.get("leftDays") is not None:
                days = f"{int(float(sj['leftDays']))} 天"

            # 3. 查询总积分（严格校验数字有效性）
            p = session.get(POINTS_URL, headers=headers, timeout=TIMEOUT)
            pj = safe_json(p)
            raw_points = pj.get("points")
            if raw_points is not None:
                try:
                    total_points_val = int(float(raw_points))
                    total_points_str = f"{total_points_val}"
                except (ValueError, TypeError):
                    total_points_val = None

            # 4. 积分达标才执行兑换（双重校验，避免异常）
            if total_points_val is not None and total_points_val >= EXCHANGE_REQUIRED_POINTS:
                try:
                    exchange_payload = {"planType": EXCHANGE_PLAN}
                    e = session.post(
                        EXCHANGE_URL,
                        headers=headers,
                        data=json.dumps(exchange_payload),
                        timeout=TIMEOUT
                    )
                    ej = safe_json(e)
                    if ej.get("code") == 0:
                        exchange_result = f"🎁 兑换成功({EXCHANGE_PLAN})"
                    else:
                        exchange_msg = ej.get("message", "未知错误")
                        exchange_result = f"⚠️ 兑换失败:{exchange_msg}"
                except Exception:
                    exchange_result = "⚠️ 兑换异常"

        except Exception:
            fail += 1
            status = "❌ 异常"

        # 拼接输出：未兑换则不显示兑换相关内容
        line_parts = [
            f"{idx}. {email}",
            status,
            f"本次获得{points}积分",
            f"总积分:{total_points_str}",
            f"剩余:{days}"
        ]
        if exchange_result != "未兑换":
            line_parts.append(exchange_result)
        
        lines.append(" | ".join(line_parts))
        time.sleep(random.uniform(1, 2))

    title = f"GLaDOS 签到完成 ✅{ok} ❌{fail} 🔁{repeat}"
    content = "\n".join(lines)
    print(content)
    
    push_all(bot_token, chat_id, title, content)


if __name__ == "__main__":
    main()
