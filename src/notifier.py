#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📱 Telegram 알림 발송기
"""

import os
import aiohttp
from utils import load_config, setup_logging

logger = setup_logging()


class TelegramNotifier:
    """Telegram 봇을 통한 알림 발송"""
    
    TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
    
    def __init__(self):
        self.config = load_config()
        self.enabled = self.config['notification']['telegram']['enabled']
        
        self.bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if self.enabled and (not self.bot_token or not self.chat_id):
            logger.warning("Telegram 설정 누락, 알림 비활성화")
            self.enabled = False
    
    async def send(self, message: str) -> bool:
        """
        Telegram 메시지 발송
        
        Args:
            message: 발송할 메시지
            
        Returns:
            bool: 성공 여부
        """
        if not self.enabled:
            logger.info("Telegram 알림 비활성화됨")
            return False
        
        try:
            url = self.TELEGRAM_API_URL.format(token=self.bot_token)
            
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Telegram 알림 발송 완료")
                        return True
                    else:
                        error = await response.text()
                        logger.error(f"Telegram 발송 실패: {error}")
                        return False
                        
        except Exception as e:
            logger.error(f"Telegram 발송 오류: {str(e)}")
            return False
    
    async def send_photo(self, photo_url: str, caption: str) -> bool:
        """이미지와 함께 메시지 발송"""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            payload = {
                'chat_id': self.chat_id,
                'photo': photo_url,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload) as response:
                    return response.status == 200
                    
        except Exception as e:
            logger.error(f"Telegram 사진 발송 오류: {str(e)}")
            return False
    
    async def send_document(self, file_path: str, caption: str = "") -> bool:
        """파일 발송"""
        if not self.enabled:
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field('chat_id', self.chat_id)
                    data.add_field('document', f, filename=os.path.basename(file_path))
                    if caption:
                        data.add_field('caption', caption)
                    
                    async with session.post(url, data=data) as response:
                        return response.status == 200
                        
        except Exception as e:
            logger.error(f"Telegram 파일 발송 오류: {str(e)}")
            return False
