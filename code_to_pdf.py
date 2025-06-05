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
    while all(len(line) > 0 and line[0] == " " for line in snippet):
        for i in range(len(snippet)):
            snippet[i] = snippet[i][1:]


def clang_find_function(
    node: any, func_name: str, helpers: set[str], processed: set[str]
) -> tuple[None, None]:
    """
    Recursively visit the nodes of the clang-parsed AST.
    """
    bounds = None
    if (
        node.kind == clang.cindex.CursorKind.FUNCTION_DECL
        and node.spelling == func_name
        and node.is_definition()
    ):
        # update the start/end bounds
        bounds = (node.extent.start.offset, node.extent.end.offset)
        processed.add(func_name)
        for child in node.get_children():
            if child.kind == clang.cindex.CursorKind.COMPOUND_STMT:
                # go through the function body now
                for subchild in child.get_children():
                    if subchild.kind == clang.cindex.CursorKind.CALL_EXPR:
                        helpers.add(subchild.spelling)
    else:
        # keep looking
        for child in node.get_children():
            bounds = clang_find_function(child, func_name, helpers, processed)
            if bounds:
                break

    return bounds


def get_cpp_func(content: str, fname: str, func_name: str) -> str:
    """
    Parse the given C++ file using clang to find the named function body.
    """

    index = clang.cindex.Index.create()
    # Get the "translation unit" resulting from parsing the file
    # redundant read of the file, but that's what clang wants
    tu = index.parse(fname, args=["-std=c++17"])

    # then recursively visit and search for the function
    helpers = set()
    processed = config.ignore_helpers
    bounds = clang_find_function(tu.cursor, func_name, helpers, processed)

    snippet = ""

    if bounds:
        snippet = content[bounds[0] : bounds[1]]

    # check for helper functions as well
    while helpers:
        helper = helpers.pop()
        if helper not in processed:
            bounds = clang_find_function(tu.cursor, helper, helpers, processed)
            if bounds:
                snippet += "\n\n" + content[bounds[0] : bounds[1]]
            processed.add(helper)

    return snippet


def get_python_func(
    content: str, func_name: str, helpers: set[str], processed: set[str]
) -> str:
    """
    Parse the given Python code using ast to find the named function body.
    """
    tree = ast.parse(content)
    snippet = ""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            # add the function body to the snippet
            snippet += ast.get_source_segment(content, node).strip()
            processed.add(node.name)

            # check for helper functions and add to the set
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    # for some reason function calls can be either ast.Name or ast.Attr
                    name = (
                        child.func.id
                        if isinstance(child.func, ast.Name)
                        else child.func.attr
                    )
                    helpers.add(name)

            while helpers:
                helper = helpers.pop()
                if helper not in processed:
                    # recursively call self
                    snippet += "\n" + get_python_func(
                        content, helper, helpers, processed
                    )

    return snippet


def find_snippet(fname: str) -> list[str]:
    """
    Finds the code snippet defined by config.regex.
    """
    with open(fname, "r") as f:
        content = f.read()

    if config.language == "c++":
        snippet = get_cpp_func(content, fname, config.function_name)
    elif config.language == "python":
        helpers = set()
        processed = config.ignore_helpers
        snippet = get_python_func(content, config.function_name, helpers, processed)
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
    if not (student_name := Path(fname).parent.name):
        student_name = Path(fname).name

    student_name = student_name.replace("_", "")

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
        if code := find_snippet(fname):
            fontsize = calc_fontsize(code)
            write_tex(fname, code, fontsize)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python code_to_pdf.py <input_files>")
        sys.exit(1)

    main(sys.argv[1:])
