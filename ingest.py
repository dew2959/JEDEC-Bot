import os 
from app2.utils.pdf_parser import load_and_split_pdf
from app2.utils.vector_store import create_vector_db
from dotenv import load_dotenv

# .env 파일에서 API KEY 로드  
load_dotenv()

def main():
    #1. PDF 파일 경로 설정 
    pdf_path = r"C:\Users\user\Documents\jedec_chatbot_proj\data\pdfs\DRAM\JESD79-5_DDR5.pdf"

    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return 
    
    #2. PDF parsing & chunking 
    print(">>> Step 1: Parsing PDF...")
    chunks = load_and_split_pdf(pdf_path)

    #3. 벡터 DB 생성 및 저장 
    print(">>> Step2: Creating Vector DB...")
    create_vector_db(chunks)
    print(">>> Ingestion Complete!")

if __name__ =="__main__":
    main()