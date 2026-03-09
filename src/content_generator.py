#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 AI 콘텐츠 생성기 (Gemini API)
"""

import os
import json
import google.generativeai as genai
from utils import load_config, load_prompts, load_used_topics, save_used_topic, setup_logging

logger = setup_logging()


class ContentGenerator:
    """Gemini API를 사용한 콘텐츠 생성"""
    
    def __init__(self):
        # API 키 설정
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        
        genai.configure(api_key=api_key)
        
        # 작동하는 모델 찾기
        self.model = self._get_working_model()
        
        self.config = load_config()
        self.prompts = load_prompts()
        self.used_topics = load_used_topics()
    
    def _get_working_model(self):
        """작동하는 Gemini 모델 찾기"""
        model_names = [
            'gemini-2.5-flash',      # 최신 모델 (테스트 통과!)
            'gemini-2.0-flash',
            'gemini-flash-latest',
            'gemini-pro-latest',
            'gemini-1.5-flash',
        ]
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                # 간단한 테스트
                response = model.generate_content("Hi")
                if response.text:
                    logger.info(f"Gemini 모델 선택됨: {model_name}")
                    return model
            except Exception as e:
                logger.warning(f"모델 {model_name} 실패: {str(e)[:30]}")
                continue
        
        # 마지막 시도
        logger.warning("기본 모델로 시도")
        return genai.GenerativeModel('gemini-1.5-flash')
        
    async def generate(self, day_config: dict, language: str) -> dict:
        """
        스크립트 및 메타데이터 생성
        """
        try:
            # 1. 스크립트 생성
            script = await self._generate_script(day_config, language)
            
            # 2. 메타데이터 생성
            metadata = await self._generate_metadata(script, language)
            
            # 3. 사용된 주제 기록 (중복 방지)
            if self.config['content']['prevent_duplicates']:
                save_used_topic(day_config['topic'], script[:50])
            
            return {
                'script': script,
                'title': metadata['title'],
                'description': metadata['description'],
                'tags': metadata['tags']
            }
            
        except Exception as e:
            logger.error(f"콘텐츠 생성 실패: {str(e)}")
            raise
    
    async def _generate_script(self, day_config: dict, language: str) -> str:
        """스크립트 생성"""
        lang_key = 'korean' if language == 'korean' else 'english'
        day = day_config['day']
        
        # 시스템 프롬프트
        system_prompt = self.prompts['system_prompt'][lang_key]
        
        # 요일별 프롬프트
        topic_prompt = self.prompts['topic_prompts'][day][lang_key]
        
        # 중복 방지 지시
        used_list = self._get_recent_topics(day)
        avoid_prompt = ""
        if used_list:
            avoid_prompt = f"\n\n⚠️ 다음 주제는 최근에 사용했으니 피해줘:\n{', '.join(used_list)}"
        
        # 전체 프롬프트 조합
        full_prompt = f"""
{system_prompt}

---

{topic_prompt}

{avoid_prompt}

---

위 지침에 따라 스크립트만 작성해줘. 다른 설명 없이 스크립트 텍스트만 응답해.
"""
        
        # API 호출
        response = self.model.generate_content(full_prompt)
        script = response.text.strip()
        
        # 길이 검증
        if language == 'korean' and len(script) > 250:
            script = script[:250]
        elif language == 'english' and len(script.split()) > 100:
            script = ' '.join(script.split()[:100])
        
        return script
    
    async def _generate_metadata(self, script: str, language: str) -> dict:
        """제목, 설명, 태그 생성"""
        lang_key = 'korean' if language == 'korean' else 'english'
        
        prompt = f"""
다음 스크립트에 대한 유튜브 쇼츠 메타데이터를 생성해줘.

스크립트:
{script}

---

{self.prompts['metadata_prompt'][lang_key]}

JSON 형식으로만 응답해. 다른 텍스트 없이.
"""
        
        response = self.model.generate_content(prompt)
        
        # JSON 파싱
        try:
            text = response.text.strip()
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            metadata = json.loads(text)
            
            return {
                'title': metadata.get('title', '심리학 이야기'),
                'description': metadata.get('description', ''),
                'tags': metadata.get('tags', ['심리학', 'psychology', 'shorts'])
            }
        except json.JSONDecodeError:
            logger.warning("메타데이터 JSON 파싱 실패, 기본값 사용")
            return {
                'title': '오늘의 심리학' if language == 'korean' else 'Psychology Today',
                'description': script[:100],
                'tags': ['심리학', 'psychology', 'shorts', 'facts', '심리']
            }
    
    def _get_recent_topics(self, day: str) -> list:
        """최근 사용된 주제 목록 반환"""
        check_days = self.config['content'].get('duplicate_check_days', 30)
        recent = []
        
        for topic_data in self.used_topics:
            if topic_data.get('day') == day:
                recent.append(topic_data.get('summary', ''))
        
        return recent[-10:]
