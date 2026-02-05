import pdfplumber
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def load_and_split_pdf(file_path):
    """
    pdfplumber를 사용하여 텍스트 레이아웃을 보존하며 파싱합니다.
    표 데이터 인식률이 PyPDFLoader보다 훨씬 좋습니다.
    """
    print(f"Loading PDF with pdfplumber: {file_path}...")
    
    docs = []
    
    # pdfplumber로 파일 열기
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # extract_text(layout=True) 옵션이 핵심입니다.
            # 텍스트의 물리적 위치를 공백으로 유지하여 '표' 모양을 흉내냅니다.
            text = page.extract_text(layout=True) 
            
            if text:
                docs.append(Document(
                    page_content=text,
                    metadata={"source": file_path, "page": i + 1}
                ))
    
    print(f"Loaded {len(docs)} pages.")

    # Chunking (문맥 유지를 위해 오버랩을 조금 더 늘림)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,    # 표가 포함되면 글자수가 많아지므로 약간 늘림
        chunk_overlap=300, 
        length_function=len,
        is_separator_regex=False,
    )

    chunks = text_splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks.")
    
    return chunks