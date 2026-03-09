#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 업로더 - OAuth 환경변수 방식
"""

import os
import json
import logging
import asyncio
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/youtube.upload',
    'https://www.googleapis.com/auth/youtube.readonly'
]


class YouTubeUploader:
    """YouTube 업로더 - 환경변수로 직접 인증"""
    
    def __init__(self):
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """
        환경변수로 직접 인증
        - 파일 기반 인증 X
        - InstalledAppFlow X (이게 오류 원인이었음)
        """
        try:
            # 환경변수에서 가져오기
            client_id     = os.environ.get('YOUTUBE_CLIENT_ID', '').strip()
            client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET', '').strip()
            refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN', '').strip()
            
            # 누락 확인
            missing = []
            if not client_id:     missing.append('YOUTUBE_CLIENT_ID')
            if not client_secret: missing.append('YOUTUBE_CLIENT_SECRET')
            if not refresh_token: missing.append('YOUTUBE_REFRESH_TOKEN')
            
            if missing:
                raise ValueError(f"❌ 누락된 GitHub Secrets: {', '.join(missing)}")
            
            logger.info(f"CLIENT_ID: {client_id[:20]}...")
            logger.info(f"REFRESH_TOKEN: {refresh_token[:20]}...")
            
            # Credentials 직접 생성 (파일 없이)
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES
            )
            
            # 액세스 토큰 갱신
            credentials.refresh(Request())
            
            # YouTube API 클라이언트 생성
            self.youtube = build(
                'youtube', 'v3',
                credentials=credentials,
                cache_discovery=False  # file_cache 경고 제거
            )
            
            logger.info("✅ YouTube 인증 완료")
            
        except ValueError as e:
            logger.error(str(e))
            raise
        except Exception as e:
            logger.error(f"❌ YouTube 인증 실패: {e}")
            raise
    
    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        visibility: str = "private"  # 기본값: 비공개
    ) -> str:
        """
        YouTube에 영상 업로드 (async 래퍼)
        
        Returns:
            YouTube URL (https://youtube.com/shorts/{video_id})
        """
        # 동기 함수를 async로 실행
        loop = asyncio.get_event_loop()
        video_id = await loop.run_in_executor(
            None,
            self._upload_sync,
            video_path, title, description, tags, visibility
        )
        return f"https://youtube.com/shorts/{video_id}"
    
    def _upload_sync(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list = None,
        visibility: str = "private"
    ) -> str:
        """실제 업로드 (동기)"""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"영상 파일 없음: {video_path}")
        
        file_size = os.path.getsize(video_path)
        logger.info(f"📤 업로드 시작: {title} ({file_size / 1024 / 1024:.1f}MB)")
        
        # 메타데이터
        body = {
            'snippet': {
                'title': title[:100],
                'description': description[:5000],
                'tags': tags or [],
                'categoryId': '22',  # People & Blogs
            },
            'status': {
                'privacyStatus': visibility,
                'selfDeclaredMadeForKids': False,
                'madeForKids': False,
            }
        }
        
        # 미디어 파일
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True,
            chunksize=5 * 1024 * 1024  # 5MB 청크
        )
        
        try:
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            # 청크 업로드
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    logger.info(f"  업로드 진행: {pct}%")
            
            video_id = response['id']
            logger.info(f"✅ 업로드 완료: https://youtube.com/shorts/{video_id}")
            
            # 기록 저장
            self._save_history(video_id, title, visibility)
            
            return video_id
            
        except HttpError as e:
            error_content = json.loads(e.content.decode())
            error_message = error_content.get('error', {}).get('message', str(e))
            logger.error(f"❌ YouTube API 오류: {error_message}")
            raise
    
    def _save_history(self, video_id: str, title: str, visibility: str):
        """업로드 기록 저장"""
        history_file = "data/upload_history.json"
        os.makedirs("data", exist_ok=True)
        
        try:
            history = []
            if os.path.exists(history_file):
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            
            history.append({
                "video_id": video_id,
                "title": title,
                "url": f"https://youtube.com/shorts/{video_id}",
                "visibility": visibility,
                "uploaded_at": datetime.now().isoformat()
            })
            
            # 최근 500개만 유지
            history = history[-500:]
            
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.warning(f"⚠️ 업로드 기록 저장 실패 (무시): {e}")
