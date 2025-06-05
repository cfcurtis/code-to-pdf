from pathlib import Path

output_dir = Path("testing/output")
template = "templates/one_page.tex"
title_prefix = "COMP 1633 A1 Quiz"
function_name = r"print_report"
language = "c++" # python or c++, case-sensitive
ignore_helpers = set([]) # which helper functions to ignore?