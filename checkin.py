name: GLaDOS Auto Checkin
on:
  workflow_dispatch:
  schedule:
    - cron: '0 4 * * *'
jobs:
  checkin:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests
      - name: Run checkin
        run: python checkin.py
        env:
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
          COOKIES: ${{ secrets.COOKIES }}

      # 新增：工作流保活，防止60天无活动被禁用
      - name: Keep alive
        uses: liskin/gh-workflow-keepalive@v1 

      # 新增：自动清理7天前的成功运行记录
      - name: Delete workflow runs
        uses: Mattraks/delete-workflow-runs@v2
        with:
          token: ${{ github.token }}
          repository: ${{ github.repository }}
          retain_days: 7
          keep_minimum_runs: 7
          delete_run_by_conclusion_pattern: success
