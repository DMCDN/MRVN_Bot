import discord

from discord import app_commands
from discord.ext import commands, tasks

import os 
import datetime
import requests
import json
import traceback
import time
import asyncio
from StringProgressBar import progressBar
from typing import Optional

DataPath = 'data/r5apex/'
allUserUIDInfo=f"{DataPath}/apex_UIDList.json"
apex_ServerLanguage=f"{DataPath}/apex_ServerLanguage.json"
apex_trackingUserInfo=f"{DataPath}/apex_trackingUserInfo.json"


class ApexCog(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot
        self.APEX_API_KEY=''
        self.APEX_Headers='Respawn HTTPS/1.0'
        self.APEX_Endpoint='https://r5-crossplay.r5prod.stryder.respawn.com/user.php?qt=user-getinfo&getinfo=0'
        
       # self.loopEvent.start()


    def getUrlText(self,url):
        r5 = requests.get(url)
        return r5.text

    def getStatusIcon(self,num):
        num=int(num) 
        iconDict={
            "0": "https://cdn.discordapp.com/attachments/976434681669091358/976442674917834782/off.png",
            "1": "https://cdn.discordapp.com/attachments/976434681669091358/976442674527739924/on.png",
            "2": "https://cdn.discordapp.com/attachments/976434681669091358/976442674234142770/ingame.png",
            "3": "https://cdn.discordapp.com/attachments/976434681669091358/976434801093525524/disconnect.png",
            "9": "⚫"
        }
        return iconDict[str(num)]
    def getRankChinese(self,name): 
        iconDict={
            "Unranked": "未定級", #Apex Predato
            "Rookie": "鐵牌",
            "Bronze": "銅牌",
            "Silver": "銀牌",
            "Gold": "金牌",
            "Platinum": "白金",
            "Diamond": "鑽石",
            "Master": "大師",
            "Apex Predator": "頂尖獵殺者",}
        return iconDict[name]


    def getUidByName(self,playerName):
        player = playerName #一定要Origin
        PLATFORM='PC' 
        URL = "https://api.mozambiquehe.re/origin?auth=" + self.APEX_API_KEY +"&player=" + player + "&platform=" + PLATFORM
        dictUID = json.loads(self.getUrlText(URL))
        return dictUID["uid"]
        
    def get_PlayerData(self,UID):

        PLATFORM='PC' 
        URL = "https://api.mozambiquehe.re/bridge?auth=" + self.APEX_API_KEY +"&uid=" + UID + "&platform=" + PLATFORM
        dictPlayerInfo = json.loads(self.getUrlText(URL))
        self.headicon='https://cdn.discordapp.com/avatars/974520472135946284/1e52028b8609e64c48004a2d49d47f6c.webp?size=80'
    
        self.apexName=dictPlayerInfo['global']['name'] #中文會抓不到
        self.level=str(dictPlayerInfo['global']['level']) #int
        self.battlePassLevel=dictPlayerInfo['global']['battlepass']['level']  #string

        #banDict
        self.bBanActive=dictPlayerInfo['global']['bans']['isActive'] #bool
        self.iBanRemainingSecond=dictPlayerInfo['global']['bans']['remainingSeconds'] #int
        #rankDict
        self.rankScore=dictPlayerInfo['global']['rank']['rankScore'] #int
        self.rankName=dictPlayerInfo['global']['rank']['rankName']
        self.rankDiv=str(dictPlayerInfo['global']['rank']['rankDiv']) #int
        self.rankImgUrl=dictPlayerInfo['global']['rank']['rankImg']
        if self.rankName in 'Apex Predator' or self.rankName in 'Master' or self.rankName in 'Unranked':
            self.rankDiv='' 
        #arenaDict
        self.arenaScore=dictPlayerInfo['global']['arena']['rankScore'] #int
        self.arenaName=dictPlayerInfo['global']['arena']['rankName']
        self.arenaDiv=str(dictPlayerInfo['global']['arena']['rankDiv']) #int
        self.arenaImgUrl=dictPlayerInfo['global']['arena']['rankImg']
        self.rankImgUrl=dictPlayerInfo['global']['rank']['rankImg']
        if self.arenaName in 'Apex Predator' or self.arenaName in 'Master' or self.arenaName in 'Unranked':
            self.arenaDiv=''
        #playerStatus

        self.playerStatus_NowStatus=dictPlayerInfo['realtime']['currentState'] #offline , In lobby , In match
        self.playerStatus_NowStatusAndTime=dictPlayerInfo['realtime']['currentStateAsText'] #In lobby (00:10)
        #playerStatus_iCurrentStateSecAgo=statusDict['currentStateSecsAgo'] #int 這個要上線才會出現
        self.playerStatus_SelectedHero=dictPlayerInfo['realtime']['selectedLegend'] #LOBA
        #playerStatus_PartyFull
        if dictPlayerInfo['realtime']['partyFull'] == 0:
            self.playerStatus_iPartyFull='false'
        elif dictPlayerInfo['realtime']['partyFull'] == 1:
            self.playerStatus_iPartyFull='true'
        else:
            self.playerStatus_iPartyFull='unknow' 
        #playerStatus_iCanJoin
        if dictPlayerInfo['realtime']['canJoin'] == 1:
            self.playerStatus_iCanJoin='false'
        elif dictPlayerInfo['realtime']['canJoin'] == 0:
            self.playerStatus_iCanJoin='true'
        else:
            self.playerStatus_iCanJoin='unknow' 
        self.playerStatus_StatusIcon=self.getStatusIcon(dictPlayerInfo['realtime']['isOnline']+dictPlayerInfo['realtime']['isInGame'])

        if dictPlayerInfo['realtime']['isOnline'] == 0: #檢測isOnline 避免強制關閉遊戲isInGame仍然為1
            self.headicon=self.getStatusIcon(0)
            self.headicon='https://cdn.discordapp.com/attachments/976434681669091358/976442674917834782/off.png'
            if dictPlayerInfo['realtime']['isInGame'] == 1:
                self.headicon='https://cdn.discordapp.com/attachments/976434681669091358/976434801093525524/disconnect.png'
                self.playerStatus_NowStatusAndTime='disconnect'
        elif dictPlayerInfo['realtime']['isOnline'] == 1:        
            self.headicon='https://cdn.discordapp.com/attachments/976434681669091358/976442674527739924/on.png'
            if dictPlayerInfo['realtime']['isInGame'] == 1:
                self.headicon='https://cdn.discordapp.com/attachments/976434681669091358/976442674234142770/ingame.png'



    # --------------------------APEX BIND--------------------------#
    @app_commands.command(name="apex_bind",description="綁定遊戲帳號")
    @app_commands.describe(playername = "限EA帳號名稱")
    async def apex_bind(self, interaction: discord.Interaction, playername : str):
        try :
            apexUID = self.getUidByName(playername)

            embed = discord.Embed(color=0x6400ff, timestamp=datetime.datetime.utcnow())
            embed.set_author(name='設置完成！')
            embed.add_field(name="玩家名稱", value=playername, inline=False)
            embed.add_field(name="綁定的帳號uid", value=apexUID, inline=False)

            # UIDInfo寫入 待優化
            with open(allUserUIDInfo, "r") as f:
                dictUIDInfo = json.load(f)
                dictUIDInfo.update({str(interaction.user.id):apexUID})
            with open(allUserUIDInfo, "w") as f:
                json.dump(dictUIDInfo, f)

        except KeyError:
            await interaction.response.send_message(f'[Error]找不到該玩家的uid(請確保輸入的是EA帳號名稱,不是steam平台的名稱)')
        await interaction.response.send_message(embed=embed)

    # --------------------------APEX PlayerInfo--------------------------#
    @app_commands.command(name="apex_playerinfo",description="查詢該玩家資訊")
    @app_commands.describe(playername = "玩家EA帳號名稱(若已綁定帳號免輸入)")
    async def apex_playerinfo(self, interaction: discord.Interaction, playername : Optional[str] = None):
            uid=''
            #errorMsg=''
            # 沒輸入playername 從綁定列表提UID
            if not playername:
                with open(allUserUIDInfo, "r") as f:
                    dictUIDInfo = json.load(f)
                try:
                    uid= dictUIDInfo[str(interaction.user.id)]
                except Exception:
                    await interaction.response.send_message(f"您尚未綁定EA帳號，請輸入玩家名稱查詢，或使用/Apex_Bind 綁定")
                    return
            # 反之 提getUIDByName
            else:
                uid = self.getUidByName(playername)

            
            embed = discord.Embed(color=0x6400ff)
            if uid:
                self.get_PlayerData(uid)
                embed.set_author(name=self.apexName, icon_url=self.headicon)
                embed.add_field(name="等級", value=self.level, inline=True)
                # [220305]根據回報 BP等級m3 api給的資料不太準確
                #if self.battlePassLevel in '-1':
                #    embed.add_field(name=languageDict["BattlePass Lavel"],value=languageDict["unbuy"], inline=True) #value=self.battlePassLevel
                #elif self.battlePassLevel in '111':
                #    embed.add_field(name=languageDict["BattlePass Lavel"],value=languageDict["Full-level"], inline=True) #value=self.battlePassLevel
                #else:
                #    embed.add_field(name=languageDict["BattlePass Lavel"],value=self.battlePassLevel, inline=True) #value=self.battlePassLevel
                embed.add_field(name="中離懲罰/懲罰剩餘時間(s)", value=str(self.bBanActive)+'/'+str(self.iBanRemainingSecond), inline=True) 
                embed.add_field(name="大逃殺排位", value='`'+self.getRankChinese(self.rankName)+self.rankDiv+'  '+str(self.rankScore)+'分`', inline=False)  
                #embed.add_field(name=languageDict["Arena Rank"], value='`'+languageDict[self.arenaName]+self.arenaDiv+'  '+str(self.arenaScore)+'分`', inline=True)
                embed.add_field(name="玩家狀態", value=self.playerStatus_NowStatusAndTime, inline=False)  
                embed.add_field(name="選擇的英雄", value=self.playerStatus_SelectedHero, inline=True)  
                #if self.playerStatus_NowStatusAndTime in 'Offline':
                #  pass
                #else: 
                embed.add_field(name="是否滿房", value=self.playerStatus_iPartyFull, inline=True)  
                embed.add_field(name="是否鎖房", value=self.playerStatus_iCanJoin, inline=True) 
                embed.set_thumbnail(url=self.rankImgUrl)
                await interaction.response.send_message(embed=embed)

            else:
                await interaction.response.send_message(f"[Error]找不到該玩家的uid(請確保輸入的是EA帳號名稱,不是steam平台的名稱)")
            

    # --------------------------APEX RankTrack--------------------------#
    @app_commands.command(name="apex_ranktrack",description="Rank動態追蹤")
    @app_commands.describe(playername = "玩家EA帳號名稱(若已綁定帳號免輸入)")
    async def apex_RankTrack(self, interaction: discord.Interaction, playername : Optional[str] = None):
        uid=''
        # 沒輸入playername 從綁定列表提UID
        if not playername:
            with open(allUserUIDInfo, "r") as f:
                dictUIDInfo = json.load(f)
            try:
                uid= dictUIDInfo[str(interaction.user.id)]
            except Exception:
                await interaction.response.send_message(f"您尚未綁定EA帳號，請輸入玩家名稱查詢，或使用/Apex_Bind 綁定")
                return
        # 反之 根據Name查詢UID
        else:
            uid = self.getUidByName(playername)

        embed = discord.Embed(color=0x6400ff)

        if uid:
           tmp=self.getR5rpAndDataByUID(uid)
           r5RP=tmp[0]
           r5Name=tmp[1]
           r5Online=tmp[2]
           embed=discord.Embed(
               title=r5Name,
               description='`'+self.getR5rpToName(r5RP)[0]+str(r5RP)+'` → `'+self.getR5rpToName(r5RP)[0]+str(r5RP)+'`',
               color=0x6400ff)

           embed.add_field(name=self.getR5rpToName(r5RP)[2], value=self.getR5rpToName(r5RP)[3],inline=False)
           #embed.set_footer(text=self.getR5rpToName(r5RP)[2][0]+str(round(self.getR5rpToName(r5RP)[2][1],2))+'%')
           embed.set_thumbnail(url=self.getR5rpToName(r5RP)[1])
           #embed.set_author(name="已開始追蹤,約每一分半更新內容")

           # 修復 當使用者無頭像
           if interaction.user.avatar == None:
               embed.set_author(name=interaction.user.name)
           else:
               embed.set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url)
            
           await interaction.response.send_message("成功", delete_after=1)
           tip = interaction.user.mention+" 已開始追蹤,約每一分半更新內容\n(因DC限制一次僅可顯示25筆對局，25之後不會顯示加扣分細節，但會在最終結算時顯示加總)"
           msg = await interaction.channel.send(tip,embed=embed)
        
            

        else:
            await interaction.response.send_message(f"[Error]找不到該玩家的uid(請確保輸入的是EA帳號名稱,不是steam平台的名稱)")

        print(msg)
        # dc.py 2.0後已經不支援
        #await msg.add_reaction(emoji='⏹️')
        #await msg.add_reaction(emoji='🔄')
#
        with open(apex_trackingUserInfo, "r") as f:
            dictTrackingUserInfo = json.load(f)
            dictTrackingUserInfo.update({str(interaction.user.id):{
                'UID':uid,
                'playerName':r5Name,
                'OldRP':r5RP,
                'History':[],
                'isOnline':r5Online,
                'embedID':msg.id,
                'channelID':msg.channel.id,
                }
            })
        with open(apex_trackingUserInfo, "w") as f:
            json.dump(dictTrackingUserInfo, f)


    def getR5rpAndDataByUID(self,uid):
        headers = {"User-Agent": self.APEX_Headers,}
       
        url = f'{self.APEX_Endpoint}&hardware=PC&uid={uid}&language=tchinese'
        r5 = requests.get(url, headers=headers)
        r5data=json.loads(r5.text[11::])
        r5RP=r5data["rankScore"]
        r5Name=r5data["name"]
        r5Online=r5data["online"]
        return (r5RP,r5Name,r5Online)
    
    # 待優化
    def getR5rpToName(self,r5RP):
        diamond_div=1000
        diamond_min=20000
        diamond_max=24000

        platinum_div=1000
        platinum_min=16000
        platinum_max=20000

        gold_div=1000
        gold_min=12000
        gold_max=16000

        silver_div=1000
        silver_min=8000
        silver_max=12000

        bronze_div=1000
        bronze_min=4000
        bronze_max=8000

        rookie_div=1000
        rookie_min=0
        rookie_max=4000
        if r5RP >= 24000:
            r5RP2NaneAndDiv="大師"
            #rankImgUrl="https://api.mozambiquehe.re/assets/ranks/apexpredator1.png"
            rankImgUrl="https://api.mozambiquehe.re/assets/ranks/master.png"
            bardata = progressBar.filledBar(100, 100, size=20)
            Tips_1=f':radioactive:距離下個段位還需要:0' #900
            Tips_2=f'24000/24000' #900
        elif r5RP >= diamond_min: #"鑽石"#3600 900
            for i in range(1,5):
                if r5RP + diamond_div*i >=diamond_max:
                    r5RP2NaneAndDiv="鑽石"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/diamond{i}.png'
                    bardata = progressBar.filledBar(diamond_div, r5RP-diamond_min-diamond_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{diamond_div-(r5RP-diamond_min-diamond_div*(4-i))}'
                    Tips_2=f'{diamond_min+diamond_div*(4-i)}{bardata[0]}{diamond_min+diamond_div*(5-i)}({round(bardata[1],2)})'

                    break
        #"白金"#3200 800
        elif r5RP >= platinum_min: 
            for i in range(1,5):
                if r5RP + platinum_div*i >=platinum_max:
                    r5RP2NaneAndDiv="白金"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/platinum{i}.png'
                    bardata = progressBar.filledBar(platinum_div, r5RP-platinum_min-platinum_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{platinum_div-(r5RP-platinum_min-platinum_div*(4-i))}'
                    Tips_2=f'{platinum_min+platinum_div*(4-i)}{bardata[0]}{platinum_min+platinum_div*(5-i)}({round(bardata[1],2)}%)'
                    break
        #"金牌"#2800 700
        elif r5RP >= gold_min: 
            for i in range(1,5):
                if r5RP + gold_div*i >=gold_max:
                    r5RP2NaneAndDiv="黃金"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/gold{i}.png'
                    bardata = progressBar.filledBar(gold_div, r5RP-gold_min-gold_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{gold_div-(r5RP-gold_min-gold_div*(4-i))}'
                    Tips_2=f'{gold_min+gold_div*(4-i)}{bardata[0]}{gold_min+gold_div*(5-i)}({round(bardata[1],2)})'
                    break
        elif r5RP >= silver_min: 
            for i in range(1,5):
                if r5RP + silver_div*i >=silver_max:
                    r5RP2NaneAndDiv="白銀"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/silver{i}.png'
                    bardata = progressBar.filledBar(silver_div, r5RP-silver_min-silver_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{silver_div-(r5RP-silver_min-silver_div*(4-i))}'
                    Tips_2=f'{silver_min+silver_div*(4-i)}{bardata[0]}{silver_min+silver_div*(5-i)}({round(bardata[1],2)})'
                    break
        elif r5RP >= bronze_min: 
            for i in range(1,5):
                if r5RP + bronze_div*i >=bronze_max:
                    r5RP2NaneAndDiv="青銅"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/bronze{i}.png'
                    bardata = progressBar.filledBar(bronze_div, r5RP-bronze_min-bronze_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{bronze_div-(r5RP-bronze_min-bronze_div*(4-i))}'
                    Tips_2=f'{bronze_min+bronze_div*(4-i)}{bardata[0]}{bronze_min+bronze_div*(5-i)}({round(bardata[1],2)})'
                    break
        elif r5RP >= rookie_min: 
            for i in range(1,5):
                if r5RP + rookie_div*i >=rookie_max:
                    r5RP2NaneAndDiv="新手"+str(i)
                    rankImgUrl=f'https://api.mozambiquehe.re/assets/ranks/rookie{i}.png'
                    bardata = progressBar.filledBar(rookie_div, r5RP-rookie_min-rookie_div*(4-i), size=20)
                    Tips_1=f':radioactive:距離下個段位還需要:{rookie_div-(r5RP-rookie_min-rookie_div*(4-i))}'
                    Tips_2=f'{rookie_min+rookie_div*(4-i)}{bardata[0]}{rookie_min+rookie_div**(5-i)}({round(bardata[1],2)})'
                    break
        return (r5RP2NaneAndDiv+' ',rankImgUrl,Tips_1,'`'+Tips_2+'`')

    @commands.Cog.listener()
    async def on_ready(self):
        self.Task_RankTrack.start()


    @tasks.loop(seconds=30)
    async def Task_RankTrack(self):
        try:
           # print(f'100s ')
            def getR5rpAndDataByUID(uid):
                try:
                    headers = {"User-Agent": self.APEX_Headers}
                    url = f'{ self.APEX_Endpoint}&hardware=PC&uid={uid}&language=tchinese'
                    r5 = requests.get(url, headers=headers)
                    r5data=json.loads(r5.text[11::])
                    r5RP=r5data["rankScore"]
                    r5Name=r5data["name"]
                    r5Online=r5data["online"]
                    return (r5RP,r5Name,r5Online)
                except:
                    print("[error][getR5rpAndDataByUID]:",r5.text)


            with open(apex_trackingUserInfo, "r") as f:
                dictTrackingUserInfo = json.load(f)
            userIDs=(*dictTrackingUserInfo.keys(),)
            for userID in userIDs:
            
                uid=dictTrackingUserInfo[userID]['UID']
                oldRP=dictTrackingUserInfo[userID]['OldRP']
                History=dictTrackingUserInfo[userID]['History']
                embedID=dictTrackingUserInfo[userID]['embedID']
                channelID=dictTrackingUserInfo[userID]['channelID']

                tmp=getR5rpAndDataByUID(uid)
                r5RP=tmp[0]
                r5Name=tmp[1]
                r5Online=tmp[2]
                #History=[]
                if r5RP - oldRP == 0:
                        pass
                else:
                    tt=0
                    for i in History:
                        tt+=i
                    if oldRP + tt == r5RP:
                        pass
                    else:
                        History.append(r5RP - oldRP-tt)
                imgUrl=self.getR5rpToName(r5RP)[1]
                if (r5RP - oldRP) >0 :
                    total='+'+str(r5RP - oldRP)
                elif (r5RP - oldRP)==0 :
                    total='±'+str(r5RP - oldRP)
                else:
                    total=str(r5RP - oldRP)+",運氣太差了😥😥"
                    imgUrl="https://media.discordapp.net/attachments/976434681669091358/1011161174223630336/unknown.png"
                embed=discord.Embed(
                    title=r5Name,
                    description='`'+self.getR5rpToName(oldRP)[0]+str(oldRP)+'` → `'+self.getR5rpToName(r5RP)[0]+str(r5RP)+'`',
                    color=0x6400ff)
                game=1
                HistoryTT=0
                for i in History:
                    HistoryTT+=i
                    if i >0 :
                        record='+'+str(i)
                    else:
                        record=str(i)

                    if HistoryTT >0 :
                        sz_HistoryTT='+'+str(HistoryTT)
                    else:
                        sz_HistoryTT=str(HistoryTT) #不用'-',因為負數自帶 
                    embed.add_field(name="紀錄"+str(game), value=f'{record}(加總:{sz_HistoryTT})',inline=True)
                    game+=1
                #embed.add_field(name=f'距離下個段位還需要:{self.getR5rpToName(r5RP)[4]}', value=f'距離下個段位還需要:{self.getR5rpToName(r5RP)[4]}',inline=True)
                embed.add_field(name=self.getR5rpToName(r5RP)[2], value=self.getR5rpToName(r5RP)[3],inline=False)
                nextUpdateTime = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(  time.time()+ 28800 +100))
                embed.set_footer(text=f'下次更新時間:{nextUpdateTime}')
                embed.set_thumbnail(url=imgUrl)

                try:
                    user= await self.bot.fetch_user(userID)
                    if user.avatar is None:
                        embed.set_author(name=user.name)
                    else:
                        embed.set_author(name=user.name, icon_url=user.avatar.url)


                    channel = self.bot.get_channel(channelID) 
                    msg_id = embedID 
                    msg = await channel.fetch_message(msg_id)
                    if r5Online == 0:
                        dictTrackingUserInfo.pop(userID)
                        await msg.edit(content=f'{user.mention} 由於檢測到該遊戲帳號已下線,因此已自動停止追蹤\n[總計:{total}]',embed=embed)
                        await msg.clear_reactions()
                    else:
                        await msg.edit(content=f'{user.mention} 已自動更新\n[目前總計:total]',embed=embed)
                        await msg.edit(embed=embed)
                        dictTrackingUserInfo.update({userID:{
                    'UID':uid,
                    'playerName':r5Name,
                    'OldRP':oldRP,
                    'History':History,
                    'isOnline':r5Online,
                    'embedID':msg.id,
                    'channelID':msg.channel.id,
                        }
                        })
                    with open(apex_trackingUserInfo, "w") as f:
                        json.dump(dictTrackingUserInfo, f)
                    await asyncio.sleep(1)

                except Exception as err:
                    print("FBI WARNING!!!!!")
                    print(err)
                    ErrorEmbed = discord.Embed(color=0xFF0000)
                    ErrorEmbed.set_author(name=f'[loopEvent錯誤]\nFBI WARNING!!!:"{str(traceback.format_exc())}\n{str(err)}')
                    print(traceback.format_exc())

        except Exception as err:
            print(err)
            print(traceback.format_exc())


async def setup(bot):
    await bot.add_cog(ApexCog(bot=bot))

async def cog_load(self):
    print(f"{self.__class__.__name__} loaded!")

async def cog_unload(self):
    print(f"{self.__class__.__name__} unloaded!")
