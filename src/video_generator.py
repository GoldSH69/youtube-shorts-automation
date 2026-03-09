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
from moviepy.video.fx.all import resize
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
                logger=None
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
        target_size = (self.video_config['width'], self.video_config['height'])
        
        if not video_paths:
            # 영상이 없으면 그라데이션 배경
            logger.warning("배경 영상 없음, 단색 배경 사용")
            return ColorClip(
                size=target_size,
                color=(30, 30, 40)
            ).set_duration(duration)
        
        clips = []
        total_duration = 0
        
        for video_path in video_paths:
            try:
                clip = VideoFileClip(video_path)
                
                # 세로 비율로 리사이즈
                clip_ratio = clip.w / clip.h
                target_ratio = target_size[0] / target_size[1]
                
                if clip_ratio > target_ratio:
                    # 영상이 더 넓음 -> 높이 기준
                    new_height = target_size[1]
                    new_width = int(new_height * clip_ratio)
                else:
                    # 영상이 더 좁음 -> 너비 기준
                    new_width = target_size[0]
                    new_height = int(new_width / clip_ratio)
                
                clip = clip.resize((new_width, new_height))
                
                # 중앙 크롭
                x_center = new_width // 2
                y_center = new_height // 2
                x1 = x_center - target_size[0] // 2
                y1 = y_center - target_size[1] // 2
                
                clip = clip.crop(
                    x1=max(0, x1),
                    y1=max(0, y1),
                    width=target_size[0],
                    height=target_size[1]
                )
                
                clips.append(clip)
                total_duration += clip.duration
                
                if total_duration >= duration:
                    break
                    
            except Exception as e:
                logger.warning(f"영상 로드 실패: {video_path}, {str(e)}")
                continue
        
        if not clips:
            return ColorClip(size=target_size, color=(30, 30, 40)).set_duration(duration)
        
        # 영상 이어붙이기
        if len(clips) == 1:
            bg_clip = clips[0]
            if bg_clip.duration < duration:
                # 반복
                bg_clip = bg_clip.loop(duration=duration)
        else:
            bg_clip = concatenate_videoclips(clips)
        
        # 길이 맞추기
        bg_clip = bg_clip.set_duration(duration)
        
        # 약간 어둡게 (자막 가독성)
        bg_clip = bg_clip.fl_image(lambda frame: (frame * 0.7).astype('uint8'))
        
        return bg_clip
    
    async def _create_subtitles(
        self,
        script: str,
        duration: float,
        color: str,
        bg_color: str,
        language: str
    ) -> list:
        """자막 클립 생성"""
        subtitle_clips = []
        
        # 문장 단위로 분리
        sentences = self._split_sentences(script, language)
        
        if not sentences:
            return subtitle_clips
        
        # 각 문장의 표시 시간 계산
        time_per_sentence = duration / len(sentences)
        
        font = self.subtitle_config['font_korean'] if language == 'korean' else self.subtitle_config['font_english']
        font_size = self.subtitle_config['font_size']
        
        for i, sentence in enumerate(sentences):
            start_time = i * time_per_sentence
            end_time = start_time + time_per_sentence
            
            try:
                # 텍스트 클립 생성
                txt_clip = TextClip(
                    sentence,
                    fontsize=font_size,
                    color=color,
                    font=font,
                    stroke_color=self.subtitle_config['stroke_color'],
                    stroke_width=self.subtitle_config['stroke_width'],
                    method='caption',
                    size=(self.video_config['width'] - 100, None),
                    align='center'
                )
                
                # 위치 설정 (중앙 또는 하단)
                if self.subtitle_config['position'] == 'center':
                    txt_clip = txt_clip.set_position(('center', 'center'))
                else:
                    txt_clip = txt_clip.set_position(
                        ('center', self.video_config['height'] - self.subtitle_config['margin_bottom'])
                    )
                
                # 시간 설정
                txt_clip = txt_clip.set_start(start_time).set_end(end_time)
                
                # 페이드 효과
                txt_clip = txt_clip.crossfadein(0.2).crossfadeout(0.2)
                
                subtitle_clips.append(txt_clip)
                
            except Exception as e:
                logger.warning(f"자막 생성 실패: {sentence[:20]}..., {str(e)}")
                continue
        
        return subtitle_clips
    
    def _split_sentences(self, text: str, language: str) -> list:
        """텍스트를 문장 단위로 분리"""
        # 줄바꿈으로 먼저 분리
        lines = text.strip().split('\n')
        
        sentences = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if language == 'korean':
                # 한국어: 문장 부호로 분리
                import re
                parts = re.split(r'(?<=[.!?])\s*', line)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 2:
                        # 너무 긴 문장은 추가 분리
                        if len(part) > 40:
                            mid = len(part) // 2
                            # 공백 위치 찾기
                            space_pos = part.find(' ', mid - 10)
                            if space_pos > 0:
                                sentences.append(part[:space_pos].strip())
                                sentences.append(part[space_pos:].strip())
                            else:
                                sentences.append(part)
                        else:
                            sentences.append(part)
            else:
                # 영어: 문장 부호로 분리
                import re
                parts = re.split(r'(?<=[.!?])\s+', line)
                for part in parts:
                    part = part.strip()
                    if part and len(part) > 2:
                        sentences.append(part)
        
        return sentences
