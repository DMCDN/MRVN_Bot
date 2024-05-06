# MRVN_Bot
### 已停機，直到尋找到新的雲託管平台

一台服務馬文 

使用Discord.py製作的Discord bot

![1](https://github.com/DMCDN/MRVN_Bot/assets/128150279/cacc2c46-a632-40ca-90f0-acb6db047fad)

# 功能

## Discord
### 動態語音頻道
### 自訂義歡迎頻道
### 用戶頭像獲取
### 其餘互動

## Apex Legends：
### 帳號綁定
```
/Apex_bind <UserName>
```
說明：

將一個EA遊戲帳號與Discord帳號綁定
  
 參數說明:
  - UserName (必選)：EA帳號名稱
    
### 玩家資料查詢

```
/Apex_UserInfo [UserName]
```
說明：

查詢玩家資料
  
參數說明:
  - UserName (可選): 欲查詢玩家的EA帳號名稱(未填入則查詢自己的)

![apex-bind](https://github.com/DMCDN/MRVN_Bot/assets/128150279/c3ea8155-a2b7-448a-b046-8cd741182a44)

### Rank動態追蹤

```
/Apex_RankTrack [UserName]
```
說明：

追蹤指定玩家的Rank走向，每2分鐘更新一次(可透過點擊更新圖示手動更新)，玩家離線則會自動停止追蹤。

參數說明:
  - UserName (可選): 欲追蹤玩家的EA帳號名稱(未填入則查詢自己的)
    
![apex-1](https://github.com/DMCDN/MRVN_Bot/assets/128150279/db97b699-209b-4b0d-8a59-2b8943ee2c36)

## Valorant
 ### 帳號綁定
```
/Val_bind <UserName> <PassWord>
```
說明：

將一個Riot遊戲帳號與Discord帳號綁定
  
 參數說明:
  - UserName (必選)：Riot帳號名稱
  - PassWord (必選)：Riot密碼


### 玩家每日商成查詢

```
/Val_Shop
```
說明：

查詢玩家個人商城物品，限已綁定用戶使用
  
![val-shop](https://github.com/DMCDN/MRVN_Bot/assets/128150279/e4c0e70d-7d61-4c4a-9876-70ba2ee514a5)


### 對局資料查詢

```
/Val_BattleInfo
```
說明：

查詢玩家當前對局中所有人的資訊，在進入載入畫面後即可隨時使用，限已綁定用戶使用
      
![val-2](https://github.com/DMCDN/MRVN_Bot/assets/128150279/e17e9986-304f-4fcc-8e0a-e1665f9eeb3a)


