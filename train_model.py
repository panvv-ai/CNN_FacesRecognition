"""Deprecated compatibility module and training entrypoint."""

from face_workbench.legacy import Model

if __name__ == "__main__":
    from face_workbench.cli import app

    print("此入口已弃用，正在转发到统一 CLI。建议运行：python main.py")
    app(["train"])


__all__ = ["Model"]
