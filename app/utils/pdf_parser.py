import os 
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_and_split_pdf(file_path):
    """
    PDF 문서를 load하고, 적절한 크기의 chunk로 분할하는 함수 
    
    Args: 
        file_path (str) : PDF 파일의 경로 
    Returns:
        list: 분할된 Document 객체 리스트 
    """

    # 1. 문서 로드 
    # PyPDFLoader는 PDF의 각 페이지를 하나의 Document 객체로 가져온다. 
    print(f"Loading PDF from: {file_path}...")
    loader = PyPDFLoader(file_path)
    raw_documents = loader.load()
    print(f"Loaded {len(raw_documents)} pages.")

    # 2. 텍스트 분할 (Split)
    # RecursiveCharacterTextSplitter는 문단→줄바꿈→문장 순서로 자르려고 시도하여 문맥 끊김을 방지. 
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1000,              # 한 조각의 최대 글자 수 (토큰 수 아님)
        chunk_overlap = 200,            # 조각 간 중복되는 글자 수 (문맥 유지용)
        length_function = len,          # 길이 측정 함수 
        is_separator_regex= False,
    )

    chunks = text_splitter.split_documents(raw_documents)
    print(f"Split into {len(chunks)} chunks.")

    return chunks


# 테스트 실행 코드 
if __name__ == "__main__":
    TEXT_FILE_PATH = r"C:\Users\user\Documents\jedec_chatbot_proj\data\pdfs\DRAM\JESD79-5_DDR5.pdf"

    if not os.path.exists(TEXT_FILE_PATH):
        print(f"Error : 파일을 찾을 수 없습니다. 경로를 확인해주세요")
    else:
        docs = load_and_split_pdf(TEXT_FILE_PATH)

        print("\n---[Chunk 1 Sample] ---")
        print(docs[0].page_content)
        print("\n------[Metadata]------")
        print(docs[0].metadata)