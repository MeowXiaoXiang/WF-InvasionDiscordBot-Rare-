import os
import json
import discord
import asyncio
import requests
import keep_alive 
import datetime as dt
from replit import db
from opencc import OpenCC
from loguru import logger
from discord.ext import commands
#----------給使用者改變設定的區域---------------------
detection_time = 60 #偵測時間 目前每60秒一次
edit_cycle = 20 #編輯週期 依照上面時間 如果60秒那麼這數值設定20等於20分鐘
keep_alive_url = '' #喚醒用網址 這個網址就是打開replit的程式後右上角的網址
#---------------------------------------------------
bot = commands.Bot(command_prefix=commands.when_mentioned,intents=discord.Intents.all())
cc = OpenCC('s2t')  #簡體中文 -> 繁體中文
Dict = json.load(open("rawDict.json", 'r', encoding='utf8')) #讀取字典(表情那些)
#-------------當機器人準備好 會設定自己的狀態和提示已經READY!---------
@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching,
                                name="Warframe 稀有入侵&警報&午夜電波") #更改這邊可以改變機器人的狀態
    await bot.change_presence(activity=activity)
    logger.info(f'{bot.user} | Ready!')
#----------主要重複執行的TASK-----------------
async def Preset_task():
  await bot.wait_until_ready()
  if "timer" not in db.keys():
    db['timer'] = 0
    print("已新增timer變數至db")
  while True:
    print(bot.description)
    target = ['Orokin 反應爐藍圖','Orokin 催化劑藍圖','Warframe 特殊功能槽連接器 藍圖','Forma 藍圖']
    alarm_channel_id = int(os.environ['ALARM_CHANNEL']) #警報頻道ID
    channel = bot.get_channel(alarm_channel_id)
    #---------------------------------------------
    try:
      raw = requests.get("https://api.warframestat.us/pc/invasions",headers={"Accept-Language":"zh"})
      text = cc.convert(raw.text)
      data = json.loads(text)
      invasions = {}
      print("入侵小幫手運作中提示：" + UTC_8_NOW()) 
      for fdata in data:
        ID = fdata['id']
        invasions[ID] = fdata
        node = invasions[ID]['node']
        if invasions[ID]['vsInfestation']:
          attacker = invasions[ID]['attackingFaction']
          attackerRewardCount = ""
          attackerReward = "無獎勵"
        else:
          attacker = invasions[ID]['attackingFaction']
          attackerRewardCount = "x" + str(invasions[ID]['attackerReward']['countedItems'][0]['count'])
          attackerReward = invasions[ID]['attackerReward']['countedItems'][0]['type']
        defender = invasions[ID]['defendingFaction']
        defenderRewardCount = "x" + str(invasions[ID]['defenderReward']['countedItems'][0]['count'])
        defenderReward = invasions[ID]['defenderReward']['countedItems'][0]['type']
        if ID not in db.keys() and not invasions[ID]['completed'] and invasions[ID]['eta'] != "Infinityd" and invasions[ID]['eta'] != "-Infinityd" and (attackerReward in target or defenderReward in target):
          #-------------進攻方表情符號-----------------------
          attackerReward = Dict['Reward'].get(attackerReward,attackerReward)
          #-------------防守方表情符號-----------------------
          defenderReward = Dict['Reward'].get(defenderReward,defenderReward)
          #-------------------------------------------------
          embed=discord.Embed(title=node, color=0x00ff4c)
          embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/708960426758635591/853580054755541012/InvasionIcon_b.png")
          embed.add_field(name=attacker, value=f"{attackerReward}{attackerRewardCount}", inline=True)
          embed.add_field(name=defender, value=f"{defenderReward}{defenderRewardCount}", inline=True)
          completion = invasions[ID]['completion']
          embed.add_field(name=f"進度",value=f"{'%.1f' % completion}%  |  {'%.1f' % (100 - completion)}%",inline=False)
          embed.set_footer(text=f"資料更新時間：{UTC_8_NOW()}")
          embedmsg = await channel.send(embed=embed)
          logger.info(str(ID)+' | '+str(embedmsg.id)+' | '+node)
          db[ID] = embedmsg.id
          print(UTC_8_NOW(),embedmsg.id)
          continue
      if db["timer"] >= edit_cycle:
        for ID in db.keys():
          if ID != "timer":
            if ID not in invasions.keys() or invasions[ID]['completed']:
              message = await channel.fetch_message(db[ID])
              for embed in message.embeds:
                raw = embed
                raw.remove_field(2)
                raw.add_field(name="進度",value="已結束",inline=False)
                raw.color = 0xff0000
                await message.edit(embed=raw)
                del db[ID]
            else:
              try:
                message = await channel.fetch_message(db[ID])
                print(UTC_8_NOW(),message.id,invasions[ID]['node'])
                for embed in message.embeds:
                  raw = embed
                  raw.remove_field(2)
                  completion = invasions[ID]['completion']
                  raw.add_field(name=f"進度",value=f"{'%.1f' % completion}%  |  {'%.1f' % (100 - completion)}%",inline=False)
                  raw.set_footer(text=f"資料更新時間：{UTC_8_NOW()}")
                await message.edit(embed=raw)
              except Exception as e:
                print(UTC_8_NOW,e,db[ID])
        db["timer"] = 0
      await asyncio.sleep(detection_time) #每60秒偵測一次
      db["timer"] = db["timer"] + 1
      print("Timer記數次數：",db['timer'],"次") #設定為60秒更新一次,一次等於60秒 這條訊息提示目前的次數
    except Exception as e:
      logger.error(str(e))

@bot.command(name="cleardb" , aliases=['cleandb' , '清除資料庫'])
async def cleardb(ctx):
  print("開始清除db")
  for data in db.keys():
    try:
      del db[data]
    except Exception as e:
      logger.error(str(e))
  print("清除完成db")

@bot.command(name="reset" , aliases=['resettimer' , '重設timer'])
async def reset(ctx):
  print("重設timer為20")
  for data in db.keys():
    try:
      db["timer"] = 20
      print("timer目前為:",db["timer"])
    except Exception as e:
      logger.error(str(e))
  print("重設timer完成")

@bot.event
async def on_disconnect():
    logger.info('機器人已關閉')


def set_logger():
    log_format = ('{time:YYYY-MM-DD HH:mm:ss!UTC} | '
                  '<lvl>{level: ^9}</lvl>| '
                  '{message}')
    # logger.add(sys.stderr, level='INFO', format=log_format)
    logger.add(f'./logs/bot.log',
               rotation='7 day',
               retention='30 days',
               level='INFO',
               encoding='UTF-8',
               format=log_format)


def UTC_8_NOW():
    f = '%Y-%m-%d %H:%M'
    time_delta = dt.timedelta(hours=+8)
    utc_8_date_str = (dt.datetime.utcnow() + time_delta).strftime(f)  #時間戳記
    return utc_8_date_str


if __name__ == '__main__':
    set_logger()
    keep_alive.awake(f'{keep_alive_url}', True)
    bot.loop.create_task(Preset_task())
    bot.run(os.environ['TOKEN'])
    bot.loop.run_forever()