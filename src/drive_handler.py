#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
☁️ Google Drive 핸들러
"""

import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from utils import load_config, setup_logging

logger = setup_logging()

SCOPES = ['https://www.googleapis.com/auth/drive.file']


class DriveHandler:
    """Google Drive 파일 업로드 관리"""
    
    def __init__(self):
        self.config = load_config()
        self.service = None
        self.folder_ids = {}  # 캐시
        self._authenticate()
    
    def _authenticate(self):
        """서비스 계정으로 인증"""
        try:
            # 환경 변수에서 인증 정보 가져오기
            creds_json = os.environ.get('GOOGLE_CREDENTIALS')
            
            if not creds_json:
                raise ValueError("GOOGLE_CREDENTIALS 환경변수가 설정되지 않았습니다.")
            
            # JSON 파싱
            creds_dict = json.loads(creds_json)
            
            # 서비스 계정 인증
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
            
            # Drive API 클라이언트 생성
            self.service = build('drive', 'v3', credentials=credentials)
            logger.info("Google Drive API 인증 완료")
            
        except Exception as e:
            logger.error(f"Drive 인증 실패: {str(e)}")
            raise
    
    async def upload(self, file_path: str, language: str) -> str:
        """
        파일을 Google Drive에 업로드
        
        Args:
            file_path: 업로드할 파일 경로
            language: "korean" 또는 "english"
            
        Returns:
            str: 공유 URL
        """
        try:
            # 폴더 ID 가져오기 (없으면 생성)
            folder_id = await self._get_or_create_folder(language)
            
            # 파일명 생성
            from datetime import datetime
            filename = os.path.basename(file_path)
            
            # 메타데이터
            file_metadata = {
                'name': filename,
                'parents': [folder_id]
            }
            
            # 미디어
            media = MediaFileUpload(
                file_path,
                mimetype='video/mp4',
                resumable=True
            )
            
            # 업로드
            logger.info(f"Drive 업로드 시작: {filename}")
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            
            # 공유 설정 (링크가 있는 사람 모두 보기 가능)
            self.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # 공유 링크 가져오기
            file = self.service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            web_link = file.get('webViewLink', f'https://drive.google.com/file/d/{file_id}')
            
            logger.info(f"Drive 업로드 완료: {web_link}")
            return web_link
            
        except Exception as e:
            logger.error(f"Drive 업로드 실패: {str(e)}")
            raise
    
    async def _get_or_create_folder(self, language: str) -> str:
        """폴더 ID 가져오기 (없으면 생성)"""
        
        # 캐시 확인
        if language in self.folder_ids:
            return self.folder_ids[language]
        
        folder_name = self.config['storage']['google_drive']['folder_name']
        subfolder_name = "한국어" if language == "korean" else "English"
        
        try:
            # 1. 메인 폴더 찾기/생성
            main_folder_id = await self._find_or_create_folder(folder_name, None)
            
            # 2. 서브 폴더 찾기/생성
            sub_folder_id = await self._find_or_create_folder(subfolder_name, main_folder_id)
            
            # 캐시 저장
            self.folder_ids[language] = sub_folder_id
            
            return sub_folder_id
            
        except Exception as e:
            logger.error(f"폴더 생성 실패: {str(e)}")
            raise
    
    async def _find_or_create_folder(self, name: str, parent_id: str = None) -> str:
        """폴더 찾기, 없으면 생성"""
        
        # 폴더 검색
        query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = self.service.files().list(
            q=query,
            fields='files(id, name)'
        ).execute()
        
        files = results.get('files', [])
        
        if files:
            return files[0]['id']
        
        # 폴더 생성
        file_metadata = {
            'name': name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = self.service.files().create(
            body=file_metadata,
            fields='id'
        ).execute()
        
        logger.info(f"폴더 생성됨: {name}")
        return folder.get('id')
