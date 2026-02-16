from __future__ import annotations

import time
import traceback
from pathlib import Path
from typing import Optional

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    TK_AVAILABLE = True
    TK_IMPORT_ERROR: Optional[Exception] = None
except ImportError as exc:
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]
    ScrolledText = None  # type: ignore[assignment]
    TK_AVAILABLE = False
    TK_IMPORT_ERROR = exc

from .graph import ClauseAtomGraph, build_graph_for_selection, validate_selection_scope
from .tf_loader import load_bhsa
from .viz import RenderOptions, graphviz_available, render


class BhsHierarchyGui:
    FORMATS = ("svg", "png", "pdf", "dot")

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("BHS Hierarchy Renderer")
        self.root.geometry("980x700")

        self.graph: Optional[ClauseAtomGraph] = None

        self.version_var = tk.StringVar(value="2021")
        self.book_var = tk.StringVar(value="Genesis")
        self.chapter_var = tk.StringVar()
        self.verse_from_var = tk.StringVar()
        self.verse_to_var = tk.StringVar()
        self.format_var = tk.StringVar(value="svg")
        self.output_path_var = tk.StringVar(value="out/tree.svg")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()
        if not graphviz_available():
            self._log("Graphviz dot not found: SVG/PNG/PDF rendering disabled. Use DOT format.")

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        selection = ttk.LabelFrame(frame, text="Selection", padding=10)
        selection.pack(fill=tk.X)

        ttk.Label(selection, text="Version").grid(row=0, column=0, sticky="w")
        ttk.Entry(selection, textvariable=self.version_var, width=12).grid(
            row=0, column=1, sticky="w", padx=(6, 14)
        )

        ttk.Label(selection, text="Book").grid(row=0, column=2, sticky="w")
        ttk.Entry(selection, textvariable=self.book_var, width=20).grid(
            row=0, column=3, sticky="w", padx=(6, 0)
        )

        ttk.Label(selection, text="Chapter (optional)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(selection, textvariable=self.chapter_var, width=12).grid(
            row=1, column=1, sticky="w", padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(selection, text="Verse from (optional)").grid(
            row=1, column=2, sticky="w", pady=(8, 0)
        )
        ttk.Entry(selection, textvariable=self.verse_from_var, width=12).grid(
            row=1, column=3, sticky="w", padx=(6, 14), pady=(8, 0)
        )

        ttk.Label(selection, text="Verse to (optional)").grid(row=1, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(selection, textvariable=self.verse_to_var, width=12).grid(
            row=1, column=5, sticky="w", padx=(6, 0), pady=(8, 0)
        )

        output = ttk.LabelFrame(frame, text="Output", padding=10)
        output.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(output, text="Format").grid(row=0, column=0, sticky="w")
        fmt = ttk.Combobox(
            output,
            textvariable=self.format_var,
            values=self.FORMATS,
            width=10,
            state="readonly",
        )
        fmt.grid(row=0, column=1, sticky="w", padx=(6, 14))
        fmt.bind("<<ComboboxSelected>>", self._on_format_change)

        ttk.Label(output, text="Output path").grid(row=0, column=2, sticky="w")
        ttk.Entry(output, textvariable=self.output_path_var).grid(
            row=0, column=3, sticky="ew", padx=(6, 6)
        )
        ttk.Button(output, text="Browse", command=self._browse_output_path).grid(row=0, column=4, sticky="e")
        output.columnconfigure(3, weight=1)

        buttons = ttk.Frame(frame)
        buttons.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(buttons, text="Load roots", command=self._load_roots).pack(side=tk.LEFT)
        ttk.Button(buttons, text="Render selected root", command=self._render_selected_root).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        roots = ttk.LabelFrame(frame, text="Roots", padding=10)
        roots.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.roots_list = tk.Listbox(roots, height=10, exportselection=False)
        root_scroll = ttk.Scrollbar(roots, orient=tk.VERTICAL, command=self.roots_list.yview)
        self.roots_list.configure(yscrollcommand=root_scroll.set)
        self.roots_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        root_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(frame, textvariable=self.status_var).pack(anchor="w", pady=(10, 0))

        log_frame = ttk.LabelFrame(frame, text="Status log", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.log_text = ScrolledText(log_frame, height=10, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def _on_format_change(self, _event: object = None) -> None:
        fmt = self.format_var.get().strip().lower()
        out = self.output_path_var.get().strip()
        if fmt not in self.FORMATS:
            return
        if not out:
            self.output_path_var.set(f"out/tree.{fmt}")
            return
        path = Path(out)
        if path.suffix.lower() != f".{fmt}":
            self.output_path_var.set(str(path.with_suffix(f".{fmt}")))

    def _browse_output_path(self) -> None:
        fmt = self.format_var.get().strip().lower() or "svg"
        current = Path(self.output_path_var.get().strip() or f"out/tree.{fmt}")
        selected = filedialog.asksaveasfilename(
            title="Choose output file",
            initialdir=str(current.parent) if current.parent.exists() else ".",
            initialfile=current.name,
            defaultextension=f".{fmt}",
            filetypes=[
                ("SVG", "*.svg"),
                ("PNG", "*.png"),
                ("PDF", "*.pdf"),
                ("DOT", "*.dot"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.output_path_var.set(selected)
            self._log(f"Output path set to {selected}")

    def _parse_optional_int(self, value: str, field_name: str) -> Optional[int]:
        value = value.strip()
        if not value:
            return None
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer.") from exc
        if number <= 0:
            raise ValueError(f"{field_name} must be greater than 0.")
        return number

    def _selection_values(
        self,
    ) -> tuple[str, str, Optional[int], Optional[int], Optional[int]]:
        version = self.version_var.get().strip()
        if not version:
            raise ValueError("Version is required.")

        book = self.book_var.get().strip()
        if not book:
            raise ValueError("Book is required.")

        chapter = self._parse_optional_int(self.chapter_var.get(), "Chapter")
        verse_from = self._parse_optional_int(self.verse_from_var.get(), "Verse from")
        verse_to = self._parse_optional_int(self.verse_to_var.get(), "Verse to")

        if (verse_from is not None or verse_to is not None) and chapter is None:
            raise ValueError("Chapter is required when verse range is set.")
        if verse_to is not None and verse_from is None:
            raise ValueError("Verse from is required when verse to is set.")

        validate_selection_scope(
            book=book,
            chapter=chapter,
            verse_from=verse_from,
            verse_to=verse_to,
        )

        return version, book, chapter, verse_from, verse_to

    def _load_roots(self) -> None:
        try:
            version, book, chapter, verse_from, verse_to = self._selection_values()
            self._set_status("Loading BHSA dataset...")
            api = load_bhsa(version=version, silent=True)
            self._set_status("Building graph...")
            graph = build_graph_for_selection(
                api,
                book=book,
                chapter=chapter,
                verse_from=verse_from,
                verse_to=verse_to,
            )
        except Exception as exc:  # noqa: BLE001 - convert all UI errors to visible feedback
            self._handle_error("Load roots", exc)
            return

        self.graph = graph
        self.roots_list.delete(0, tk.END)

        for idx, root in enumerate(graph.roots):
            item = (
                f"[{idx}] node={root} {graph.section_label(root)} "
                f"{graph.typ(root)}  {graph.text(root)}"
            )
            self.roots_list.insert(tk.END, item)

        if graph.roots:
            self.roots_list.selection_set(0)
            self.roots_list.activate(0)
            self._set_status(f"Loaded {len(graph.roots)} root(s).")
            self._log(f"Loaded {len(graph.roots)} roots.")
            return

        self._set_status("No roots found for selection.")
        self._log("No roots found for current selection.")
        messagebox.showinfo("No roots found", "No roots were found for this selection.")

    def _render_selected_root(self) -> None:
        if self.graph is None:
            messagebox.showwarning("Load roots first", "Load roots before rendering.")
            return

        selected = self.roots_list.curselection()
        if not selected:
            messagebox.showwarning("No root selected", "Select one root from the list.")
            return

        try:
            idx = selected[0]
            root = self.graph.roots[idx]
            fmt = self.format_var.get().strip().lower()
            if fmt not in self.FORMATS:
                raise ValueError(f"Unsupported output format: {fmt}")

            output = self.output_path_var.get().strip()
            if not output:
                raise ValueError("Output path is required.")

            out_path = Path(output).expanduser()
            if out_path.suffix.lower() != f".{fmt}":
                out_path = out_path.with_suffix(f".{fmt}")
                self.output_path_var.set(str(out_path))
                self._log(f"Adjusted output extension to .{fmt}")

            if fmt != "dot" and not graphviz_available():
                raise RuntimeError(
                    "Graphviz dot is not available. Install Graphviz or choose DOT format."
                )

            self._set_status("Rendering selected root...")
            rendered = render(
                self.graph,
                roots=[root],
                out_path=out_path,
                fmt=fmt,
                opts=RenderOptions(show_code=True, show_tab=False),
            )
        except Exception as exc:  # noqa: BLE001 - convert all UI errors to visible feedback
            self._handle_error("Render selected root", exc)
            return

        self._set_status(f"Rendered to {rendered}")
        self._log(f"Rendered root index {idx} (node {root}) to {rendered}")
        messagebox.showinfo("Render complete", f"Rendered file:\n{rendered}")

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.root.update_idletasks()

    def _log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _handle_error(self, action: str, exc: Exception) -> None:
        self._set_status(f"{action} failed")
        self._log(f"{action} error: {exc}")
        self._log(traceback.format_exc().rstrip())
        messagebox.showerror("Error", f"{action} failed:\n{exc}")


def main() -> None:
    if not TK_AVAILABLE:
        raise SystemExit(
            "tkinter is not installed. Install tkinter/python3-tk first, then run bhs-hier-gui again."
        ) from TK_IMPORT_ERROR

    root = tk.Tk()
    BhsHierarchyGui(root)
    root.mainloop()


if __name__ == "__main__":
    main()
