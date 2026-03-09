#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📺 YouTube 업로더
"""

import os
import json
import pickle
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from utils import setup_logging

logger = setup_logging()

# YouTube API 범위
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']


class YouTubeUploader:
    """YouTube 영상 업로더"""
    
    def __init__(self):
        self.credentials = None
        self.youtube = None
        self._authenticate()
    
    def _authenticate(self):
        """YouTube API 인증"""
        try:
            # 1. 저장된 토큰 확인
            token_path = 'config/youtube_token.pickle'
            
            if os.path.exists(token_path):
                with open(token_path, 'rb') as token:
                    self.credentials = pickle.load(token)
            
            # 2. 토큰 갱신 필요 여부 확인
            if not self.credentials or not self.credentials.valid:
                if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    # 환경 변수에서 클라이언트 시크릿 가져오기
                    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
                    
                    if client_secret:
                        # JSON 문자열을 파일로 저장
                        client_secret_path = 'temp/client_secret.json'
                        os.makedirs('temp', exist_ok=True)
                        
                        with open(client_secret_path, 'w') as f:
                            f.write(client_secret)
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            client_secret_path, SCOPES
                        )
                        self.credentials = flow.run_local_server(port=0)
                        
                        # 임시 파일 삭제
                        os.remove(client_secret_path)
                    else:
                        raise ValueError("YOUTUBE_CLIENT_SECRET 환경변수가 필요합니다.")
                
                # 토큰 저장
                os.makedirs('config', exist_ok=True)
                with open(token_path, 'wb') as token:
                    pickle.dump(self.credentials, token)
            
            # 3. YouTube API 클라이언트 생성
            self.youtube = build('youtube', 'v3', credentials=self.credentials)
            logger.info("YouTube API 인증 완료")
            
        except Exception as e:
            logger.error(f"YouTube 인증 실패: {str(e)}")
            raise
    
    async def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        visibility: str = 'private'
    ) -> str:
        """
        YouTube에 영상 업로드
        
        Args:
            video_path: 영상 파일 경로
            title: 영상 제목
            description: 영상 설명
            tags: 태그 리스트
            visibility: 'private', 'public', 'unlisted'
            
        Returns:
            str: 업로드된 영상 URL
        """
        try:
            logger.info(f"YouTube 업로드 시작: {title}")
            
            # 메타데이터 설정
            body = {
                'snippet': {
                    'title': title[:100],  # 최대 100자
                    'description': description[:5000],  # 최대 5000자
                    'tags': tags[:500],  # 태그 제한
                    'categoryId': '22'  # People & Blogs
                },
                'status': {
                    'privacyStatus': visibility,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # 미디어 파일 준비
            media = MediaFileUpload(
                video_path,
                mimetype='video/mp4',
                resumable=True,
                chunksize=1024*1024  # 1MB chunks
            )
            
            # 업로드 실행
            request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"업로드 진행: {int(status.progress() * 100)}%")
            
            video_id = response['id']
            video_url = f"https://youtu.be/{video_id}"
            
            logger.info(f"YouTube 업로드 완료: {video_url}")
            return video_url
            
        except Exception as e:
            logger.error(f"YouTube 업로드 실패: {str(e)}")
            raise
    
    def get_channel_info(self) -> dict:
        """채널 정보 조회"""
        try:
            request = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            )
            response = request.execute()
            
            if response['items']:
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'subscribers': channel['statistics'].get('subscriberCount', 0)
                }
            return None
        except Exception as e:
            logger.error(f"채널 정보 조회 실패: {str(e)}")
            return None
