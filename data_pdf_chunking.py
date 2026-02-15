import os
import json
import re

from docling.document_converter import DocumentConverter


def convert_pdf(input_path: str, output_path: str, chunk_min_size: int | None = 2000):
    print(f"Processing {input_path}")

    if os.path.exists(output_path):
        print(f"  Skipping because output already exists")
        return

    converter = DocumentConverter()
    result = converter.convert(input_path)
    print("  conversion done, dumping to markdown")
    txt = result.document.export_to_markdown()

    lines = txt.splitlines()

    # Filter out lines that start with [Image]
    lines = [line for line in lines if not line.strip().startswith('![Image]')]
    lines = [line for line in lines if not line.strip().startswith('![]')]



    # Initialize variables to track sections
    sections = []
    current_section = []
    current_heading = None

    # Process lines to group them by markdown sections
    for line in lines:
        stripped_line = line.strip()
        
        # Check if the line is a heading (starts with one or more # followed by whitespace)
        if re.match(r'^#+\s', stripped_line):
            # If we have content in the current section, save it
            if current_section and current_heading:
                section_content = '\n'.join(current_section)
                sections.append({
                    'heading': current_heading,
                    'content': section_content
                })
            
            # Start a new section
            current_heading = stripped_line
            current_section = []
        else:
            # Add the line to the current section if it's not empty
            if stripped_line and current_heading:  # only add lines that are part of a section (not before any section)
                current_section.append(line)

    # Add the last section if it exists
    if current_section and current_heading:
        section_content = '\n'.join(current_section)
        sections.append({
            'heading': current_heading,
            'content': section_content
        })

    # Combine sections until each combined section is at least 2000 characters
    combined_sections = []
    i = 0
    while i < len(sections):
        current_combined = {
            'heading': sections[i]['heading'],
            'content': sections[i]['content']
        }
        
        # Keep combining with next sections until we reach minimum length or run out of sections
        j = i + 1
        if chunk_min_size is not None:
            while j < len(sections) and len(current_combined['content']) < chunk_min_size:
                current_combined['content'] += '\n\n' + sections[j]['heading'] + '\n' + sections[j]['content']
                j += 1
        
        combined_sections.append(current_combined)
        i = j  # Move to the next unprocessed section

    # Print some statistics about the sections
    print(f"Found {len(sections)} original sections in the markdown file")
    print(f"Combined into {len(combined_sections)} sections after merging small ones")

    # Create a single string for each section with the heading at the top
    formatted_sections = []
    for section in combined_sections:
        # Combine the heading and content with newlines
        section_text = section['heading'] + '\n' + section['content']
        formatted_sections.append(section_text)

    # Print some statistics about the formatted sections
    print(f"Created {len(formatted_sections)} formatted sections")

    formatted_contexts = []
    for section in formatted_sections:
        sec_id = hash(section)
        formatted_contexts.append({'id': sec_id, 'context': section})

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(formatted_contexts, f, indent=2)



if __name__ == "__main__":
    # Directory containing PDF files
    pdf_dir = './data'
    # Ensure the directory exists
    if not os.path.isdir(pdf_dir):
        raise FileNotFoundError(f"PDF directory not found: {pdf_dir}")

    pdf_files = [fn for fn in os.listdir(pdf_dir) if fn.lower().endswith('.pdf')]

    for pdf_file in pdf_files:
        input_path = os.path.join(pdf_dir, pdf_file)
        output_path = input_path.replace('.pdf', '.json')
        convert_pdf(input_path, output_path)

    


    