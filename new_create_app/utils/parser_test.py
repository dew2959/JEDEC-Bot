from new_create_app.utils.pdf_parser import parse_jedec_pdf

def main():
    sections = parse_jedec_pdf(
        pdf_path='data/pdfs/DRAM/JESD79-4_DDR4.pdf',
        standard='JESD79-4_DDR4',
        version='DDR4'
    )

    print("sections count:", len(sections))
    print(sections[0])

    valid_sections = [s for s in sections if len(s["text"].strip()) > 100]

    print("valid sections:", len(valid_sections))
    print(valid_sections[0])

if __name__ == "__main__":
    main()