# -*- coding: utf-8 -*-
import aiohttp
import asyncio

async def rewrite(text: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
                'https://api.aicloud.sbercloud.ru/public/v2/rewriter/predict',
                json={
                    "instances": [
                        {
                            "text": text[:1500],
                            "temperature": 0.9,
                            "top_k": 50,
                            "top_p": 0.7,
                            "range_mode": "bertscore"
                        }
                    ]
                }
        ) as response:
            return (await response.json())['prediction_best']['bertscore']

async def main():
    print(await rewrite('Тестовый пример'))

if __name__ == '__main__':
    asyncio.run(main())
