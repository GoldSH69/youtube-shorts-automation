#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎙️ TTS 음성 생성기 (Edge TTS)
"""

import os
import asyncio
import edge_tts
from utils import setup_logging

logger = setup_logging()


class TTSGenerator:
    """Edge TTS를 사용한 음성 생성"""
    
    # 사용 가능한 음성 목록
    VOICES = {
        # 한국어
        'ko-KR-InJoonNeural': '한국어 남성 (인준)',
        'ko-KR-SunHiNeural': '한국어 여성 (선희)',
        # 영어 (미국)
        'en-US-GuyNeural': '영어 남성 (Guy)',
        'en-US-JennyNeural': '영어 여성 (Jenny)',
        'en-US-AriaNeural': '영어 여성 (Aria)',
        # 영어 (영국)
        'en-GB-RyanNeural': '영국 남성 (Ryan)',
        'en-GB-SoniaNeural': '영국 여성 (Sonia)',
    }
    
    def __init__(self):
        # temp 폴더 생성
        os.makedirs('temp', exist_ok=True)
        
    async def generate(self, text: str, voice: str, output_dir: str = "temp") -> str:
        """
        텍스트를 음성으로 변환
        
        Args:
            text: 변환할 텍스트
            voice: Edge TTS 음성 코드
            output_dir: 출력 디렉토리
            
        Returns:
            str: 생성된 음성 파일 경로
        """
        try:
            # 출력 경로
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "voice.mp3")
            
            # 음성 검증
            if voice not in self.VOICES:
                logger.warning(f"알 수 없는 음성: {voice}, 기본값 사용")
                voice = 'ko-KR-InJoonNeural'
            
            logger.info(f"음성 생성 시작: {voice}")
            
            # Edge TTS 생성
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            
            # 파일 크기 확인
            file_size = os.path.getsize(output_path)
            logger.info(f"음성 파일 생성: {output_path} ({file_size} bytes)")
            
            return output_path
            
        except Exception as e:
            logger.error(f"TTS 생성 실패: {str(e)}")
            raise
    
    async def get_audio_duration(self, audio_path: str) -> float:
        """오디오 파일 길이 반환 (초)"""
        try:
            from moviepy.editor import AudioFileClip
            
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            audio.close()
            
            return duration
        except Exception as e:
            logger.error(f"오디오 길이 측정 실패: {str(e)}")
            return 30.0  # 기본값
    
    @staticmethod
    def list_voices():
        """사용 가능한 음성 목록 출력"""
        for code, name in TTSGenerator.VOICES.items():
            print(f"{code}: {name}")
