#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 YouTube Shorts 자동화 메인 실행 파일
"""

import os
import sys
import asyncio
import json
from datetime import datetime
import pytz

# 모듈 임포트
from content_generator import ContentGenerator
from tts_generator import TTSGenerator
from video_source import VideoSourceFetcher
from video_generator import VideoGenerator
from uploader import YouTubeUploader
from drive_handler import DriveHandler
from notifier import TelegramNotifier
from analytics import AnalyticsTracker
from utils import load_config, load_schedule, get_day_of_week, setup_logging

# 로깅 설정
logger = setup_logging()


class YouTubeShortsAutomation:
    """유튜브 쇼츠 자동화 메인 클래스"""
    
    def __init__(self, language: str = "korean"):
        """
        Args:
            language: "korean" 또는 "english"
        """
        self.language = language
        self.config = load_config()
        self.schedule = load_schedule()
        
        # 컴포넌트 초기화
        self.content_generator = ContentGenerator()
        self.tts_generator = TTSGenerator()
        self.video_fetcher = VideoSourceFetcher()
        self.video_generator = VideoGenerator()
        self.drive_handler = DriveHandler()
        self.notifier = TelegramNotifier()
        self.analytics = AnalyticsTracker()
        
        # YouTube 업로더 (옵션)
        if self.config['options']['auto_upload']:
            self.uploader = YouTubeUploader()
        else:
            self.uploader = None
            
        logger.info(f"초기화 완료: {language} 채널")
    
    async def run(self):
        """메인 실행 함수"""
        try:
            logger.info("=" * 50)
            logger.info("🎬 YouTube Shorts 자동화 시작")
            logger.info("=" * 50)
            
            # 1. 오늘의 설정 가져오기
            day_config = self._get_today_config()
            logger.info(f"📅 오늘의 주제: {day_config['topic']}")
            
            # 2. 스크립트 생성
            logger.info("🤖 Step 1: AI 스크립트 생성 중...")
            content = await self.content_generator.generate(
                day_config=day_config,
                language=self.language
            )
            logger.info(f"✅ 스크립트 생성 완료: {len(content['script'])}자")
            
            # 3. 음성 생성
            logger.info("🎙️ Step 2: 음성 생성 중...")
            audio_path = await self.tts_generator.generate(
                text=content['script'],
                voice=day_config['voice'],
                output_dir="temp"
            )
            logger.info(f"✅ 음성 생성 완료: {audio_path}")
            
            # 4. 배경 영상 다운로드
            logger.info("🎬 Step 3: 배경 영상 다운로드 중...")
            video_paths = await self.video_fetcher.fetch(
                keywords=day_config['keywords'],
                count=3
            )
            logger.info(f"✅ 영상 다운로드 완료: {len(video_paths)}개")
            
            # 5. 영상 합성
            logger.info("✂️ Step 4: 영상 합성 중...")
            final_video_path = await self.video_generator.create(
                script=content['script'],
                audio_path=audio_path,
                video_paths=video_paths,
                day_config=day_config,
                language=self.language
            )
            logger.info(f"✅ 영상 합성 완료: {final_video_path}")
            
            # 6. Google Drive 업로드
            logger.info("☁️ Step 5: Google Drive 업로드 중...")
            drive_url = await self.drive_handler.upload(
                file_path=final_video_path,
                language=self.language
            )
            logger.info(f"✅ Drive 업로드 완료: {drive_url}")
            
            # 7. YouTube 업로드 (옵션)
            youtube_url = None
            if self.uploader and self.config['options']['auto_upload']:
                logger.info("📺 Step 6: YouTube 업로드 중...")
                youtube_url = await self.uploader.upload(
                    video_path=final_video_path,
                    title=content['title'],
                    description=content['description'],
                    tags=content['tags'],
                    visibility=self.config['options']['upload_visibility']
                )
                logger.info(f"✅ YouTube 업로드 완료: {youtube_url}")
            
            # 8. 분석 기록
            logger.info("📊 Step 7: 분석 데이터 기록 중...")
            await self.analytics.record(
                date=datetime.now().strftime("%Y-%m-%d"),
                day=get_day_of_week(),
                topic=day_config['topic'],
                language=self.language,
                status="완료",
                drive_url=drive_url,
                youtube_url=youtube_url
            )
            logger.info("✅ 분석 기록 완료")
            
            # 9. 알림 전송
            logger.info("📱 Step 8: 알림 전송 중...")
            await self.notifier.send(
                message=self._create_notification_message(
                    content=content,
                    drive_url=drive_url,
                    youtube_url=youtube_url
                )
            )
            logger.info("✅ 알림 전송 완료")
            
            # 10. 정리
            self._cleanup()
            
            logger.info("=" * 50)
            logger.info("🎉 자동화 완료!")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 오류 발생: {str(e)}")
            await self.notifier.send(f"❌ 오류 발생: {str(e)}")
            raise
    
    def _get_today_config(self) -> dict:
        """오늘 요일에 맞는 설정 반환"""
        day = get_day_of_week()  # monday, tuesday, ...
        day_schedule = self.schedule['schedule'][day]
        
        topic_key = 'topic_kr' if self.language == 'korean' else 'topic_en'
        voice_key = 'voice_kr' if self.language == 'korean' else 'voice_en'
        
        return {
            'day': day,
            'topic': day_schedule[topic_key],
            'keywords': day_schedule['keywords'],
            'color_primary': day_schedule['color_primary'],
            'color_secondary': day_schedule['color_secondary'],
            'color_text': day_schedule['color_text'],
            'bgm_style': day_schedule['bgm_style'],
            'voice': day_schedule[voice_key],
            'voice_style': day_schedule['voice_style']
        }
    
    def _create_notification_message(self, content: dict, drive_url: str, youtube_url: str = None) -> str:
        """알림 메시지 생성"""
        lang_emoji = "🇰🇷" if self.language == "korean" else "🇺🇸"
        channel_name = self.config['channels'][self.language]['name']
        
        message = f"""
{lang_emoji} **{channel_name}** 영상 생성 완료!

📌 **제목**: {content['title']}
📅 **날짜**: {datetime.now().strftime("%Y-%m-%d")}

📁 **Google Drive**: {drive_url}
"""
        if youtube_url:
            message += f"📺 **YouTube**: {youtube_url}\n"
            message += f"\n✅ 비공개 상태로 업로드됨 - 검토 후 공개하세요!"
        
        return message
    
    def _cleanup(self):
        """임시 파일 정리"""
        import shutil
        temp_dir = "temp"
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            os.makedirs(temp_dir)
        logger.info("🧹 임시 파일 정리 완료")


async def main():
    """메인 엔트리 포인트"""
    # 언어 파라미터 받기
    language = os.environ.get('LANGUAGE', 'korean')
    
    if language not in ['korean', 'english']:
        print(f"Invalid language: {language}")
        sys.exit(1)
    
    # 자동화 실행
    automation = YouTubeShortsAutomation(language=language)
    success = await automation.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
