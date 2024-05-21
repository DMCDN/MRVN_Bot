
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional


import json 
from datetime import datetime
import psutil
import time
import re
class ExampleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bootTime = datetime.utcnow()
        self.DEVlist = [429640904463351818,525665069128744962] #DEV ID's
        self.WelcomeChannel_Path='data/Welcome.json'
        self.VoiceChannel_Path='data/Voice.json'
        with open(self.VoiceChannel_Path, "r") as f:
            self.dictVoiceInfo = json.load(f)

    #await asyncio.sleep(5)
    #@commands.command(name="ping")
    #async def pingcmd(self, ctx):
    #    """the best command in existence"""
    #    await ctx.send(ctx.author.mention)
    @app_commands.command(name="ping",description="查看機器人Ping")
    async def slash_ping(self, interaction):

        now = datetime.utcnow()
        elapsed = now - self.bootTime
        seconds = elapsed.seconds
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)

        embed = discord.Embed(title="MRVN狀態欄", color=discord.Color.orange())
        embed.add_field(name="Ping", value=str(round(self.bot.latency * 1000)) + "ms")
        embed.add_field(name="CPU", value=str(psutil.cpu_percent()) + "%")
        embed.add_field(name="RAM", value=str(round(psutil.virtual_memory().used * 10 ** -9, 2)) + "GB/" + str(round(psutil.virtual_memory().total * 10 ** -9, 2)) + "GB")
        embed.add_field(name="伺服器總數", value=str(len(self.bot.guilds)))
        
        amount_users = 0
        for guild in self.bot.guilds:
            for _ in guild.members:
                amount_users += 1
        embed.add_field(name="使用者總數", value=str(amount_users))

        await self.bot.wait_until_ready()
        pusheen = await self.bot.fetch_user(429640904463351818)
        embed.add_field(name="託管運行時間", value="{}天|{}時:{}分:{}秒".format(elapsed.days, hours, minutes, seconds))
        embed.set_footer(text=" bug/問題反饋:ipsips65@gmail.com", icon_url=pusheen.avatar.url) #dc.py 2.0以前為avatar_url

        await interaction.response.send_message(embed=embed, ephemeral=False)


    @app_commands.command(name="icon",description="顯示使用者頭貼")
    @app_commands.describe(usertag = "輸入數字", displayselfonly = "只對自己顯示")
    async def slash_icon(self, interaction: discord.Interaction , usertag:discord.Member , displayselfonly : Optional[bool] = False):
        await interaction.response.send_message(usertag.avatar.url, ephemeral = displayselfonly)



    @app_commands.command(description="設置新成員提示頻道")
    @app_commands.describe(channel = "文字頻道")
    async def set_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if interaction.user.guild_permissions.administrator or interaction.user.id in self.DEVlist:
            dictWelcomeInfo = {}
            guildID = interaction.guild.id
            channelID = channel.id
            with open(self.WelcomeChannel_Path, "r") as f:
                dictWelcomeInfo = json.load(f)
                dictWelcomeInfo.update({str(guildID): str(channelID)})
            with open(self.WelcomeChannel_Path, "w") as f:
                json.dump(dictWelcomeInfo, f)
            await interaction.response.send_message(f'頻道設置完成[伺服器ID:{str(guildID)},頻道ID:{str(channelID)}]')


    ###clear SLASH###
    @app_commands.command(name="clear",description="清除訊息")
    @app_commands.describe(deletenum = "訊息數量")
    async def slash_clear(self, interaction: discord.Interaction, deletenum: int):
        if interaction.user.guild_permissions.administrator or interaction.user.id in self.DEVlist:
        # await ctx.send(f'馬文打掃中...') #+1
            await interaction.channel.purge(limit=deletenum) 
            #await ctx.message.delete() #包刮刪除指令 -1
            await interaction.response.send_message(f'已清除{deletenum}則訊息')
        else:
            await interaction.response.send_message(interaction.user.mention + "您沒有權限執行這項指令")
    #clear SLASH END#


    @app_commands.command(name="starburst",description="星爆一名玩家1次 輸入：Tag / 使用者ID (擇一)")
    @app_commands.describe(burstplayer = "要星爆的玩家")
    @app_commands.describe(burstplayerid = "要星爆的玩家id")
    async def slash_burst(self, interaction: discord.Interaction, burstplayer: Optional[discord.Member] = None , burstplayerid: Optional[str] = None):
        if burstplayerid:
            burstplayer = await self.bot.fetch_user(int(burstplayerid))
        try:
            num=1
            whitelist=[464313514605936650]+self.DEVlist
            if interaction.user.id in whitelist or interaction.message.author.guild_permissions.administrator:
                message="https://cdn.discordapp.com/emojis/936674486319726622.webp?size=1024"
                await interaction.response.send_message(f"正在星爆 {burstplayer} ...")
                original_response = await interaction.original_response()

                for i in range(num):
                    await burstplayer.send(message)
                    time.sleep(1.25)

                await burstplayer.send('您被 {0} 星爆了{1}次'.format(interaction.user.name,str(num)))
                await original_response.edit(content=f'已成功星爆: {burstplayer} {num}次')
                await interaction.channel.send(message)
                
                #await msgWaiting.delete()
                #interaction.delete_original_response()
        except Exception as error:
            if '403 Forbidden' in str(error):
                await interaction.response.send_message('錯誤: 此用戶或該伺服器不允許私人訊息 [{}]'.format(str(error)))
            else:
                await interaction.response.send_message('錯誤: {}'.format(str(error)))

    @commands.Cog.listener()
    async def on_message(self, message):
        hit=['打','扁','揍','破','垃圾','拉基','爛','臭','笨']
        for keyW in hit:
         if  keyW in message.content and '馬文' in message.content : 
          #await message.delete()
          await message.channel.send('りしれ供さ小?')

        hit=['讚','好','棒','水']
        for keyW in hit:
         if  keyW in message.content and '馬文' in message.content : 
          #await message.delete()
          await message.channel.send('免っがわ来じっ套')

        starburst=['十秒','10秒','刀劍','sao','SAO','星爆','48763','burst','Burst','switch','Switch']
        for keyW in starburst:
         if  keyW in message.content : 
          await message.channel.send('https://cdn.discordapp.com/emojis/936674486319726622.webp?size=1024')

        if '不想努力' in message.content  :
            if self.bot.user !=message.author: 
             await message.channel.send('不想努力就去死')
             print("不想努力就去死")

        hansome = re.compile(r'(?=.*我)(?=.*帥)^.*')
        match2 = hansome.search(message.content)
        if match2:
            await message.add_reaction('\U0001F92E')
            print("\U0001F92E")
        #
        await self.bot.process_commands(message)


    @app_commands.command(name="setwelcome",description="設置新成員提示頻道")
    @app_commands.describe(channel = "指定的文字頻道")
    async def slash_setwelcome(self, interaction: discord.Interaction , channel:discord.TextChannel):
        if interaction.user.guild_permissions.administrator or interaction.user.id in self.DEVlist:
            dictWelcomeInfo={}
            guildID = interaction.guild.id
            channelID=channel.id
            with open(self.WelcomeChannel_Path, "r") as f:
                dictWelcomeInfo = json.load(f)
                dictWelcomeInfo.update({str(guildID):str(channelID)})
            with open(self.WelcomeChannel_Path, "w") as f:
                json.dump(dictWelcomeInfo, f)
            await interaction.response.send_message(f'頻道設置完成[伺服器ID:{str(guildID)},頻道ID:{str(channelID)}]')

    @app_commands.command(name="setdynvoice",description="設置動態語音頻道")
    @app_commands.describe(channel = "指定的文字頻道")
    async def slash_dynvoice(self, interaction: discord.Interaction , channel:discord.VoiceChannel):
        if interaction.user.guild_permissions.administrator or interaction.user.id in self.DEVlist:
            guildID = interaction.guild.id
            channelID=channel.id
            with open(self.VoiceChannel_Path, "r") as f:
                self.dictVoiceInfo = json.load(f)
                self.dictVoiceInfo.update({str(guildID):{
                    "channelID":channelID,
                    "channelist":[],
                    }
                })
            with open(self.VoiceChannel_Path, "w") as f:
                json.dump(self.dictVoiceInfo, f)
            await interaction.response.send_message(f'設置完成[{str(guildID)}:{str(channelID)}]')

    @commands.Cog.listener()
    async def on_member_join(self,member):
        with open(self.WelcomeChannel_Path, "r") as f:
            dictWelcomeInfo = json.load(f)
        try:
            dictWelcomeInfo[str(member.guild.id)] #先測試

            channel = discord.utils.get(member.guild.channels, id=int(dictWelcomeInfo[str(member.guild.id)])) #name="歡迎"
            embed = discord.Embed(color=0x6400ff,title=f"{member.guild}", description=f"歡迎 {member.mention} ,跟著{len(list(member.guild.members))}位成員乖乖進來吧!")
            embed.set_thumbnail(url=f"{member.avatar.url}")
            embed.set_image(url=f"https://cdn.discordapp.com/attachments/976434681669091358/988691469370028032/fd9cb24e7d23a0a8.gif")
            await channel.send(embed=embed)
        except:
            pass
    
    @commands.Cog.listener()
    async def on_voice_state_update(self,member, before, after):
        try:
            vcID=self.dictVoiceInfo[str(member.guild.id)]["channelID"]
            vcList=self.dictVoiceInfo[str(member.guild.id)]["channelist"]
            if  before.channel is not None :
                if before.channel.id in vcList: #若再list裡 
                    if len(before.channel.members) == 0:
                        vcList.remove(before.channel.id) 
                        await before.channel.delete()
                        self.dictVoiceInfo.update({str(member.guild.id):{
                            "channelID":vcID,
                            "channelist":vcList,
                            }
                        })
                        with open(self.VoiceChannel_Path, "w") as f:
                            json.dump(self.dictVoiceInfo, f)
                    elif after.channel is not None: #如果是退+進
                        if  after.channel.id in vcList:
                            if after.channel != before.channel:
                                channel = discord.utils.get(member.guild.voice_channels, name = f'└[{member}] 的家')
                                if channel is not None:
                                    await member.edit(voice_channel=channel)
                                    print("1")
        except KeyError:  #沒有匹配項 步處理
            pass     

        try:
            vcID=self.dictVoiceInfo[str(member.guild.id)]["channelID"]
            vcList=self.dictVoiceInfo[str(member.guild.id)]["channelist"]
            if after.channel is not None :
                if after.channel.id == vcID:#若進了test
                    channel = discord.utils.get(member.guild.voice_channels, name = f'└[{member}] 的家')
                    if channel == None : #若不存在ph home
                        await after.channel.clone(name=f'└[{member}] 的家')
                        channel = discord.utils.get(member.guild.voice_channels, name = f'└[{member}] 的家')
                        await member.edit(voice_channel=channel)
                        vcList.append(channel.id) 
                        self.dictVoiceInfo.update({str(member.guild.id):{
                            "channelID":vcID,
                            "channelist":vcList,
                            }
                        })
                        with open(self.VoiceChannel_Path, "w") as f:
                            json.dump(self.dictVoiceInfo, f)



                    else:
                        if after.channel != before.channel: #若非觸發狀態
                            channel = discord.utils.get(member.guild.voice_channels, name = f'└[{member}] 的家')
                            #if channel
                            await member.edit(voice_channel=channel)
                    # else:

                        if after.channel.id in vcList: #0825
                            if len(before.channel.members) == 0:
                                vcList.remove(before.channel.id) 
                                await after.channel.delete()
                                self.dictVoiceInfo.update({str(member.guild.id):{
                                    "channelID":vcID,
                                    "channelist":vcList,
                                    }
                                })
                                with open(self.VoiceChannel_Path, "w") as f:
                                    json.dump(self.dictVoiceInfo, f)
                        
        except KeyError:  #沒有匹配項 步處理
            pass     




async def setup(bot):
    await bot.add_cog(ExampleCog(bot=bot))

async def cog_load(self):
    print(f"{self.__class__.__name__} loaded!")

async def cog_unload(self):
    print(f"{self.__class__.__name__} unloaded!")

