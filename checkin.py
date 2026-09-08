import os
import json
import time
import random
import requests
import sys

# ========== 配置区 ==========
BASE_DOMAIN = "glados.space"  # 改成你实际使用的域名：glados.cloud / glados.space
EXCHANGE_REQUIRED_POINTS = 500
EXCHANGE_PLAN = "plan100"
# ============================

CHECKIN_URL = f"https://{BASE_DOMAIN}/api/user/checkin"
STATUS_URL = f"https://{BASE_DOMAIN}/api/user/status"
POINTS_URL = f"https://{BASE_DOMAIN}/api/user/points"
EXCHANGE_URL = f"https://{BASE_DOMAIN}/api/user/exchange"

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
TIMEOUT = 15


def push_telegram(bot_token, chat_id, title, content):
    if not bot_token or not chat_id:
        return
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        text = f"{title}\n\n{content}"
        if len(text) > 4000:
            text = text[:3990] + "..."
        data = {"chat_id": chat_id, "text": text}
        resp = requests.post(url, json=data, timeout=TIMEOUT)
        if resp.status_code == 200 and resp.json().get("ok"):
            print("✅ Telegram 推送成功")
        else:
            print(f"⚠️ Telegram 推送失败: {resp.text}")
    except Exception as e:
        print(f"⚠️ Telegram 推送异常: {e}")


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
        print("❌ 未检测到 COOKIES")
        push_telegram(bot_token, chat_id, "GLaDOS 签到", "❌ 未检测到 COOKIES")
        return

    session = requests.Session()
    ok = fail = repeat = 0
    lines = []

    for idx, cookie in enumerate(cookies, 1):
        headers = dict(HEADERS_BASE)
        headers["cookie"] = cookie
        email = "unknown"
        points = "-"
        total_points_str = "-"
        total_points_val = None
        days = "-"
        exchange_result = ""
        status = "❌ 异常"

        try:
            # 1. 签到
            try:
                r = session.post(
                    CHECKIN_URL, headers=headers,
                    data=json.dumps(PAYLOAD), timeout=TIMEOUT
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
                    status = f"❌ 失败:{msg[:20]}"
            except Exception as e:
                fail += 1
                status = f"❌ 签到异常:{str(e)[:20]}"

            # 2. 查询状态
            try:
                s = session.get(STATUS_URL, headers=headers, timeout=TIMEOUT)
                sj = safe_json(s).get("data") or {}
                email = sj.get("email", email)
                if sj.get("leftDays") is not None:
                    days = f"{int(float(sj['leftDays']))} 天"
            except Exception:
                pass

            # 3. 查询总积分
            try:
                p = session.get(POINTS_URL, headers=headers, timeout=TIMEOUT)
                pj = safe_json(p)
                raw_p = pj.get("points")
                if raw_p is not None:
                    total_points_val = int(float(raw_p))
                    total_points_str = f"{total_points_val}"
            except Exception:
                pass

            # 4. 积分达标自动兑换
            if total_points_val is not None and total_points_val >= EXCHANGE_REQUIRED_POINTS:
                try:
                    e = session.post(
                        EXCHANGE_URL, headers=headers,
                        data=json.dumps({"planType": EXCHANGE_PLAN}),
                        timeout=TIMEOUT
                    )
                    ej = safe_json(e)
                    if ej.get("code") == 0:
                        exchange_result = f"🎁 兑换成功({EXCHANGE_PLAN})"
                    else:
                        exchange_result = f"⚠️ 兑换失败:{ej.get('message','未知')[:15]}"
                except Exception as ex:
                    exchange_result = f"⚠️ 兑换异常:{str(ex)[:15]}"

        except Exception as e:
            fail += 1
            status = f"❌ 全局异常:{str(e)[:20]}"

        # 拼接输出
        parts = [
            f"{idx}. {email}",
            status,
            f"本次获得{points}积分",
            f"总积分:{total_points_str}",
            f"剩余:{days}"
        ]
        if exchange_result:
            parts.append(exchange_result)
        lines.append(" | ".join(parts))

        time.sleep(random.uniform(1, 3))

    title = f"GLaDOS 签到完成 ✅{ok} ❌{fail} 🔁{repeat}"
    content = "\n".join(lines)
    print(content)
    push_telegram(bot_token, chat_id, title, content)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"💥 脚本顶级异常: {e}")
        # 即使顶级异常也强制正常退出，避免工作流标红
        sys.exit(0)
