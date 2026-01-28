from typing import List
import tiktoken

encoding = tiktoken.get_encoding("cl100k_base")

def count_tokens(text:str) -> int:
    return len(encoding.encode(text))

def chunk_section(section, target_tokens: int = 350, max_tokens: int = 450):
    text = section.text
    sentences = text.split(". ")

    chunks = []
    current = ""
    current_tokens = 0
    chunk_idx = 1

    for sent in sentences:
        sent = sent.strip() + ". "
        sent_tokens = count_tokens(sent)

        if current_tokens + sent_tokens > max_tokens:
            chunks.append({
                "chunk_id" : f"{section.id}_c{chunk_idx}",
                "standard" : section.standard,
                "version" : section.version,
                "section" : section.section,
                "title" : section.title,
                "page_start" : section.page_start,
                "page_end" : section.page_end,
                "text" : current.strip(), 
                "token_count" : current_tokens
            })

            chunk_idx += 1
            current = sent
            current_tokens = sent_tokens

        else:
            current += sent
            current_tokens = sent_tokens

    if current.strip():
        chunks.append({
            "chunk_id" : f"{section.id}_c{chunk_idx}",
            "standard" : section.standard,
            "version" : section.version,
            "section" : section.section,
            "title" : section.title,
            "page_start" : section.page_start,
            "page_end" : section.page_end,
            "text" : current.strip(),
            "token_count" : current_tokens,
        })

    return chunks


