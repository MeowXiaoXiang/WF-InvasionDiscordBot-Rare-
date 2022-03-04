import json
import discord
import asyncio
import requests
import datetime as dt
from opencc import OpenCC
from loguru import logger
from discord.ext import commands
from tinydb import TinyDB, where #tinydb請安裝3.15.2版本 pip install tinydb==3.15.2
#----------給使用者改變設定的區域---------------------
detection_time = 60 #偵測時間 目前每60秒一次
edit_cycle = 20 #編輯週期 依照上面時間 如果60秒那麼這數值設定20等於20分鐘
#---------------------------------------------------
bot = commands.Bot(command_prefix=commands.when_mentioned,intents=discord.Intents.all())
cc = OpenCC('s2t')  #簡體中文 -> 繁體中文
Imp_parm = json.load(open("setting.json", 'r', encoding='utf8')) #讀取你的token那些的在setting.json
Dict = json.load(open("rawDict.json", 'r', encoding='utf8')) #讀取字典 中英翻譯那些
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
    while True:
        with TinyDB('db.json') as db:
            if not db.table('_default').contains(where('timer')):
                db.table('_default').insert({'timer': 0})
                print("已新增timer變數至db")
            inv_table = db.table('invasions')
            print(bot.description)
            target = [
                'Orokin 反應爐藍圖', 'Orokin 催化劑藍圖', 'Warframe 特殊功能槽連接器 藍圖', 'Forma 藍圖'
            ] #稀有入侵任務的獎勵目標
            alarm_channel = bot.get_channel(int(Imp_parm['ALARM_CHANNEL']))#警報頻道ID
            #---------------------------------------------
            try:
                #-----------------------------------------------------------------------
                invasions = {}
                print("入侵小幫手運作中提示：" + UTC_8_NOW())
                #---------------------inv_data------------------------------------------
                #print('取得入侵資料...')
                inv_raw = requests.get("https://api.warframestat.us/pc/invasions", headers={"Accept-Language": "zh"})
                inv_text = cc.convert(inv_raw.text)
                inv_data = json.loads(inv_text)
                #---------------------------------------------------------------------------
                for fdata in inv_data:
                    #print('\033[1;90m',"invasions detect....",'\033[0m')
                    inv_ID = fdata['id']
                    invasions[inv_ID] = fdata
                    node = invasions[inv_ID]['node']
                    if invasions[inv_ID]['vsInfestation']:
                        attacker = invasions[inv_ID]['attackingFaction']
                        attackerRewardCount = ""
                        attackerReward = "無獎勵"
                    else:
                        attacker = invasions[inv_ID]['attackingFaction']
                        attackerRewardCount = "x" + str(invasions[inv_ID]['attackerReward']['countedItems'][0]['count'])
                        attackerReward = invasions[inv_ID]['attackerReward']['countedItems'][0]['type']
                    defender = invasions[inv_ID]['defendingFaction']
                    defenderRewardCount = "x" + str(invasions[inv_ID]['defenderReward']['countedItems'][0]['count'])
                    defenderReward = invasions[inv_ID]['defenderReward']['countedItems'][0]['type']
                    #------------dbkeyslist------------------------------
                    inv_dbkeys=[]
                    for dbi in db.table('invasions').all():
                        inv_dbkeys.append("".join(dbi.keys())) 
                    if inv_ID not in inv_dbkeys and not invasions[inv_ID]['completed'] and invasions[inv_ID]['eta'] != "Infinityd" and invasions[inv_ID]['eta'] != "-Infinityd" and (attackerReward in target or defenderReward in target):
                        #-------------進攻方表情符號-----------------------
                        attackerReward = Dict['Reward'].get(attackerReward, attackerReward)
                        #-------------防守方表情符號-----------------------
                        defenderReward = Dict['Reward'].get(defenderReward, defenderReward)
                        #-------------------------------------------------
                        if invasions[inv_ID]['eta'] == "Infinityd" or invasions[inv_ID]['eta'] == "-Infinityd":
                            embed = discord.Embed(title=node, color=0xffff00)
                        else:
                            embed = discord.Embed(title=node, color=0x00ff00)
                        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/708960426758635591/853580054755541012/InvasionIcon_b.png")
                        embed.add_field(
                            name=attacker,
                            value=f"{attackerReward}{attackerRewardCount}",
                            inline=True)
                        embed.add_field(
                            name=defender,
                            value=f"{defenderReward}{defenderRewardCount}",
                            inline=True)
                        completion = invasions[inv_ID]['completion']
                        embed.add_field(
                                name=f"進度",
                                value=
                                f"{'%.1f' % completion}%  |  {'%.1f' % (100 - completion)}%",
                                inline=False)
                        embed.set_footer(text=f"資料更新時間：{UTC_8_NOW()}\n附註：每20分鐘更新一次資料")
                        embedmsg = await alarm_channel.send("<@&" + str(Imp_parm['ALARM_ROLE_ID']) + ">",embed=embed)
                        logger.info("入侵任務\n" + str(inv_ID) + ' | ' + str(embedmsg.id) + ' | ' + node)
                        inv_table.insert({inv_ID: embedmsg.id})
                        print(UTC_8_NOW(), embedmsg.id,"稀有入侵訊息發送")
                        continue
                if db.table('_default').get(where('timer'))['timer'] >= edit_cycle:  #設定每多久做訊息編輯 多久的長度取決於設定秒數 目前60s, 設定>=20 就等於20分
                    #----------------------------------------------------------------
                    inv_dbkeys=[]
                    for dbi in db.table('invasions').all():
                        inv_dbkeys.append("".join(dbi.keys())) 
                    #----------------------------------------------------------------
                    for ID in inv_dbkeys:
                        if ID not in invasions.keys() or invasions[ID]['completed']:
                            message = await alarm_channel.fetch_message(inv_table.get(where(ID))[ID])
                            print(UTC_8_NOW(), message.id,"入侵任務結束")
                            for embed in message.embeds:
                                raw = embed
                                raw.remove_field(2)
                                raw.add_field(name="進度",
                                            value="已結束",
                                            inline=False)
                                raw.color = 0xff0000
                                raw.set_footer(
                                    text=f"資料更新時間：{UTC_8_NOW()} [每20分刷新一次資料]")
                                await message.edit(embed=raw)
                            inv_table.remove(where(ID))
                        else:
                            try:
                                message = await alarm_channel.fetch_message(inv_table.get(where(ID))[ID])
                                print(UTC_8_NOW(), message.id, invasions[ID]['node'])
                                for embed in message.embeds:
                                    raw = embed
                                    raw.remove_field(2)
                                    raw.add_field(
                                            name=f"進度",
                                            value=f"{'%.1f' % completion}%  |  {'%.1f' % (100 - completion)}%",
                                            inline=False)
                                    raw.set_footer(text=f"資料更新時間：{UTC_8_NOW()} [每20分刷新一次資料]")
                                    raw.color = 0x00ff00
                                await message.edit(embed=raw)
                            except Exception as e:
                                print(UTC_8_NOW(), e, inv_table.get(where(ID))[ID])
                    db.table('_default').update({'timer':0},where('timer'))
                await asyncio.sleep(detection_time) #每60秒偵測一次
                db.table('_default').update({'timer':db.table('_default').get(where('timer'))['timer'] + 1},where('timer'))
                print("Timer記數次數：", db.table('_default').get(where('timer'))['timer'],"次")
                #設定為60秒更新一次,一次等於60秒 這條訊息提示目前的次數
            except Exception as e:
                logger.error(str(e))

@bot.command(name="cleandb", aliases=['cleardb', '清除資料庫'])
async def cleandb(ctx):
    with TinyDB('db.json') as db:
        print("開始清除db")
        try:
            db.purge_table('invasions')
        except Exception as e:
            logger.error(str(e))

@bot.command(name="update", aliases=['resettimer', '重設timer'])
async def update(ctx):
    with TinyDB('db.json') as db:
        print("重設timer為",edit_cycle)
        try:
            db.table('_default').update({'timer':edit_cycle},where('timer'))
            print("timer目前為:", db.table('_default').get(where('timer'))['timer'])
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
    #keep_alive.awake(f'{keep_alive_url}', True)
    bot.loop.create_task(Preset_task())
    bot.run(Imp_parm['TOKEN'])
    bot.loop.run_forever()