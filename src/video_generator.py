#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
✂️ 영상 합성기 (MoviePy)
"""

import os
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, 
    CompositeVideoClip, concatenate_videoclips,
    ColorClip
)
from moviepy.video.fx.all import resize, loop
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from utils import load_config, setup_logging

logger = setup_logging()


class VideoGenerator:
    """영상 합성 및 편집"""
    
    def __init__(self):
        self.config = load_config()
        self.video_config = self.config['video']
        self.subtitle_config = self.config['subtitle']
        
        # 출력 폴더 생성
        os.makedirs('output', exist_ok=True)
        os.makedirs('temp', exist_ok=True)
    
    async def create(
        self,
        script: str,
        audio_path: str,
        video_paths: list,
        day_config: dict,
        language: str
    ) -> str:
        """
        최종 영상 생성
        
        Args:
            script: 자막용 스크립트
            audio_path: 음성 파일 경로
            video_paths: 배경 영상 경로 리스트
            day_config: 오늘의 설정 (색상 등)
            language: "korean" 또는 "english"
            
        Returns:
            str: 생성된 영상 파일 경로
        """
        try:
            logger.info("영상 합성 시작...")
            
            # 1. 오디오 로드 및 길이 확인
            audio = AudioFileClip(audio_path)
            duration = min(audio.duration, self.video_config['duration'])
            logger.info(f"오디오 길이: {duration:.1f}초")
            
            # 2. 배경 영상 준비
            bg_clip = await self._prepare_background(video_paths, duration)
            
            # 3. 자막 생성
            subtitle_clips = await self._create_subtitles(
                script=script,
                duration=duration,
                color=day_config['color_text'],
                bg_color=day_config['color_primary'],
                language=language
            )
            
            # 4. 합성
            final_clip = CompositeVideoClip(
                [bg_clip] + subtitle_clips,
                size=(self.video_config['width'], self.video_config['height'])
            )
            
            # 5. 오디오 추가
            final_clip = final_clip.set_audio(audio)
            final_clip = final_clip.set_duration(duration)
            
            # 6. 출력
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"output/{language}_{timestamp}.mp4"
            
            logger.info("영상 렌더링 중... (시간이 걸릴 수 있습니다)")
            
            final_clip.write_videofile(
                output_path,
                fps=self.video_config['fps'],
                codec='libx264',
                audio_codec='aac',
                preset='medium',
                threads=2,
                logger=None  # MoviePy 로그 끄기
            )
            
            # 정리
            final_clip.close()
            audio.close()
            
            logger.info(f"영상 생성 완료: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"영상 생성 실패: {str(e)}")
            raise
    
    async def _prepare_background(self, video_paths: list, duration: float) -> VideoFileClip:
        """배경 영상 준비 (반복, 리사이즈)"""
        if not video_paths:
            # 영상이 없으면 검은색 배경
            return ColorClip(
                size=(self.video_config['width'], self.video_config['height']),
                color=(20, 20, 20)
            ).set_duration(duration)
        
