import json
import os
import re


def _filter_image_lines(lines):
    """Remove markdown image lines."""
    return [
        line for line in lines
        if not line.strip().startswith("![Image]")
        and not line.strip().startswith("![]")
    ]


def _split_sections(lines):
    """Split lines into (heading, content) sections on markdown headings."""
    sections = []
    current_heading = None
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if re.match(r"^#+\s", stripped):
            if current_heading and current_lines:
                sections.append((current_heading, "\n".join(current_lines)))
            current_heading = stripped
            current_lines = []
        elif stripped and current_heading:
            current_lines.append(line)

    if current_heading and current_lines:
        sections.append((current_heading, "\n".join(current_lines)))

    return sections


def _merge_small_sections(sections, chunk_min_size):
    """Merge consecutive sections until each chunk meets the minimum size."""
    if chunk_min_size is None:
        return sections

    merged = []
    i = 0
    while i < len(sections):
        heading, content = sections[i]
        j = i + 1
        while j < len(sections) and len(content) < chunk_min_size:
            next_heading, next_content = sections[j]
            content += "\n\n" + next_heading + "\n" + next_content
            j += 1
        merged.append((heading, content))
        i = j

    return merged


def chunk_markdown(text, chunk_min_size=2000):
    """Split markdown text into chunked sections, returning [{id, context}]."""
    lines = text.splitlines()
    lines = _filter_image_lines(lines)
    sections = _split_sections(lines)
    sections = _merge_small_sections(sections, chunk_min_size)

    results = []
    for heading, content in sections:
        context = heading + "\n" + content
        results.append({"id": hash(context), "context": context})

    return results


def convert_pdf(input_path, output_path, chunk_min_size=2000):
    """Convert a PDF to chunked JSON via docling."""
    from docling.document_converter import DocumentConverter

    print(f"Processing {input_path}")

    if os.path.exists(output_path):
        print("  Skipping, output already exists")
        return

    converter = DocumentConverter()
    result = converter.convert(input_path)
    print("  Conversion done, chunking markdown")
    text = result.document.export_to_markdown()

    chunks = chunk_markdown(text, chunk_min_size)
    print(f"  {len(chunks)} chunks")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)


def convert_markdown(input_path, output_path, chunk_min_size=2000):
    """Chunk an existing markdown file into JSON."""
    print(f"Processing {input_path}")

    if os.path.exists(output_path):
        print("  Skipping, output already exists")
        return

    with open(input_path, encoding="utf-8") as f:
        text = f.read()

    chunks = chunk_markdown(text, chunk_min_size)
    print(f"  {len(chunks)} chunks")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)


def convert_file(input_path, output_path=None, chunk_min_size=2000):
    """Convert a PDF or markdown file to chunked JSON, choosing the right path."""
    ext = os.path.splitext(input_path)[1].lower()
    if output_path is None:
        output_path = os.path.splitext(input_path)[0] + ".json"

    if ext == ".pdf":
        convert_pdf(input_path, output_path, chunk_min_size)
    elif ext in (".md", ".markdown"):
        convert_markdown(input_path, output_path, chunk_min_size)
    else:
        raise ValueError(f"Unsupported file type: {ext} (expected .pdf or .md)")


if __name__ == "__main__":
    data_dir = "./data"
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    for fn in os.listdir(data_dir):
        ext = os.path.splitext(fn)[1].lower()
        if ext in (".pdf", ".md", ".markdown"):
            convert_file(os.path.join(data_dir, fn))
