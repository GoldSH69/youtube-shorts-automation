#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📊 분석 및 기록 트래커
"""

import os
import json
import csv
from datetime import datetime
from typing import Optional

# Google Sheets (옵션)
try:
    import gspread
    from google.oauth2 import service_account
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

from utils import load_config, setup_logging

logger = setup_logging()


class AnalyticsTracker:
    """콘텐츠 분석 및 기록 관리"""
    
    def __init__(self):
        self.config = load_config()
        self.sheets_enabled = (
            self.config['analytics']['google_sheets']['enabled'] 
            and GSPREAD_AVAILABLE
        )
        self.csv_enabled = self.config['analytics']['local_csv']['enabled']
        
        self.sheets_client = None
        self.spreadsheet = None
        
        if self.sheets_enabled:
            self._init_google_sheets()
        
        # CSV 폴더 생성
        os.makedirs('data', exist_ok=True)
    
    def _init_google_sheets(self):
        """Google Sheets 초기화"""
        try:
            creds_json = os.environ.get('GOOGLE_CREDENTIALS')
            sheets_id = os.environ.get('GOOGLE_SHEETS_ID')
            
            if not creds_json or not sheets_id:
                logger.warning("Google Sheets 설정 누락, 비활성화")
                self.sheets_enabled = False
                return
            
            creds_dict = json.loads(creds_json)
            
            credentials = service_account.Credentials.from_service_account_info(
                creds_dict,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
            )
            
            self.sheets_client = gspread.authorize(credentials)
            self.spreadsheet = self.sheets_client.open_by_key(sheets_id)
            
            # 워크시트 확인/생성
            self._ensure_worksheet()
            
            logger.info("Google Sheets 연결 완료")
            
        except Exception as e:
            logger.error(f"Google Sheets 초기화 실패: {str(e)}")
            self.sheets_enabled = False
    
    def _ensure_worksheet(self):
        """워크시트 존재 확인 및 헤더 설정"""
        try:
            worksheet_name = "Upload History"
            
            try:
                worksheet = self.spreadsheet.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name,
                    rows=1000,
                    cols=10
                )
                
                # 헤더 설정
                headers = [
                    "날짜", "요일", "주제", "언어", "상태",
                    "제목", "Drive URL", "YouTube URL", "생성시간"
                ]
                worksheet.append_row(headers)
                
                logger.info(f"워크시트 생성됨: {worksheet_name}")
                
        except Exception as e:
            logger.error(f"워크시트 설정 실패: {str(e)}")
    
    async def record(
        self,
        date: str,
        day: str,
        topic: str,
        language: str,
        status: str,
        title: str = "",
        drive_url: str = "",
        youtube_url: str = ""
    ) -> bool:
        """
        기록 저장
        
        Args:
            date: 날짜 (YYYY-MM-DD)
            day: 요일 (monday, tuesday, ...)
            topic: 주제
            language: 언어
            status: 상태 (완료, 실패 등)
            title: 영상 제목
            drive_url: Drive URL
            youtube_url: YouTube URL
            
        Returns:
            bool: 성공 여부
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        record_data = {
            'date': date,
            'day': day,
            'topic': topic,
            'language': language,
            'status': status,
            'title': title,
            'drive_url': drive_url,
            'youtube_url': youtube_url,
            'timestamp': timestamp
        }
        
        success = True
        
        # Google Sheets 기록
        if self.sheets_enabled:
            try:
                worksheet = self.spreadsheet.worksheet("Upload History")
                row = [
                    date, day, topic, language, status,
                    title, drive_url, youtube_url, timestamp
                ]
                worksheet.append_row(row)
                logger.info("Google Sheets 기록 완료")
            except Exception as e:
                logger.error(f"Google Sheets 기록 실패: {str(e)}")
                success = False
        
        # CSV 기록 (항상)
        if self.csv_enabled:
            try:
                csv_path = 'data/upload_history.csv'
                file_exists = os.path.exists(csv_path)
                
                with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=record_data.keys())
                    
                    if not file_exists:
                        writer.writeheader()
                    
                    writer.writerow(record_data)
                
                logger.info("CSV 기록 완료")
            except Exception as e:
                logger.error(f"CSV 기록 실패: {str(e)}")
                success = False
        
        return success
    
    async def get_recent_records(self, days: int = 7) -> list:
        """최근 기록 조회"""
        records = []
        
        try:
            csv_path = 'data/upload_history.csv'
            
            if os.path.exists(csv_path):
                with open(csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    records = list(reader)
                
                # 최근 N일 필터링
                from datetime import datetime, timedelta
                cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                records = [r for r in records if r.get('date', '') >= cutoff]
                
        except Exception as e:
            logger.error(f"기록 조회 실패: {str(e)}")
        
        return records
    
    async def get_stats(self) -> dict:
        """통계 조회"""
        records = await self.get_recent_records(days=30)
        
        return {
            'total_videos': len(records),
            'korean_videos': len([r for r in records if r.get('language') == 'korean']),
            'english_videos': len([r for r in records if r.get('language') == 'english']),
            'success_rate': len([r for r in records if r.get('status') == '완료']) / max(len(records), 1) * 100
        }
