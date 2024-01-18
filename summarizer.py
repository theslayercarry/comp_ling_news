# -*- coding: utf-8 -*-

# summarizer.py
import aiohttp
import asyncio

async def summarize(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
                'https://api.aicloud.sbercloud.ru/public/v2/summarizator/predict',
                json={
                    "instances": [
                        {
                            "text": text[:1000],
                            "num_beams": 5,
                            "num_return_sequences": 3,
                            "length_penalty": 0.5
                        }
                    ]
                }
        ) as response:
            return (await response.json())['prediction_best']['bertscore']

async def main():
        print(await summarize('Тестовый пример'))

if __name__ == '__main__':
    asyncio.run(main())
