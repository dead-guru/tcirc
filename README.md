# TCIRC

Scrape telegram channels and send message to irc channel.


## Setup:
1) Install deps using `pip3 install -r requirements.txt`
2) Run manually `python3 main.py` and provide all Telegram account information to bot for session creation.
3) Setup cron like `*/5 * * * * cd /root/irc/news_bot/ && python3 ./main.py >>/var/log/newsbot-info.log 2>>/var/log/newsbot-error.log`