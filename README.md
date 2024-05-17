# MRVN_Bot
### 已停機，直到尋找到新的雲託管平台
### 經過Discord驗證才能加入超過100個伺服器，但考量到replit免費版本的性能資源有限，最終暫時決定延用此限制


一台使用Discord.py製作的服務馬文(Discord bot)

![1](https://github.com/DMCDN/MRVN_Bot/assets/128150279/cacc2c46-a632-40ca-90f0-acb6db047fad)

# 功能

## Discord
### 動態語音頻道管理

使用/setdynvoice 設置設置語音頻道

![voice](https://github.com/DMCDN/MRVN_Bot/assets/128150279/a6764831-fb18-4cb5-b525-5b7b2fed65b4)

接著進入該頻道 即可創建自己的語音頻道

當該語音頻道無人時會自動移除

https://github.com/DMCDN/MRVN_Bot/assets/128150279/f2bbd76e-59fe-41f8-8eab-b07894e9a8a4


### 自訂義歡迎頻道
使用/set_welcome 設置設置歡迎頻道

![xi](https://github.com/DMCDN/MRVN_Bot/assets/128150279/ef15d560-e5ac-4cde-af62-2c95dd66783e)

  * 一個可選參數：
  
    - WelcomeImageUrl：歡迎圖片連結 
      
  * 一個必選參數
     用於設計自訂義歡迎詞，可使用以下參數自行設計：
  
    - UserTag：用戶TAG
      
    - GroupNum：當前群組人數
      
  如： /set_welcometext Text：歡迎{UserTag}，您是本群組第{GroupNum}位用戶 WelcomeImageUrl：https：...
  
  新成員加入後即會在指定的頻道發送歡迎訊息，並根據設置的參數發送自訂義歡迎詞()

![XI2](https://github.com/DMCDN/MRVN_Bot/assets/128150279/5057448b-50fd-4860-b03a-98dbbcc602d6)

### 用戶頭像獲取
用於獲取指定用戶最高畫質頭貼

有兩個參數：
* usertag(必填):欲提取的用戶
* displayselfonly(選填,預設False):該指令結果只對自己顯示

![ICON](https://github.com/DMCDN/MRVN_Bot/assets/128150279/fd27f9c5-728a-4646-9b23-8f1562fb3397)
![ICON2](https://github.com/DMCDN/MRVN_Bot/assets/128150279/cbe948b5-674f-46d5-a139-878c61899e5c)

### 互動彩蛋

目前有7種互動彩蛋，可使用指令將其關閉

![image](https://github.com/DMCDN/MRVN_Bot/assets/128150279/2fbc3d1d-1115-4a3a-b9a9-596ab377765a)

# 其他遊戲類功能

透過串接遊戲API，提取遊戲玩家資料後製作的功能

## Apex Legends：
### 帳號綁定

將一個EA遊戲帳號與Discord帳號綁定
  
    
### 玩家資料查詢

查詢玩家資料

![apex-bind](https://github.com/DMCDN/MRVN_Bot/assets/128150279/c3ea8155-a2b7-448a-b046-8cd741182a44)

### Rank動態追蹤

追蹤指定玩家的Rank走向，每2分鐘更新一次(可透過點擊更新圖示手動更新)，玩家離線則會自動停止追蹤。

![apex-1](https://github.com/DMCDN/MRVN_Bot/assets/128150279/db97b699-209b-4b0d-8a59-2b8943ee2c36)

## Valorant
 ### 帳號綁定

將一個Riot遊戲帳號與Discord帳號綁定

### 玩家每日商成查詢

查詢玩家當日的個人商城物品，並顯示價格、最高等級、展示影片，限已綁定用戶使用
  
![val-shop](https://github.com/DMCDN/MRVN_Bot/assets/128150279/e4c0e70d-7d61-4c4a-9876-70ba2ee514a5)


### 對局資料查詢


查詢玩家當前對局中所有人的資訊，在進入載入畫面後即可隨時使用，限已綁定用戶使用
      
![val-2](https://github.com/DMCDN/MRVN_Bot/assets/128150279/e17e9986-304f-4fcc-8e0a-e1665f9eeb3a)


