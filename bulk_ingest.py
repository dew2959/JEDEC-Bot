import os
import time
from app.utils.pdf_parser2 import load_and_split_pdf
from app.utils.vector_store import create_vector_db
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRELOAD_DIR = os.path.join(BASE_DIR, "data", "pdfs")
DB_ROOT = os.path.join(BASE_DIR, "chroma_dbs")

def ingest_all():
    print(f"📂 데이터 폴더 스캔 중: {PRELOAD_DIR}")
    
    tasks = []
    
    # 모든 하위 폴더 스캔
    for dirpath, dirnames, filenames in os.walk(PRELOAD_DIR):
        category = os.path.relpath(dirpath, PRELOAD_DIR)
        
        for filename in filenames:
            if filename.lower().endswith(".pdf"):
                pdf_path = os.path.join(dirpath, filename)
                
                # DB 경로 생성 규칙 (app.py와 동일하게)
                if category == ".":
                    db_name = f"Root_{os.path.splitext(filename)[0]}_db"
                else:
                    clean_cat = category.replace(os.sep, "_")
                    db_name = f"{clean_cat}_{os.path.splitext(filename)[0]}_db"
                
                db_path = os.path.join(DB_ROOT, db_name)
                tasks.append((pdf_path, db_path, filename))

    print(f"총 {len(tasks)}개의 PDF 파일을 찾았습니다.\n")

    # 순차적으로 학습 진행
    for i, (pdf_path, db_path, filename) in enumerate(tasks):
        print(f"[{i+1}/{len(tasks)}] 처리 중: {filename} ...")
        
        if os.path.exists(db_path):
            print(f"  👉 이미 학습됨 (건너뜀)")
            continue
            
        try:
            # 파싱 및 DB 생성
            chunks = load_and_split_pdf(pdf_path)
            create_vector_db(chunks, db_path)
            print(f"  ✅ 학습 완료!")
        except Exception as e:
            print(f"  ❌ 실패: {e}")

    print("\n🎉 모든 작업이 완료되었습니다! 이제 앱을 실행하세요.")

if __name__ == "__main__":
    ingest_all()