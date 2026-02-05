# 💾 JEDEC Specs Navigator: 반도체 표준 문서 분석 AI 어시스턴트

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.31-FF4B4B?logo=streamlit&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-0.1-1C3C3C?logo=langchain&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o--mini-412991?logo=openai&logoColor=white)
![ChromaDB](https://img.shields.io/badge/VectorDB-Chroma-orange)

> **"수백 페이지의 반도체 표준 문서(JEDEC), Ctrl+F보다 더 똑똑하게 검색할 수는 없을까?"**

이 프로젝트는 반도체 엔지니어들이 겪는 정보 검색의 비효율성을 해결하기 위해 개발된 **RAG(Retrieval-Augmented Generation) 기반의 AI 챗봇 솔루션**입니다. 단순한 텍스트 매칭이 아닌, 문맥을 이해하는 시맨틱 검색을 통해 복잡한 타이밍 파라미터와 제약 조건을 정확하게 찾아냅니다.

---

## 📌 프로젝트 소개 (Project Overview)

반도체 표준(예: DDR5, HBM3) 문서는 방대하고 표(Table) 위주의 데이터가 많아, 기존 검색 방식으로는 문맥에 맞는 정답을 찾기 어렵습니다. 본 프로젝트는 **Local RAG Pipeline**을 구축하여 사용자가 자연어로 질문하면 관련 근거(Source)와 함께 정확한 답변을 제공합니다.

### 🎯 핵심 기능 (Key Features)
* **계층형 문서 라이브러리:** `DRAM`, `Storage`, `Package` 등 카테고리별로 문서를 자동 분류 및 관리.
* **영구적 지식 베이스 (Persistent Knowledge Base):** 한 번 학습된 문서는 벡터 DB(Chroma)에 저장되어 재학습 없이 즉시 검색 가능.
* **표(Table) 데이터 처리 강화:** `pdfplumber`를 도입하여 JEDEC 문서의 핵심인 타이밍 스펙(Table)의 레이아웃 정보 보존.
* **문서 메타데이터 자동 생성:** 문서 학습 시 AI가 자동으로 **요약(Summary)**과 **추천 질문(Key Questions)**을 추출하여 사용자에게 가이드 제공.

---

## 🏗️ 시스템 아키텍처 (Architecture)

단순한 1회성 스크립트가 아닌, **확장 가능한 모듈형 구조**로 설계되었습니다.

<img width="2076" height="1086" alt="image" src="https://github.com/user-attachments/assets/a634048c-b792-40cd-b668-11a4ac4c1cc8" />

## 📁 디렉토리 구조 (Directory Structure)

```bash
.
├── app2/
│   ├── chain/          # RAG 로직 (LangChain)
│   └── utils/          # PDF 파서, Vector Store 관리자
├── chroma_dbs/         # 학습된 벡터 데이터베이스 (Persistent Storage)
├── data/               # 원본 PDF 파일 저장소
│   └── pdfs/           # DRAM, Storage 등 하위 폴더 자동 인식
├── app.py              # Streamlit 메인 애플리케이션
├── bulk_ingest.py      # 대량 문서 일괄 학습 스크립트
└── requirements.txt    # 의존성 패키지
```

## 🛠️ 기술 스택 (Tech Stack)

| 구분 | 기술 | 선정 이유 |
| :--- | :--- | :--- |
| **LLM** | **GPT-5-nano** | 속도가 빠르고 비용 효율적 |
| **Embedding** | **text-embedding-3-large** | 한국어/영어 기술 문서 검색에 최적화된 성능과 낮은 비용. |
| **Framework** | **LangChain** | 모듈화된 RAG 파이프라인(Loader -> Splitter -> VectorStore -> Retriever) 구축 용이. |
| **Vector DB** | **ChromaDB** | 별도의 서버 구축 없이 로컬 파일 시스템 기반으로 관리 가능하며, 메타데이터 필터링 지원. |
| **Parser** | **pdfplumber** | `extract_text(layout=True)` 옵션을 통해 PDF 내 표(Table)의 물리적 레이아웃을 보존, 데이터 왜곡 최소화. |
| **UI** | **Streamlit** | Python만으로 빠른 풀스택 프로토타이핑 가능, Chat Interface 및 Session State 관리 용이. |
