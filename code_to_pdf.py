import sys
from pathlib import Path
import config
import re

MAX_HEIGHT_IN = 8.5
MAX_WIDTH_IN = 7
PT_PER_INCH = 72
BOX_WIDTH_EM = 0.6 # listing package default
LINE_SPACE_SCALE = 2 # double space

def unindent(snippet: list[str]) -> None:
    """
    Remove any consistent indentation from all lines
    """
    all_indented = True
    while all_indented:
        for line in snippet:
            all_indented = all_indented and len(line) > 0 and line[0] == ' '
        
        if all_indented:
            for i in range(len(snippet)):
                snippet[i] = snippet[i][1:]


def find_snippet(fname: str) -> list[str]:
    """
    Finds the code snippet defined by config.regex.
    """
    with open(fname, "r", encoding="utf-8") as f:
        content = f.read()

    match = re.search(config.regex, content, re.DOTALL | re.MULTILINE)
    snippet = []
    if match:
        block_start = match.span()[0]
        # This assumes C++, would need to do something different for Python
        first_brace = content.find("{", block_start)
        brace_count = 1
        block_end = first_brace + 1
        while brace_count > 0 and block_end < len(content):
            if content[block_end] == "{":
                brace_count += 1
            elif content[block_end] == "}":
                brace_count -= 1
            block_end += 1
        
        snippet = content[block_start:block_end].strip().splitlines()
        unindent(snippet)
    else:
        print(f"Warning: code snippet not found in {fname}")
    
    return snippet

def calc_fontsize(code: list[str]) -> float:
    """
    Calculate the font size needed to fit the code on one page.
    """
    h_min = MAX_HEIGHT_IN * PT_PER_INCH / (len(code) * LINE_SPACE_SCALE)
    longest_line = max([len(line) for line in code])
    print(f"Longest line: {longest_line} characters")
    w_min = MAX_WIDTH_IN * PT_PER_INCH / (longest_line * BOX_WIDTH_EM)
    return min(h_min, w_min)

def write_tex(fname: str, code: list[str], fontsize: float) -> None: 
    """
    Modifies the template file and writes to output directory.
    """
    with open(config.template, "r") as f:
        text = f.read()
    
    # Assumes the files are in folders named for each student
    student_name = Path(fname).parent.name
    # replace placeholders
    text = text.replace("REPLACEWITHTITLE", config.title_prefix + ": " + student_name)
    text = text.replace("REPLACEWITHCODE", "\n".join(code))
    text = text.replace("FONTSIZE", f"{fontsize:.1f}")
    text = text.replace("SKIPSIZE", f"{fontsize * LINE_SPACE_SCALE:.1f}")

    with open(config.output_dir / (student_name + ".tex"), "w") as f:
        f.write(text)


def main(files: list[str]) -> None:
    """
    Loop over the given files, find the matching regex in the code, output to pdf.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)
    
    for fname in files:
        code = find_snippet(fname)
        if code:
            fontsize = calc_fontsize(code)
            write_tex(fname, code, fontsize)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python code_to_pdf.py <input_files>")
        sys.exit(1)
    
    main(sys.argv[1:])