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


# 정규표현식 -> 예) "7.3.2 On-Die Termination"
SECTION_PATTERN = re.compile(r"^(\d+(\.\d+)+)\s+(.+)")


# 목차 라인인지 확인하는 간단한 헬퍼 함수
def is_toc_line(line: str) -> bool:
    if line.count('.') > 10:
        return True
    # 끝에 페이지 번호만 있는 경우 
    if re.search(r"\.{3,}\s*\d+$", line):
        return True
    return False

# 섹션 분리 함수 
def trim_text_by_next_section(text, current_section):
    """
    current_section: "3.1"
    다음 섹션 예: 3.2, 3.3, 3.10 ...
    """
    base = current_section.split('.')[0]

    # 공백 또는 문장 중간에 나오는 "3.x Title" 패턴 탐지
    pattern = rf"\b{base}\.(\d+)\s+[A-Z]"

    matches = list(re.finditer(pattern, text))

    if not matches:
        return text.strip()
    
    # 첫 번째 match가 자기 자신일 수 있으므로 두 번째부터
    for m in matches:
        sec = f"{base}.{m.group(1)}"
        if sec != current_section:
            return text[:m.start()].strip()

    return text.strip()


# JEDEC PDF를 Section 단위로 파싱하는 함수 
def parse_jedec_pdf(pdf_path: str, standard: str, version: str) -> List[Dict]:    
     
    doc = fitz.open(pdf_path)

    sections = []
    current_section = None 

    for page_num, page in enumerate(doc, start=1):   #페이지 번호 유지. 출처 신뢰성을 위해서. 
        text = page.get_text("text") 
        text = re.sub(
            r"Table\s+\d+\s+—.*?(?=\n[A-Z0-9])",
            "",
            text,
            flags=re.DOTALL
        )
        lines = text.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue 

            match = SECTION_PATTERN.match(line)
            if match and not is_toc_line(line): 
                #새로운 Section 시작 
                if current_section:
                    current_section['text'] = trim_text_by_next_section(current_section['text'], current_section['section'])

                    if len(current_section["text"]) >= 200:  ## section 길이 필터
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
        current_section['text'] = trim_text_by_next_section(current_section['text'], current_section['section'])
        if len(current_section["text"]) >= 200:
            sections.append(current_section)

    return sections 

