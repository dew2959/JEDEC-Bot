from new_create_app.utils.pdf_parser import parse_jedec_pdf
from new_create_app.utils.schemas import JedecDocument, JedecSection
from new_create_app.utils.save_json import save_json

def main():
    raw_sections = parse_jedec_pdf(
        pdf_path='data/pdfs/DRAM/JESD79-4_DDR4.pdf',
        standard='JESD79-4_DDR4',
        version='DDR4'
    )

    sections = []

    for s in raw_sections:
        section = JedecSection(
            id=f"{s['standard']}_{s['section']}",
            standard=s['standard'],
            version=s['version'],
            section=s['section'],
            title=s['title'],
            page_start=s['page'],
            page_end=s['page'],
            text=s['text']
        )
        sections.append(section)

    doc = JedecDocument(
        standard='JESD79-4_DDR4',
        version='DDR4',
        source='JESD79-4_DDR4.pdf',
        parser='custom_pdf_parser_v1',
        created_at='2024-06-01T12:00:00Z',
        sections=sections
    )

    save_json(doc.to_dict(), 'data/json/JESD79-4_DDR4_sections.json')

    print(f"✅ saved {len(sections)} sections")
    print("sections count:", len(sections))
    print(sections[0])

    from new_create_app.utils.chunker import chunk_section

    all_chunks = []

    for section in doc.sections:
        chunks = chunk_section(section)
        all_chunks.extend(chunks)

    print("total chunks:", len(all_chunks))
    print(all_chunks[0])

    tokens = [c["token_count"] for c in all_chunks]

    print("min:", min(tokens))
    print("max:", max(tokens))
    print("avg:", sum(tokens) / len(tokens))


if __name__ == "__main__":
    main()