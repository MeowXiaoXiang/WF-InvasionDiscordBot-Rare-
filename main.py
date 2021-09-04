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

bot = commands.Bot(command_prefix=commands.when_mentioned,intents = discord.Intents.all())
cc = OpenCC('s2twp') #簡體中文 -> 繁體中文 (台灣, 包含慣用詞轉換)

Dict = json.load(open("rawDict.json",'r',encoding='utf8'))

@bot.event
async def on_ready():
    activity = discord.Activity(type=discord.ActivityType.watching,name = "Warframe 稀有入侵任務")
    await bot.change_presence(activity=activity)  
    logger.info(f'{bot.user} | Ready!')

async def invasions():
  await bot.wait_until_ready()
  if "timer" not in db.keys():
    db['timer'] = 0
    print("已新增timer變數至db")
  while True:
    print(bot.description)
    requests.get("http://127.0.0.1:8080/") #防止機器人自行關閉 每拿資料一次會ping自己一次
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
        node = fdata['node']
        if fdata['vsInfestation']:
          attacker = fdata['attackingFaction']
          attackerRewardCount = ""
          attackerReward = "無獎勵"
        else:
          attacker = fdata['attackingFaction']
          attackerRewardCount = "x" + str(fdata['attackerReward']['countedItems'][0]['count'])
          attackerReward = fdata['attackerReward']['countedItems'][0]['type']
        defender = fdata['defendingFaction']
        defenderRewardCount = "x" + str(fdata['defenderReward']['countedItems'][0]['count'])
        defenderReward = fdata['defenderReward']['countedItems'][0]['type']
        if ID not in db.keys() and not fdata['completed'] and fdata['eta'] != "Infinityd" and (attackerReward in target or defenderReward in target):
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
          embed.set_footer(text=f"資料更新時間：{UTC_8_NOW()}\n附註：每15分鐘更新一次資料")
          embedmsg = await channel.send("<@&"+ str(os.environ['ALARM_ROLE_ID']) +">",embed=embed)
          logger.info(str(ID)+' | '+str(embedmsg.id)+' | '+node)
          db[ID] = embedmsg.id
          print(UTC_8_NOW(),embedmsg.id)
          await asyncio.sleep(60)
          continue
      if db["timer"] >= 15: #設定每多久做訊息編輯 多久的長度取決於設定秒數 目前60s, 設定>=15 就等於15分
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
                  raw.set_footer(text=f"資料更新時間：{UTC_8_NOW()} [每15分刷新一次資料]")
                await message.edit(embed=raw)
              except Exception as e:
                print(UTC_8_NOW,e,db[ID])
        db["timer"] = 0
      await asyncio.sleep(60)
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

@bot.event
async def on_disconnect():
    requests.get("http://127.0.0.1:8080/")
    logger.info('機器人已關閉')

def set_logger():
    log_format = (
        '{time:YYYY-MM-DD HH:mm:ss!UTC} | '
        '<lvl>{level: ^9}</lvl> | '
        '{message}'
    )
    # logger.add(sys.stderr, level='INFO', format=log_format)
    logger.add(
        f'./logs/bot.log',
        rotation='7 day',
        retention='30 days',
        level='INFO',
        encoding='UTF-8',
        format=log_format
    )

def UTC_8_NOW():
    f = '%Y-%m-%d %H:%M'
    time_delta = dt.timedelta(hours=+8)
    utc_8_date_str = (dt.datetime.utcnow()+time_delta).strftime(f) #時間戳記
    return utc_8_date_str

if __name__ == '__main__':
    set_logger()
    keep_alive.keep_alive()
    bot.loop.create_task(invasions())
    bot.run(os.environ['TOKEN'])
    bot.loop.run_forever()