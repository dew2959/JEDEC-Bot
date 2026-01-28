from typing import List, Dict
import re 
import tiktoken

# =========================
# 설정값 (중요)
# =========================
MIN_TOKENS = 50
TARGET_TOKENS = 250
MAX_TOKENS = 450
OVERLAP_TOKENS = 40

# ========================================================================================================
# Token counter (LLM 기준)
# OpenAI 계열 LLM이 쓰는 토크나이저 규칙을 로드하는 코드. GPT-4 / GPT-4o / GPT-3.5-turbo 계열이 쓰는 토큰 규칙을 가져오라는 뜻
# ========================================================================================================
encoding = tiktoken.to("cl100k_base")
def count_tokens(text:str) -> int:
   return len(encoding.encode(text))


# =========================
# Token 기준 강제 분할. sentence 하나가 MAX_TOKENS 초과 시 (지금은 안 쓰는 함수)
# =========================
def force_split_by_tokens(text: str, max_tokens: int) -> List[str]:
    words = text.split()
    chunks = []

    start = 0
    while start < len(words):
        end = start + max_tokens
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words).strip()

        if chunk_text:
            chunks.append(chunk_text)

        # overlap 적용
        start = end - OVERLAP_TOKENS
        if start < 0:
            start = 0

    return chunks


# =========================
# 문장 단위 분할
# =========================
def split_by_sentences(text: str) -> List[str]:
    # JEDEC 문서에 맞춘 보수적 분할
    sentences = re.split(r'(?<=[.;])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


# =========================
# 메인 Chunk 함수
# =========================
def chunk_section(section, max_tokens: int = MAX_TOKENS):
    text = section.text
    sentences = split_by_sentences(text)

    chunks = []
    current_text = ""
    current_tokens = 0
    chunk_idx = 1

    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue

        sent_tokens = count_tokens(sent)

        # 새 chunk 필요
        if current_tokens + sent_tokens > max_tokens:
            if current_text.strip():
                chunks.append({
                    "chunk_id" : f"{section.id}_c{chunk_idx}",
                    "standard" : section.standard,
                    "version" : section.version,
                    "section" : section.section,
                    "title" : section.title,
                    "page_start" : section.page_start,
                    "page_end" : section.page_end,
                    "text" : current_text.strip(), 
                    "token_count" : current_tokens
                })
                chunk_idx += 1
            
            current_text = sent + " "
            current_tokens = sent_tokens

        else:
            current_text += sent + " "
            current_tokens += sent_tokens

    # 마지막 chunk
    if current_text.strip():
        chunks.append({
            "chunk_id" : f"{section.id}_c{chunk_idx}",
            "standard" : section.standard,
            "version" : section.version,
            "section" : section.section,
            "title" : section.title,
            "page_start" : section.page_start,
            "page_end" : section.page_end,
            "text" : current_text.strip(),
            "token_count" : current_tokens,
        })

    return chunks


