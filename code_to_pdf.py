import sys
from pathlib import Path
import config

if config.language == "c++":
    import clang.cindex

    # Not great...
    clang.cindex.Config.set_library_file("/usr/lib64/llvm20/lib/libclang.so.20.1")
elif config.language == "python":
    import ast

MAX_HEIGHT_IN = 8.5
MAX_WIDTH_IN = 7
PT_PER_INCH = 72
BOX_WIDTH_EM = 0.6  # listing package default
LINE_SPACE_SCALE = 2  # double space


def unindent(snippet: list[str]) -> None:
    """
    Remove any consistent indentation from all lines
    """
    all_indented = True
    while all_indented:
        for line in snippet:
            all_indented = all_indented and len(line) > 0 and line[0] == " "

        if all_indented:
            for i in range(len(snippet)):
                snippet[i] = snippet[i][1:]


def clang_find_function(node) -> tuple[None, None]:
    """
    Recursively visit the nodes of the clang-parsed AST.
    """
    bounds = None
    if (
        node.kind == clang.cindex.CursorKind.FUNCTION_DECL
        and node.spelling == config.function_name
        and node.is_definition()
    ):
        # update the start/end bounds
        bounds = (node.extent.start.offset,
                  node.extent.end.offset)
    else:
        for child in node.get_children():
            bounds = clang_find_function(child)
            if bounds:
                break
    
    return bounds

def get_cpp_func(content: str, fname: str) -> str:
    """
    Parse the given C++ file using clang to find the named function body.
    """

    index = clang.cindex.Index.create()
    # Get the "translation unit" resulting from parsing the file
    # redundant read of the file, but that's what clang wants
    tu = index.parse(fname, args=["-std=c++17"])

    # then recursively visit and search for the function
    bounds = clang_find_function(tu.cursor)

    if bounds:
        return content[bounds[0]:bounds[1]]
    else:
        return ""

def get_python_func(content: str) -> str:
    """
    Parse the given Python code using ast to find the named function body.
    """
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == config.function_name:
            return ast.get_source_segment(content, node)

    # couldn't find it, return an empty string
    return ""


def find_snippet(fname: str) -> list[str]:
    """
    Finds the code snippet defined by config.regex.
    """
    with open(fname, "r") as f:
        content = f.read()

    if config.language == "c++":
        snippet = get_cpp_func(content, fname)
    elif config.language == "python":
        snippet = get_python_func(content)
    else:
        print("Sorry, only C++ and Python supported at this time")
        sys.exit(1)

    if not snippet:
        print(f"Warning: function {config.function_name} not found in {fname}")
    else:
        snippet = snippet.strip().splitlines()
        unindent(snippet)

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
    text = text.replace("REPLACEWITHLANGUGE", config.language)
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
