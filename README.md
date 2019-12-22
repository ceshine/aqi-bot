# aqi-bot

[![Build Status](https://travis-ci.org/ceshine/aqi-bot.svg?branch=master)](https://travis-ci.org/ceshine/aqi-bot)

A minimal Telegram AQI notification bot

The latest version uses [Cloud Firestore](https://firebase.google.com/docs/firestore) as the persistent storage backend. The original in-memory version can be found in the [in-memory](https://github.com/ceshine/aqi-bot/tree/in-memory) branch.

## Set Up

You need to provide two environment variables:

1. AQI_TOKEN
2. BOT_TOKEN

And save your [service account JSON keyfile from Google Cloud](https://googleapis.dev/python/google-api-core/latest/auth.html) as `keyfile.json` in the root folder.

### AQI token

Get your token from [aqi.cn](http://aqicn.org/data-platform/token/#/).

### Bot token

Get your token from [@BotFather](https://telegram.me/BotFather)

### Cloud Firestore

This bot uses collection named `subscriptions`, and use the `chat_id` as key.

The free tier should be more than enough to cover the read/write from this bot. However, currently we haven't implemented anti-abuse mechanisms. Be extra careful if you've enabled billing for your project.

### Docker

We provide a simple Dockerfile and sample docker-compose.yml for you to get started.

## Public Demo Bot

[@aqi_monitor_bot](https://t.me/aqi_monitor_bot)

Please do not abuse this service (excessive /set, /unset, or /get commands).

## Usage

### 1. Find the nearest station

`/find <lat> <lng>`

![find.png](imgs/find.png)

### 2. Subscribe

Use the station id from `/find`.
`/set <station_id>`

![set](imgs/set.png)

### 3. Unsubsribe

`/unset`

![unset](imgs/unset.png)

## Missing Features

### 1. Adaptive notification

Adjust behaviors according to the pollution level.

### 2. More robust schedule

Sometimes the update from an station can be delayed for more than 20 minutes(the maximum allowed delay in the current setting). Need a retry mechanism.
