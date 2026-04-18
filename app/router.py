import re


def select_model(query: str) -> str:
    if len(query) > 200:
        return "claude"
    complex_patterns = [
        r"代码", r"编程", r"算法", r"数学", r"证明",
        r"分析.*原因", r"比较.*区别", r"为什么.*不能",
        r"如何.*实现", r"请.*详细.*解释",
    ]
    for pattern in complex_patterns:
        if re.search(pattern, query):
            return "claude"
    return "deepseek"
