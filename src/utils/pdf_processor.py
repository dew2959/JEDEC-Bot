"""
PDF Processing Module for JEDEC Insight
Handles extraction of text and tables from JEDEC PDF documents
using PyMuPDF and Unstructured libraries.
"""

import os
import logging
from typing import List, Dict, Any, Tuple
from pathlib import Path
import fitz  # PyMuPDF
from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Table, Text
import pandas as pd
import markdown

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Processes JEDEC PDF documents to extract text and tables."""
    
    def __init__(self, pdf_dir: str, output_dir: str):
        """
        Initialize PDF processor.
        
        Args:
            pdf_dir: Directory containing PDF files
            output_dir: Directory to save processed content
        """
        self.pdf_dir = Path(pdf_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_with_pymupdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract content using PyMuPDF for basic text and table detection.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing extracted content
        """
        try:
            doc = fitz.open(pdf_path)
            content = {
                "text_pages": [],
                "tables": [],
                "metadata": doc.metadata
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text
                text = page.get_text()
                if text.strip():
                    content["text_pages"].append({
                        "page": page_num + 1,
                        "text": text
                    })
                
                # Extract tables
                tables = page.find_tables()
                for table_idx, table in enumerate(tables):
                    try:
                        df = table.to_pandas()
                        table_content = {
                            "page": page_num + 1,
                            "table_id": f"table_page_{page_num + 1}_{table_idx}",
                            "data": df,
                            "markdown": self._dataframe_to_markdown(df)
                        }
                        content["tables"].append(table_content)
                    except Exception as e:
                        logger.warning(f"Failed to extract table on page {page_num + 1}: {e}")
            
            doc.close()
            return content
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path} with PyMuPDF: {e}")
            return {"text_pages": [], "tables": [], "metadata": {}}
    
    def extract_with_unstructured(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Extract content using Unstructured for better table detection.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary containing extracted content
        """
        try:
            elements = partition_pdf(
                filename=str(pdf_path),
                infer_table_structure=True,
                strategy="hi_res",
                chunking_strategy="by_title"
            )
            
            content = {
                "text_elements": [],
                "tables": [],
                "metadata": {}
            }
            
            for element in elements:
                if isinstance(element, Table):
                    # Convert table to DataFrame and then to markdown
                    try:
                        df = pd.DataFrame(element.rows)
                        table_content = {
                            "element_id": str(element.id) if hasattr(element, 'id') else f"table_{len(content['tables'])}",
                            "data": df,
                            "markdown": self._dataframe_to_markdown(df),
                            "page": element.metadata.page_number if hasattr(element, 'metadata') else None
                        }
                        content["tables"].append(table_content)
                    except Exception as e:
                        logger.warning(f"Failed to process table element: {e}")
                        
                elif isinstance(element, Text):
                    text_content = {
                        "element_id": str(element.id) if hasattr(element, 'id') else f"text_{len(content['text_elements'])}",
                        "text": str(element),
                        "page": element.metadata.page_number if hasattr(element, 'metadata') else None
                    }
                    content["text_elements"].append(text_content)
            
            return content
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path} with Unstructured: {e}")
            return {"text_elements": [], "tables": [], "metadata": {}}
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to Markdown table format.
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Markdown formatted table string
        """
        try:
            # Clean the DataFrame
            df = df.fillna("")  # Replace NaN with empty string
            df = df.astype(str)  # Convert all to string
            
            # Convert to markdown
            markdown_table = df.to_markdown(index=False, tablefmt="pipe")
            return markdown_table
        except Exception as e:
            logger.error(f"Error converting DataFrame to markdown: {e}")
            return "| Error converting table |\n|---|"
    
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Process a single PDF file using both methods.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Combined extracted content
        """
        logger.info(f"Processing PDF: {pdf_path}")
        
        # Extract with both methods
        pymupdf_content = self.extract_with_pymupdf(pdf_path)
        unstructured_content = self.extract_with_unstructured(pdf_path)
        
        # Combine results
        combined_content = {
            "filename": pdf_path.name,
            "pymupdf": pymupdf_content,
            "unstructured": unstructured_content,
            "processed_at": pd.Timestamp.now().isoformat()
        }
        
        return combined_content
    
    def save_processed_content(self, content: Dict[str, Any], pdf_path: Path) -> str:
        """
        Save processed content to files.
        
        Args:
            content: Processed content dictionary
            pdf_path: Original PDF path
            
        Returns:
            Path to saved markdown file
        """
        base_name = pdf_path.stem
        output_file = self.output_dir / f"{base_name}_processed.md"
        
        # Create markdown content
        markdown_content = []
        markdown_content.append(f"# {content['filename']}\n")
        markdown_content.append(f"Processed at: {content['processed_at']}\n")
        
        # Add metadata
        if content['pymupdf']['metadata']:
            markdown_content.append("## Document Metadata\n")
            for key, value in content['pymupdf']['metadata'].items():
                markdown_content.append(f"- **{key}**: {value}")
            markdown_content.append("")
        
        # Add text content
        markdown_content.append("## Text Content\n")
        
        # Use unstructured text if available, otherwise PyMuPDF
        if content['unstructured']['text_elements']:
            for element in content['unstructured']['text_elements']:
                markdown_content.append(f"### Page {element.get('page', 'Unknown')}\n")
                markdown_content.append(element['text'])
                markdown_content.append("")
        else:
            for page in content['pymupdf']['text_pages']:
                markdown_content.append(f"### Page {page['page']}\n")
                markdown_content.append(page['text'])
                markdown_content.append("")
        
        # Add tables
        all_tables = content['unstructured']['tables'] + content['pymupdf']['tables']
        if all_tables:
            markdown_content.append("## Tables\n")
            for table in all_tables:
                table_id = table.get('element_id', table.get('table_id', 'unknown'))
                page = table.get('page', 'Unknown')
                markdown_content.append(f"### Table {table_id} (Page {page})\n")
                markdown_content.append(table['markdown'])
                markdown_content.append("")
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(markdown_content))
        
        logger.info(f"Saved processed content to: {output_file}")
        return str(output_file)
    
    def process_all_pdfs(self) -> List[str]:
        """
        Process all PDF files in the input directory.
        
        Returns:
            List of paths to processed markdown files
        """
        processed_files = []
        
        for pdf_file in self.pdf_dir.glob("*.pdf"):
            if pdf_file.is_file():
                try:
                    content = self.process_pdf(pdf_file)
                    output_path = self.save_processed_content(content, pdf_file)
                    processed_files.append(output_path)
                except Exception as e:
                    logger.error(f"Failed to process {pdf_file}: {e}")
        
        return processed_files


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    processor = PDFProcessor(
        pdf_dir="./data/pdfs",
        output_dir="./data/processed"
    )
    
    processed = processor.process_all_pdfs()
    print(f"Processed {len(processed)} PDF files:")
    for file in processed:
        print(f"  - {file}")
