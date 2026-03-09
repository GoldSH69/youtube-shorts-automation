#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 API 테스트 스크립트
"""

import os
import sys
import asyncio

def test_gemini():
    """Gemini API 테스트"""
    print("🤖 Testing Gemini API...")
    try:
        import google.generativeai as genai
        
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("❌ GEMINI_API_KEY not found")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        response = model.generate_content("Say 'Hello, test successful!' in Korean")
        print(f"✅ Gemini Response: {response.text[:100]}")
        return True
    except Exception as e:
        print(f"❌ Gemini Error: {str(e)}")
        return False

def test_pexels():
    """Pexels API 테스트"""
    print("🎬 Testing Pexels API...")
    try:
        import requests
        
        api_key = os.environ.get('PEXELS_API_KEY')
        if not api_key:
            print("❌ PEXELS_API_KEY not found")
            return False
        
        headers = {'Authorization': api_key}
        response = requests.get(
            'https://api.pexels.com/videos/search',
            headers=headers,
            params={'query': 'nature', 'per_page': 1}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Pexels Response: Found {data.get('total_results', 0)} videos")
            return True
        else:
            print(f"❌ Pexels Error: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Pexels Error: {str(e)}")
        return False

async def test_tts():
    """Edge TTS 테스트"""
    print("🎙️ Testing Edge TTS...")
    try:
        import edge_tts
        import asyncio
        
        # 여러 번 재시도
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate("테스트 음성입니다.", "ko-KR-InJoonNeural")
                await communicate.save("test_audio.mp3")
                
                if os.path.exists("test_audio.mp3"):
                    size = os.path.getsize("test_audio.mp3")
                    os.remove("test_audio.mp3")
                    print(f"✅ TTS Success: Generated {size} bytes")
                    return True
            except Exception as e:
                print(f"⚠️ TTS attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2)
        
        print("❌ TTS Error: All attempts failed")
        return False
    except Exception as e:
        print(f"❌ TTS Error: {str(e)}")
        return False

async def test_telegram():
    """Telegram 테스트"""
    print("📱 Testing Telegram...")
    try:
        import aiohttp
        
        bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            print("❌ Telegram credentials not found")
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': '🧪 테스트 메시지: YouTube Shorts 자동화 시스템이 정상 작동합니다!'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    print("✅ Telegram message sent successfully")
                    return True
                else:
                    print(f"❌ Telegram Error: Status {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Telegram Error: {str(e)}")
        return False

def test_drive():
    """Google Drive 테스트"""
    print("☁️ Testing Google Drive...")
    try:
        import json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        creds_json = os.environ.get('GOOGLE_CREDENTIALS')
        if not creds_json:
            print("❌ GOOGLE_CREDENTIALS not found")
            return False
        
        creds_dict = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 간단한 API 호출 테스트
        results = service.files().list(pageSize=1).execute()
        print(f"✅ Google Drive connected successfully")
        return True
    except Exception as e:
        print(f"❌ Google Drive Error: {str(e)}")
        return False

async def main():
    test_type = sys.argv[1] if len(sys.argv) > 1 else 'all'
    
    print("=" * 50)
    print("🧪 YouTube Shorts Automation - API Test")
    print("=" * 50)
    
    results = {}
    
    if test_type in ['all', 'gemini']:
        results['gemini'] = test_gemini()
    
    if test_type in ['all', 'pexels']:
        results['pexels'] = test_pexels()
    
    if test_type in ['all', 'tts']:
        results['tts'] = await test_tts()
    
    if test_type in ['all', 'telegram']:
        results['telegram'] = await test_telegram()
    
    if test_type in ['all', 'drive']:
        results['drive'] = test_drive()
    
    print("\n" + "=" * 50)
    print("📊 Test Results")
    print("=" * 50)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed"))
    
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    asyncio.run(main())
