#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎬 배경 영상 소스 다운로더 (Pexels API)
"""

import os
import aiohttp
import aiofiles
import asyncio
from utils import setup_logging

logger = setup_logging()


class VideoSourceFetcher:
    """Pexels API를 사용한 무료 영상 다운로드"""
    
    PEXELS_API_URL = "https://api.pexels.com/videos/search"
    
    def __init__(self):
        self.api_key = os.environ.get('PEXELS_API_KEY')
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY 환경변수가 설정되지 않았습니다.")
        
        os.makedirs('temp/videos', exist_ok=True)
    
    async def fetch(self, keywords: list, count: int = 3) -> list:
        """
        키워드 기반 영상 검색 및 다운로드
        
        Args:
            keywords: 검색 키워드 리스트
            count: 다운로드할 영상 개수
            
        Returns:
            list: 다운로드된 영상 파일 경로 리스트
        """
        try:
            video_paths = []
            
            # 키워드로 검색
            search_query = ' '.join(keywords[:3])  # 최대 3개 키워드
            
            async with aiohttp.ClientSession() as session:
                # API 요청
                headers = {'Authorization': self.api_key}
                params = {
                    'query': search_query,
                    'orientation': 'portrait',  # 세로 영상
                    'size': 'medium',
                    'per_page': count * 2  # 여유있게 검색
                }
                
                async with session.get(
                    self.PEXELS_API_URL,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Pexels API 오류: {response.status}")
                    
                    data = await response.json()
                    videos = data.get('videos', [])
                    
                    if not videos:
                        logger.warning(f"'{search_query}' 검색 결과 없음, 기본 키워드로 재시도")
                        return await self._fetch_fallback(session, count)
                    
                    # 영상 다운로드
                    for i, video in enumerate(videos[:count]):
                        video_url = self._get_best_video_url(video)
                        if video_url:
                            path = await self._download_video(
                                session, 
                                video_url, 
                                f"temp/videos/bg_{i}.mp4"
                            )
                            if path:
                                video_paths.append(path)
            
            logger.info(f"총 {len(video_paths)}개 영상 다운로드 완료")
            return video_paths
            
        except Exception as e:
            logger.error(f"영상 다운로드 실패: {str(e)}")
            raise
    
    def _get_best_video_url(self, video_data: dict) -> str:
        """최적의 영상 URL 선택 (세로, HD)"""
        video_files = video_data.get('video_files', [])
        
        # 세로 영상 우선 (height > width)
        portrait_videos = [
            v for v in video_files 
            if v.get('height', 0) > v.get('width', 0)
        ]
        
        # HD 품질 (720p 이상)
        target_videos = portrait_videos if portrait_videos else video_files
        hd_videos = [v for v in target_videos if v.get('height', 0) >= 720]
        
        if hd_videos:
            # 가장 적절한 크기 선택 (1080p 선호)
            sorted_videos = sorted(hd_videos, key=lambda x: abs(x.get('height', 0) - 1080))
            return sorted_videos[0].get('link')
        elif target_videos:
            return target_videos[0].get('link')
        
        return None
    
    async def _download_video(self, session: aiohttp.ClientSession, url: str, path: str) -> str:
        """영상 다운로드"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(path, 'wb') as f:
                        await f.write(await response.read())
                    logger.info(f"다운로드 완료: {path}")
                    return path
        except Exception as e:
            logger.error(f"다운로드 실패: {str(e)}")
        return None
    
    async def _fetch_fallback(self, session: aiohttp.ClientSession, count: int) -> list:
        """대체 키워드로 검색"""
        fallback_keywords = ['abstract', 'motion', 'gradient', 'minimal']
        
        headers = {'Authorization': self.api_key}
        params = {
            'query': ' '.join(fallback_keywords),
            'orientation': 'portrait',
            'per_page': count
        }
        
        video_paths = []
        
        async with session.get(
            self.PEXELS_API_URL,
            headers=headers,
            params=params
        ) as response:
            data = await response.json()
            videos = data.get('videos', [])
            
            for i, video in enumerate(videos[:count]):
                video_url = self._get_best_video_url(video)
                if video_url:
                    path = await self._download_video(
                        session,
                        video_url,
                        f"temp/videos/bg_{i}.mp4"
                    )
                    if path:
                        video_paths.append(path)
        
        return video_paths
