#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎙️ TTS 음성 생성기 (Edge TTS + gTTS 대체)
"""

import os
import asyncio
from utils import setup_logging

logger = setup_logging()


class TTSGenerator:
    """TTS 음성 생성 (Edge TTS 실패 시 gTTS 사용)"""
    
    # Edge TTS 음성 목록
    VOICES = {
        'ko-KR-InJoonNeural': '한국어 남성 (인준)',
        'ko-KR-SunHiNeural': '한국어 여성 (선희)',
        'en-US-GuyNeural': '영어 남성 (Guy)',
        'en-US-JennyNeural': '영어 여성 (Jenny)',
    }
    
    # gTTS 언어 매핑
    GTTS_LANG = {
        'ko-KR-InJoonNeural': 'ko',
        'ko-KR-SunHiNeural': 'ko',
        'en-US-GuyNeural': 'en',
        'en-US-JennyNeural': 'en',
    }
    
    def __init__(self):
        os.makedirs('temp', exist_ok=True)
        
    async def generate(self, text: str, voice: str, output_dir: str = "temp") -> str:
        """
        텍스트를 음성으로 변환
        Edge TTS 실패 시 gTTS로 대체
        """
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "voice.mp3")
        
        # 1차 시도: Edge TTS
        try:
            logger.info(f"Edge TTS 시도: {voice}")
            success = await self._try_edge_tts(text, voice, output_path)
            if success:
                return output_path
        except Exception as e:
            logger.warning(f"Edge TTS 실패: {str(e)}")
        
        # 2차 시도: gTTS
        try:
            logger.info("gTTS로 대체 시도...")
            success = await self._try_gtts(text, voice, output_path)
            if success:
                return output_path
        except Exception as e:
            logger.error(f"gTTS도 실패: {str(e)}")
            raise
        
        raise Exception("모든 TTS 방법 실패")
    
    async def _try_edge_tts(self, text: str, voice: str, output_path: str) -> bool:
        """Edge TTS 시도"""
        import edge_tts
        
        for attempt in range(2):
            try:
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"Edge TTS 성공")
                    return True
            except Exception as e:
                logger.warning(f"Edge TTS 시도 {attempt + 1} 실패")
                await asyncio.sleep(1)
        
        return False
    
    async def _try_gtts(self, text: str, voice: str, output_path: str) -> bool:
        """gTTS 대체"""
        from gtts import gTTS
        
        # 언어 결정
        lang = self.GTTS_LANG.get(voice, 'ko')
        
        # gTTS 생성
        tts = gTTS(text=text, lang=lang, slow=False)
        tts.save(output_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"gTTS 성공: {lang}")
            return True
        
        return False
    
    async def get_audio_duration(self, audio_path: str) -> float:
        """오디오 파일 길이 반환"""
        try:
            from moviepy.editor import AudioFileClip
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            return duration
        except Exception as e:
            logger.error(f"오디오 길이 측정 실패: {str(e)}")
            return 30.0
