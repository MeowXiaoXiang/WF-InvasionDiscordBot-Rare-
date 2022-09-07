# InvasionBot 
#### WARFRAME稀有入侵偵測機器人

## 請安裝Python以及下列的套件 或 直接使用install.cmd直接安裝

+ pip install discord
+ pip install requests
+ pip install opencc
+ pip install flask
+ pip install loguru
+ pip install tinydb==3.15.2

## 安裝完畢之後的設定
* 請輸入三個必要的資訊在setting.json內
* 1.TOKEN 2.機器人要標記的身分組ID(ALARM_ROLE_ID) 3.入侵提示頻道(ALARM_CHANNEL)
* 請至Discord設定➜進階➜打開開發者模式 來對頻道進行滑鼠右鍵來複製ID
* 只有TOKEN為字串會有雙引號為字串 直接填入雙引號 其餘直接放入純數字ID即可
* 若要在品項前面或後面放入表情符號可以去rawDict.json修改
* 範例:"Orokin 反應爐藍圖":""<:Reactor:88888888888888888> Orokin 反應爐藍圖"
