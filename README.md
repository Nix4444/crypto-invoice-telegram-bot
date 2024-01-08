# Crypto Invoice Telegram Bot 
<div align="center">
  <img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white"><br>
  <img src="https://img.shields.io/badge/Bitcoin-000000?style=for-the-badge&logo=bitcoin&logoColor=white">
  <img src="https://img.shields.io/badge/Litecoin-A6A9AA?style=for-the-badge&logo=Litecoin&logoColor=white">
  <img src="https://img.shields.io/badge/Ethereum-3C3C3D?style=for-the-badge&logo=Ethereum&logoColor=white">
</div>



## Overview

This project is a Telegram bot powered by the Sellix API designed to generate cryptocurrency invoices and monitor them for confirmations before fulfilling the order. It uses SQLite3 for data storage and management. This bot serves as a foundational framework specifically for the payment module. If you plan to set up a comprehensive store or add additional features, further development will be required.

## Features

- **Crypto Invoice Generation**: Generate cryptocurrency invoices through the Sellix API directly from the Telegram bot.
- **Confirmation Tracking**: Wait for a predefined number of confirmations before considering the payment as fulfilled.
- **Data Management**: Utilize SQLite3 to store and manage transaction and invoice data efficiently.
- **Status and Cancel**: Commands to check for the status of an order or cancel it.

## Requirements

Before you begin, ensure you have met the following requirements:
- Python 3.11 or higher installed on your machine
- A Telegram bot token (You can obtain one through [@BotFather](https://t.me/botfather) on Telegram)
- Access to the Sellix API with your credentials [Sellix](https://sellix.io)

## Installation
- Clone this repo: ```https://github.com/Nix4444/crypto-invoice-telegram-bot```
- Install the requirements: ```pip install -r requirements.txt```
- Add the Telegram Bot Token and Sellix API Key in ``main.py``
- Start the bot: ```python main.py```


## PS
If you're wondering about past commits, I transfered this bot specifically the payment module, from my private repo which I do not wish to make public.