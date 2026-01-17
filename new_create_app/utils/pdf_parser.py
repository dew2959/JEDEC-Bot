# PDF parsing의 목적 : Section 단위 의미 블록 추출 
# PDF parser 선택 : PyMuPDF (fitz) 
# 선택한 이유 : 빠르고, 페이지 번호 정확하고, JEDEC PDF와 궁합이 좋다. 
'''
핵심 책임 
1) PDF 열기
2) 페이지별 텍스트 추출 
3) Section 헤더 탐지
4) Section별 텍스트 누적
5) 결과 JSON 반환 
'''

import fitz
import re 
from typing import List, Dict 

SECTION_PATTERN = re.compile(r"^(\d+(\.\d+)+)\s+(.*)")
# 정규표현식 -> 예) "7.3.2 On-Die Termination"

# JEDEC PDF를 Section 단위로 파싱하는 함수 
def parse_jedec_pdf(pdf_path: str, standard: str, version: str) -> List[Dict]:    
     
    doc = fitz.open(pdf_path)

    sections = []
    current_section = None 

    for page_num, page in enumerate(doc, start=1):   #페이지 번호 유지. 출처 신뢰성을 위해서.  
        text = page.get_text("text")
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue 

            match = SECTION_PATTERN.match(line)
            if match: 
                #새로운 Section 시작 
                if current_section:
                    sections.append(current_section)

                section_number = match.group(1)
                title = match.group(3)

                current_section = {
                    "standard" : standard,
                    "version" : version,
                    "section" : section_number,
                    "title" : title,
                    "page" : page_num,
                    "text" : ""
                }
            else:
                if current_section:
                    current_section['text'] += line + " " # 줄 단위가 아니라 의미 블록으로 text 누적

    if current_section:
        sections.append(current_section)

    return sections 

