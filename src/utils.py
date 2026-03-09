#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 유틸리티 함수 모음
"""

import os
import json
import yaml
import logging
from datetime import datetime
import pytz


def setup_logging() -> logging.Logger:
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def load_config() -> dict:
    """config.yaml 로드"""
    config_path = 'config/config.yaml'
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_schedule() -> dict:
    """schedule.yaml 로드"""
    schedule_path = 'config/schedule.yaml'
    
    if not os.path.exists(schedule_path):
        raise FileNotFoundError(f"스케줄 파일을 찾을 수 없습니다: {schedule_path}")
    
    with open(schedule_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def load_prompts() -> dict:
    """prompts.yaml 로드"""
    prompts_path = 'config/prompts.yaml'
    
    if not os.path.exists(prompts_path):
        raise FileNotFoundError(f"프롬프트 파일을 찾을 수 없습니다: {prompts_path}")
    
    with open(prompts_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def get_day_of_week() -> str:
    """현재 요일 반환 (영어 소문자)"""
    # 한국 시간 기준
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst)
    
    days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    return days[now.weekday()]


def load_used_topics() -> list:
    """사용된 주제 목록 로드"""
    path = 'data/used_topics.json'
    
    if not os.path.exists(path):
        return []
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []


def save_used_topic(topic: str, summary: str):
    """사용된 주제 저장"""
    path = 'data/used_topics.json'
    os.makedirs('data', exist_ok=True)
    
    topics = load_used_topics()
    
    # 새 항목 추가
    topics.append({
        'date': datetime.now().strftime("%Y-%m-%d"),
        'day': get_day_of_week(),
        'topic': topic,
        'summary': summary
    })
    
    # 최근 100개만 유지
    topics = topics[-100:]
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)


def format_duration(seconds: float) -> str:
    """초를 MM:SS 형식으로 변환"""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def sanitize_filename(filename: str) -> str:
    """파일명에서 특수문자 제거"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename[:200]  # 길이 제한


def hex_to_rgb(hex_color: str) -> tuple:
    """HEX 색상을 RGB 튜플로 변환"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    """RGB 튜플을 HEX 색상으로 변환"""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)
