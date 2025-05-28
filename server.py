# 交互式反馈 MCP
# 由 Fábio Ferreira 开发 (https://x.com/fabiomlferreira)
# 灵感来源/相关项目: dotcursorrules.com (https://dotcursorrules.com/)
# 由 Pau Oliva (https://x.com/pof) 增强，借鉴了 https://github.com/ttommyth/interactive-mcp 的想法
import os
import sys
import json
import tempfile
import subprocess

from typing import Annotated, Dict

from fastmcp import FastMCP
from pydantic import Field

# 日志级别(log_level)对于 Cline 的正常工作是必要的: https://github.com/jlowin/fastmcp/issues/81
mcp = FastMCP("Interactive Feedback MCP", log_level="ERROR")

def launch_feedback_ui(summary: str, predefinedOptions: list[str] | None = None) -> dict[str, str]:
    # 为反馈结果创建一个临时文件
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_file = tmp.name

    try:
        # 获取相对于此脚本的 feedback_ui.py 路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        feedback_ui_path = os.path.join(script_dir, "feedback_ui.py")

        # 作为独立进程运行 feedback_ui.py
        # 注意: uv 中似乎存在一个 bug，因此我们需要
        # 传递一些特殊的标志才能使其工作
        args = [
            sys.executable,
            "-u",
            feedback_ui_path,
            "--prompt", summary,
            "--output-file", output_file,
            "--predefined-options", "|||".join(predefinedOptions) if predefinedOptions else ""
        ]
        result = subprocess.run(
            args,
            check=False,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True
        )
        if result.returncode != 0:
            raise Exception(f"Failed to launch feedback UI: {result.returncode}")

        # 从临时文件中读取结果
        with open(output_file, 'r') as f:
            result = json.load(f)
        os.unlink(output_file)
        return result
    except Exception as e:
        if os.path.exists(output_file):
            os.unlink(output_file)
        raise e

@mcp.tool()
def interactive_feedback(
    message: str = Field(description="向用户提出的具体问题"),
    predefined_options: list = Field(default=None, description="供用户选择的预定义选项 (可选)"),
) -> Dict[str, str]:
    """请求用户进行交互式反馈"""
    predefined_options_list = predefined_options if isinstance(predefined_options, list) else None
    return launch_feedback_ui(message, predefined_options_list)

if __name__ == "__main__":
    mcp.run(transport="stdio")
