import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

class DataView(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, padding=10)
        self.controller = controller

        # 当前查询用到的列和数据
        self.columns = []
        self.orig = []  # 原始数据字典列表
        self.full = []  # 应用筛选或排序后的数据

        self.sort_states = {}  # 各列排序状态：True=升序，False=降序

        self.create_widgets()

    def create_widgets(self):
        # 查询类型区
        ttk.Label(self, text="查询类型:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.cb = ttk.Combobox(self, values=[
            "全部库存",
            "按商品统计盈亏",
            "按货商统计盈亏",
            "快递单号查询",
            "按货商的入库次数"
        ], state="readonly", width=20)
        self.cb.current(0)
        self.cb.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.cb.bind("<<ComboboxSelected>>", self.on_q)

        self.lbl_cond = ttk.Label(self, text="查询条件:")
        self.lbl_cond.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.ent_cond = ttk.Entry(self, width=20)
        self.ent_cond.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.ent_cond.bind("<Return>", lambda e: self.exec_q())

        ttk.Button(self, text="查询", command=self.exec_q).grid(row=0, column=4, padx=5, pady=5)
        self.btn_invoice = ttk.Button(self, text="生成票据", command=self.generate_invoice)
        self.btn_invoice.grid(row=0, column=5, padx=5, pady=5)
        self.btn_invoice.state(["disabled"]) 
        self.btn_print_detail = ttk.Button(self, text="打印明细", command=self.open_print_detail_dialog)
        self.btn_print_detail.grid(row=0, column=6, padx=5, pady=5)
        print_tools = ttk.Frame(self)
        print_tools.grid(row=0, column=7, padx=5, pady=5, sticky="w")
        ttk.Button(print_tools, text="全选打印", command=self.select_all_print).pack(side=tk.LEFT, padx=2)
        ttk.Button(print_tools, text="取消全选", command=self.deselect_all_print).pack(side=tk.LEFT, padx=2)
        self.lbl_print_selected_count = ttk.Label(print_tools, text="已选中 0 条")
        self.lbl_print_selected_count.pack(side=tk.LEFT, padx=5)
        self.on_q()

        # 结果表格
        self.tree = ttk.Treeview(self, show="headings", selectmode="extended")
        self.tree.grid(row=1, column=0, columnspan=8, sticky="nsew")
        # 仅"出库状态"列上色
        self.tree.tag_configure('outbound', foreground='green')
        self.tree.tag_configure('inbound',  foreground='blue')
        # 绑定双击事件
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_selection_change)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.grid(row=1, column=8, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=2, column=0, columnspan=8, sticky="ew")
        self.tree.configure(xscrollcommand=hsb.set)

        # 筛选区
        self.filter_canvas = tk.Canvas(self, height=60)
        self.filter_canvas.grid(row=3, column=0, columnspan=8, sticky="ew")
        fhsb = ttk.Scrollbar(self, orient="horizontal", command=self.filter_canvas.xview)
        fhsb.grid(row=4, column=0, columnspan=8, sticky="ew")
        self.filter_canvas.configure(xscrollcommand=fhsb.set)
        self.filter_inner = ttk.Frame(self.filter_canvas)
        self.filter_canvas.create_window((0,0), window=self.filter_inner, anchor="nw")
        self.filter_inner.bind(
            "<Configure>",
            lambda e: self.filter_canvas.configure(scrollregion=self.filter_canvas.bbox("all"))
        )
        self.filter_entries = {}
        self.row_items = {}
        self.create_filter_row()
        self.update_invoice_button_state()

        # 指标显示区
        self.lbl_sold_profit      = ttk.Label(self, text="卖出总利润: 0.00")
        self.lbl_settled_profit   = ttk.Label(self, text="已出库已结算总利润: 0.00")
        self.lbl_inventory_value  = ttk.Label(self, text="库存价值: 0.00")
        self.lbl_shipping_cost    = ttk.Label(self, text="快递总费用: 0.00")
        self.lbl_commission_cost  = ttk.Label(self, text="佣金总费用: 0.00")
        self.lbl_unsettled_amount = ttk.Label(self, text="未结清金额: 0.00")
        self.lbl_total_market     = ttk.Label(self, text="行情价总和: 0.00")
        self.lbl_total_rows       = ttk.Label(self, text="总条数: 0")
        self.lbl_total_qty        = ttk.Label(self, text="商品数量总和: 0.00")

        self.lbl_sold_profit     .grid(row=5, column=0, columnspan=8, sticky="w", pady=(10,0))
        self.lbl_settled_profit  .grid(row=6, column=0, columnspan=8, sticky="w")
        self.lbl_inventory_value.grid(row=7, column=0, columnspan=8, sticky="w")
        self.lbl_shipping_cost  .grid(row=8, column=0, columnspan=8, sticky="w")
        self.lbl_commission_cost.grid(row=9, column=0, columnspan=8, sticky="w")
        self.lbl_unsettled_amount.grid(row=10, column=0, columnspan=8, sticky="w")
        self.lbl_total_market   .grid(row=11, column=0, columnspan=8, sticky="w")
        self.lbl_total_rows     .grid(row=12, column=0, columnspan=8, sticky="w")
        self.lbl_total_qty      .grid(row=13, column=0, columnspan=8, sticky="w")

        # 布局权重
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(4, weight=1)

    def create_filter_row(self):
        for w in self.filter_inner.winfo_children():
            w.destroy()
        self.filter_entries.clear()
        if not self.columns:
            return
        for i, c in enumerate(self.columns):
            ttk.Label(self.filter_inner, text=c).grid(row=0, column=i, padx=2, pady=2)
            w = 20 if c == "出库记录" else 10
            e = ttk.Entry(self.filter_inner, width=w)
            e.grid(row=1, column=i, padx=2, pady=2)
            e.bind("<Return>", lambda ev: self.apply_filters())
            self.filter_entries[c] = e
        idx = len(self.columns)
        ttk.Button(self.filter_inner, text="应用筛选", command=self.apply_filters)\
            .grid(row=1, column=idx, padx=5)
        ttk.Button(self.filter_inner, text="清空筛选条件", command=self.clear_filters)\
            .grid(row=1, column=idx+1, padx=5)

    def _tree_columns(self):
        return list(self.columns)

    def _configure_tree_columns(self):
        tree_columns = self._tree_columns()
        self.tree["columns"] = tree_columns
        for c in tree_columns:
            self.tree.heading(c, text=c, command=lambda c=c: self.sort_by(c))
            width = 140 if c == "出库记录" else 100
            self.tree.column(c, width=width, anchor="center")

    def _display_cell_value(self, row, col):
        if col == "出库记录":
            return "双击查询详细"
        return row.get(col, "")

    def _row_values(self, row):
        return [self._display_cell_value(row, c) for c in self.columns]

    def _row_tags(self, row):
        return ("outbound" if row.get("出库状态", "") == "卖出" else "inbound",)

    def _selected_row_keys(self):
        return {id(self.row_items[i]) for i in self.tree.selection() if i in self.row_items}

    def _redraw_tree_rows(self, preserve_selection=True):
        selected_keys = self._selected_row_keys() if preserve_selection else set()
        self.tree.delete(*self.tree.get_children())
        self.row_items.clear()
        selected_items = []
        for row in self.full:
            iid = self.tree.insert("", tk.END, values=self._row_values(row), tags=self._row_tags(row))
            self.row_items[iid] = row
            if id(row) in selected_keys:
                selected_items.append(iid)
        if selected_items:
            self.tree.selection_set(selected_items)
        self._update_print_selected_count()
        self.update_invoice_button_state()

    def _identify_tree_column_name(self, x):
        column = self.tree.identify_column(x)
        if not column:
            return ""
        try:
            col_index = int(column.replace("#", "")) - 1
        except ValueError:
            return ""
        tree_columns = list(self.tree["columns"])
        if col_index < 0 or col_index >= len(tree_columns):
            return ""
        return tree_columns[col_index]

    def on_tree_selection_change(self, event=None):
        self._update_print_selected_count()
        self.update_invoice_button_state()

    def _update_print_selected_count(self):
        count = len(self.tree.selection())
        if hasattr(self, "lbl_print_selected_count"):
            self.lbl_print_selected_count.config(text=f"已选中 {count} 条")

    def select_all_print(self):
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children)
        self._update_print_selected_count()
        self.update_invoice_button_state()

    def deselect_all_print(self):
        children = self.tree.get_children()
        if children:
            self.tree.selection_remove(children)
        self._update_print_selected_count()
        self.update_invoice_button_state()

    def _get_selected_print_rows(self):
        rows = []
        for item in self.tree.selection():
            row = self.row_items.get(item)
            if row:
                rows.append(row)
        return rows

    def open_print_detail_dialog(self):
        rows = self._get_selected_print_rows()
        if not rows:
            messagebox.showwarning("提示", "请先选择至少一条需要打印的记录！")
            return

        available_cols = list(getattr(self, "all_columns", []) or self.columns)
        available_cols = [c for c in available_cols if any(c in row for row in rows)]
        if not available_cols:
            messagebox.showwarning("提示", "当前查询结果没有可打印的列！")
            return

        saved_cols = self.controller.settings_model.get_display_columns("data_query_print")
        default_cols = [c for c in saved_cols if c in available_cols]
        if not default_cols:
            default_cols = [c for c in self.columns if c in available_cols]
        if not default_cols:
            default_cols = list(available_cols)
        default_aliases = self.controller.settings_model.get_column_aliases("data_query_print")
        self._show_print_column_dialog(rows, available_cols, default_cols, default_aliases)

    def _show_print_column_dialog(self, rows, available_cols, default_cols, default_aliases=None):
        win = tk.Toplevel(self)
        win.title("选择打印列")
        win.geometry("520x600")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        title_frame = ttk.Frame(win)
        title_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        ttk.Label(title_frame, text="打印页名称:").pack(side=tk.LEFT)
        title_var = tk.StringVar(value="数据查询打印明细")
        ttk.Entry(title_frame, textvariable=title_var, width=24).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        remark_frame = ttk.Frame(win)
        remark_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(remark_frame, text="打印备注:").pack(side=tk.LEFT)
        remark_var = tk.StringVar()
        ttk.Entry(remark_frame, textvariable=remark_var, width=24).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))

        orientation_frame = ttk.Frame(win)
        orientation_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
        ttk.Label(orientation_frame, text="打印方向:").pack(side=tk.LEFT)
        orientation_var = tk.StringVar(value="portrait")
        ttk.Radiobutton(orientation_frame, text="纵向", value="portrait", variable=orientation_var).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Radiobutton(orientation_frame, text="横向", value="landscape", variable=orientation_var).pack(side=tk.LEFT, padx=5)

        ttk.Label(win, text=f"已选择 {len(rows)} 条记录，请选择打印列：").pack(anchor="w", padx=10, pady=(5, 5))

        body = ttk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        canvas = tk.Canvas(body, borderwidth=0, highlightthickness=0)
        scroll = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(inner, text="打印", width=6).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ttk.Label(inner, text="原列名", width=16).grid(row=0, column=1, sticky="w", padx=5, pady=2)
        ttk.Label(inner, text="打印列名", width=22).grid(row=0, column=2, sticky="w", padx=5, pady=2)

        vars_by_col = {}
        alias_vars_by_col = {}
        default_set = set(default_cols)
        default_aliases = default_aliases or {}
        for row_index, col in enumerate(available_cols, 1):
            var = tk.BooleanVar(value=col in default_set)
            vars_by_col[col] = var
            ttk.Checkbutton(inner, variable=var).grid(row=row_index, column=0, sticky="w", padx=5, pady=2)
            ttk.Label(inner, text=col, width=16).grid(row=row_index, column=1, sticky="w", padx=5, pady=2)
            alias_var = tk.StringVar(value=default_aliases.get(col, ""))
            alias_vars_by_col[col] = alias_var
            ttk.Entry(inner, textvariable=alias_var, width=24).grid(row=row_index, column=2, sticky="ew", padx=5, pady=2)
        inner.grid_columnconfigure(2, weight=1)

        btn_frame = ttk.Frame(win)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)

        def set_all(value):
            for var in vars_by_col.values():
                var.set(value)

        def preview():
            selected_cols = [col for col in available_cols if vars_by_col[col].get()]
            if not selected_cols:
                messagebox.showwarning("提示", "请至少选择一列打印！", parent=win)
                return
            column_aliases = {
                col: (alias_vars_by_col[col].get().strip() or col)
                for col in selected_cols
            }
            print_title = title_var.get().strip() or "数据查询打印明细"
            print_remark = remark_var.get().strip()
            orientation = orientation_var.get()
            win.destroy()
            self.show_print_preview(rows, selected_cols, print_title, orientation, print_remark, column_aliases)

        ttk.Button(btn_frame, text="全选", command=lambda: set_all(True)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="清空", command=lambda: set_all(False)).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="预览", command=preview).pack(side=tk.RIGHT, padx=3)
        ttk.Button(btn_frame, text="取消", command=win.destroy).pack(side=tk.RIGHT, padx=3)

    def show_print_preview(self, rows, columns, print_title="数据查询打印明细", orientation="portrait", print_remark="", column_aliases=None):
        try:
            from PIL import ImageTk
            pages = self._render_print_pages(rows, columns, print_title, orientation, print_remark, column_aliases)
        except Exception as e:
            messagebox.showerror("错误", f"生成打印预览失败: {e}")
            return

        win = tk.Toplevel(self)
        win.title("打印明细预览")
        win.geometry("980x760")
        win.transient(self.winfo_toplevel())

        toolbar = ttk.Frame(win)
        toolbar.pack(fill=tk.X, padx=10, pady=8)
        orientation_text = "横向" if orientation == "landscape" else "纵向"
        ttk.Label(toolbar, text=f"共 {len(rows)} 条，{len(columns)} 列，{len(pages)} 页，{orientation_text}").pack(side=tk.LEFT)

        printer_frame = ttk.Frame(win)
        printer_frame.pack(fill=tk.X, padx=10, pady=(0, 8))
        ttk.Label(printer_frame, text="打印机:").pack(side=tk.LEFT)
        printer_var = tk.StringVar()
        printers = self._get_printer_names()
        printer_combo = ttk.Combobox(printer_frame, textvariable=printer_var, values=printers, state="readonly", width=36)
        printer_combo.pack(side=tk.LEFT, padx=5)
        if printers:
            try:
                import win32print
                default_printer = win32print.GetDefaultPrinter()
            except Exception:
                default_printer = ""
            printer_var.set(default_printer if default_printer in printers else printers[0])
        else:
            printer_combo.state(["disabled"])
            printer_var.set("未找到可用打印机")
        ttk.Label(printer_frame, text=f"打印页名称: {print_title}").pack(side=tk.LEFT, padx=12)

        def do_print():
            printer_name = printer_var.get().strip()
            if not printers or printer_name not in printers:
                messagebox.showwarning("提示", "请先选择可用打印机。", parent=win)
                return
            try:
                self._send_print_pages(pages, printer_name, print_title)
                messagebox.showinfo("成功", f"已发送到打印机：{printer_name}", parent=win)
            except Exception as e:
                messagebox.showerror("打印失败", str(e), parent=win)

        ttk.Button(toolbar, text="打印", command=do_print).pack(side=tk.RIGHT, padx=5)
        ttk.Button(toolbar, text="关闭", command=win.destroy).pack(side=tk.RIGHT, padx=5)

        body = ttk.Frame(win)
        body.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(body, background="#f0f0f0")
        yscroll = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        xscroll = ttk.Scrollbar(body, orient="horizontal", command=canvas.xview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        preview_images = []
        for page_no, page in enumerate(pages, 1):
            scale = min(1.0, 860 / page.width)
            preview = page.resize((int(page.width * scale), int(page.height * scale)))
            tk_img = ImageTk.PhotoImage(preview)
            preview_images.append(tk_img)
            ttk.Label(inner, text=f"第 {page_no} 页").pack(pady=(10, 2))
            tk.Label(inner, image=tk_img, background="white", borderwidth=1, relief="solid").pack(padx=20, pady=(0, 12))
        win.preview_images = preview_images

    def _load_print_font(self, size):
        from PIL import ImageFont
        font_paths = [
            r"C:\Windows\Fonts\msyh.ttc",
            r"C:\Windows\Fonts\msyh.ttf",
            r"C:\Windows\Fonts\simhei.ttf",
            r"C:\Windows\Fonts\simsun.ttc",
            r"C:\Windows\Fonts\simsun.ttf",
            r"C:\Windows\Fonts\Microsoft YaHei UI.ttf",
        ]
        for path in font_paths:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        return ImageFont.load_default()

    def _text_width(self, draw, text, font):
        try:
            box = draw.textbbox((0, 0), str(text), font=font)
            return box[2] - box[0]
        except Exception:
            return len(str(text)) * 10

    def _line_height(self, draw, font):
        try:
            box = draw.textbbox((0, 0), "国", font=font)
            return max(18, box[3] - box[1] + 6)
        except Exception:
            return 22

    def _wrap_print_text(self, draw, text, font, max_width, max_lines=8):
        text = "" if text is None else str(text)
        max_width = max(10, max_width)
        lines = []
        for raw_line in text.replace("\r", "").split("\n"):
            current = ""
            for ch in raw_line:
                candidate = current + ch
                if current and self._text_width(draw, candidate, font) > max_width:
                    lines.append(current)
                    current = ch
                else:
                    current = candidate
            lines.append(current)
        if not lines:
            lines = [""]
        if max_lines and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = "..."
        return lines

    def _fit_print_text(self, draw, text, font, max_width):
        text = "" if text is None else str(text)
        if self._text_width(draw, text, font) <= max_width:
            return text
        ellipsis = "..."
        available = max(0, max_width - self._text_width(draw, ellipsis, font))
        fitted = ""
        for ch in text:
            candidate = fitted + ch
            if self._text_width(draw, candidate, font) > available:
                break
            fitted = candidate
        return (fitted + ellipsis) if fitted else ellipsis

    def _calculate_print_widths(self, rows, columns, draw, header_font, text_font, available_width, column_labels=None):
        count = max(len(columns), 1)
        min_width = max(36, min(80, available_width // count // 2))
        max_width = max(min_width, min(260, available_width // 2))
        preferred = []
        sample_rows = rows[:80]
        column_labels = column_labels or columns
        for idx, col in enumerate(columns):
            label = column_labels[idx] if idx < len(column_labels) else col
            width = self._text_width(draw, label, header_font) + 18
            for row in sample_rows:
                width = max(width, self._text_width(draw, row.get(col, ""), text_font) + 18)
            preferred.append(max(min_width, min(width, max_width)))

        total = sum(preferred)
        if total == available_width:
            return preferred
        if total > available_width:
            if min_width * count >= available_width:
                base = max(1, available_width // count)
                widths = [base] * count
            else:
                flex_total = sum(w - min_width for w in preferred) or 1
                spare = available_width - min_width * count
                widths = [min_width + int((w - min_width) * spare / flex_total) for w in preferred]
        else:
            widths = list(preferred)
            extra = available_width - total
            i = 0
            while extra > 0 and any(w < max_width for w in widths):
                if widths[i % count] < max_width:
                    widths[i % count] += 1
                    extra -= 1
                i += 1

        diff = available_width - sum(widths)
        i = 0
        while diff != 0 and widths:
            idx = i % len(widths)
            if diff > 0:
                widths[idx] += 1
                diff -= 1
            elif widths[idx] > 1:
                widths[idx] -= 1
                diff += 1
            i += 1
            if i > 10000:
                break
        return widths

    def _render_print_pages(self, rows, columns, print_title="数据查询打印明细", orientation="portrait", print_remark="", column_aliases=None):
        from PIL import Image, ImageDraw

        print_title = (print_title or "数据查询打印明细").strip() or "数据查询打印明细"
        print_remark = (print_remark or "").strip()
        column_aliases = column_aliases or {}
        column_labels = [(column_aliases.get(col, "") or col) for col in columns]
        if orientation == "landscape":
            page_width, page_height = 1754, 1240
        else:
            page_width, page_height = 1240, 1754
        margin = 70
        table_width = page_width - margin * 2
        title_font = self._load_print_font(28)
        meta_font = self._load_print_font(16)
        header_font = self._load_print_font(15)
        text_font = self._load_print_font(14)
        footer_font = self._load_print_font(13)
        probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        line_h = self._line_height(probe, text_font)
        header_line_h = self._line_height(probe, header_font)
        pad = 6
        widths = self._calculate_print_widths(rows, columns, probe, header_font, text_font, table_width, column_labels)
        header_lines = [
            self._wrap_print_text(probe, label, header_font, max(10, widths[i] - pad * 2), max_lines=3)
            for i, label in enumerate(column_labels)
        ]
        header_h = max(34, max(len(lines) for lines in header_lines) * header_line_h + pad * 2)
        bottom_limit = page_height - margin
        pages = []
        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        def draw_header(draw, y):
            x = margin
            for idx, col in enumerate(columns):
                width = widths[idx]
                draw.rectangle([x, y, x + width, y + header_h], outline="black", width=1)
                ty = y + pad
                for line in header_lines[idx]:
                    draw.text((x + pad, ty), line, fill="black", font=header_font)
                    ty += header_line_h
                x += width
            return y + header_h

        def new_page():
            img = Image.new("RGB", (page_width, page_height), "white")
            draw = ImageDraw.Draw(img)
            draw.text((page_width // 2, margin - 25), print_title, fill="black", font=title_font, anchor="mm")
            time_text = f"打印时间: {generated_at}"
            draw.text((margin, margin + 20), time_text, fill="black", font=meta_font)
            if print_remark:
                remark_text = f"备注: {print_remark}"
                max_remark_width = max(80, (page_width - margin * 2) // 2)
                remark_text = self._fit_print_text(draw, remark_text, meta_font, max_remark_width)
                draw.text((page_width - margin, margin + 20), remark_text, fill="black", font=meta_font, anchor="ra")
            draw.text((margin, margin + 46), f"记录数: {len(rows)}", fill="black", font=meta_font)
            y = draw_header(draw, margin + 82)
            pages.append(img)
            return img, draw, y

        img, draw, y = new_page()
        for row in rows:
            cell_lines = []
            row_h = 30
            for idx, col in enumerate(columns):
                lines = self._wrap_print_text(draw, row.get(col, ""), text_font, widths[idx] - pad * 2)
                cell_lines.append(lines)
                row_h = max(row_h, len(lines) * line_h + pad * 2)

            if y + row_h > bottom_limit:
                img, draw, y = new_page()

            x = margin
            for idx, lines in enumerate(cell_lines):
                width = widths[idx]
                draw.rectangle([x, y, x + width, y + row_h], outline="black", width=1)
                ty = y + pad
                for line in lines:
                    if ty + line_h <= y + row_h:
                        draw.text((x + pad, ty), line, fill="black", font=text_font)
                    ty += line_h
                x += width
            y += row_h

        total_pages = len(pages)
        for idx, page in enumerate(pages, 1):
            footer_draw = ImageDraw.Draw(page)
            footer_draw.text(
                (page_width // 2, page_height - 35),
                f"第 {idx}/{total_pages} 页",
                fill="black",
                font=footer_font,
                anchor="mm"
            )
        return pages

    def _get_printer_names(self):
        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = []
            for item in win32print.EnumPrinters(flags, None, 2):
                name = item.get("pPrinterName") if isinstance(item, dict) else item[2]
                if name and name not in printers:
                    printers.append(name)
            if not printers:
                default_printer = win32print.GetDefaultPrinter()
                if default_printer:
                    printers.append(default_printer)
            return printers
        except Exception:
            return []

    def _send_print_pages(self, pages, printer_name, document_name="数据查询打印明细"):
        if not pages:
            raise RuntimeError("没有可打印的页面。")
        printer_name = (printer_name or "").strip()
        document_name = (document_name or "数据查询打印明细").strip() or "数据查询打印明细"
        if not printer_name:
            raise RuntimeError("请先选择打印机。")
        import win32print
        import win32ui
        import win32con
        from PIL import ImageWin

        hdc = win32ui.CreateDC()
        started = False
        try:
            hdc.CreatePrinterDC(printer_name)
            horzres = getattr(win32con, "HORZRES", 8)
            vertres = getattr(win32con, "VERTRES", 10)
            printable_width = hdc.GetDeviceCaps(horzres)
            printable_height = hdc.GetDeviceCaps(vertres)
            hdc.StartDoc(document_name)
            started = True
            for page in pages:
                hdc.StartPage()
                page = page.convert("RGB")
                scale = min(printable_width / page.width, printable_height / page.height)
                target_width = int(page.width * scale)
                target_height = int(page.height * scale)
                left = max(0, (printable_width - target_width) // 2)
                top = max(0, (printable_height - target_height) // 2)
                dib = ImageWin.Dib(page)
                dib.draw(hdc.GetHandleOutput(), (left, top, left + target_width, top + target_height))
                hdc.EndPage()
            hdc.EndDoc()
        except Exception:
            if started:
                try:
                    hdc.AbortDoc()
                except Exception:
                    pass
            raise
        finally:
            try:
                hdc.DeleteDC()
            except Exception:
                pass

    def on_q(self, event=None):
        q = self.cb.get()
        if q in ["全部库存", "按商品统计盈亏", "按货商统计盈亏", "按货商的入库次数"]:
            self.ent_cond.delete(0, tk.END)
            self.ent_cond.config(state="disabled")
            self.lbl_cond.config(text="查询条件:")
        else:
            self.ent_cond.config(state="normal")
            self.lbl_cond.config(text="快递单号:")

    def exec_q(self):
        q = self.cb.get()
        c = self.ent_cond.get().strip()
        if q == "全部库存":
            self.controller.view_all_inventory_unified()
        elif q == "按商品统计盈亏":
            self.controller.view_profit_by_product_unified()
        elif q == "按货商统计盈亏":
            self.controller.view_profit_by_supplier_unified()
        elif q == "按货商的入库次数":
            self.controller.view_inbound_count_by_supplier_unified()
        else:
            self.controller.view_by_tracking_number_unified(c)

    def display_results(self, cols, data):
        # 保存所有列和原始数据
        self.all_columns = list(cols)
        self.orig = [dict(zip(cols, row)) for row in data]
        # 计算利润
        for d in self.orig:
            try:
                p = float(d.get("行情价格","0") or 0) - float(d.get("结算价","0") or 0)
                d["利润"] = f"{p:.2f}"
            except:
                d["利润"] = ""
        self.full = list(self.orig)

        # 从设置中获取要显示的列
        display_cols = self.controller.settings_model.get_display_columns('data_query')
        if not display_cols:
            # 如果没有配置，使用所有列
            display_cols = self.all_columns
        
        # 只保留存在的列
        self.columns = [col for col in display_cols if col in self.all_columns]
        if not self.columns:
            self.columns = self.all_columns

        # 默认按照入库时间降序排列
        if '入库时间' in self.all_columns:
            self.full.sort(key=lambda d: self._parse_datetime(
                d.get('入库时间', '0000-01-01 00:00:00')
            ), reverse=True)

        # 重建表头
        self.sort_states = {c: True for c in self.columns}
        self._configure_tree_columns()
        self._redraw_tree_rows(preserve_selection=False)

        # 重建筛选区
        self.create_filter_row()

        # 更新指标
        self.update_metrics()
        self.update_invoice_button_state()
    
    def refresh_columns(self):
        """刷新表格列显示配置"""
        if not hasattr(self, 'all_columns') or not self.all_columns:
            return
        
        # 从设置中获取要显示的列
        display_cols = self.controller.settings_model.get_display_columns('data_query')
        if not display_cols:
            display_cols = self.all_columns
        
        # 只保留存在的列
        self.columns = [col for col in display_cols if col in self.all_columns]
        if not self.columns:
            self.columns = self.all_columns
        
        # 重建表头
        self.sort_states = {c: True for c in self.columns}
        self._configure_tree_columns()
        self._redraw_tree_rows()
        
        # 重建筛选区
        self.create_filter_row()
        
        # 更新指标
        self.update_metrics()

    def update_current_data(self, cols, data):
        # 保留当前筛选条件，只替换数据
        self.all_columns = list(cols)
        self.orig = [dict(zip(cols, row)) for row in data]
        for d in self.orig:
            try:
                p = float(d.get("行情价格","0") or 0) - float(d.get("结算价","0") or 0)
                d["利润"] = f"{p:.2f}"
            except:
                d["利润"] = ""
        self.full = list(self.orig)
        display_cols = self.controller.settings_model.get_display_columns('data_query')
        if not display_cols:
            display_cols = self.all_columns
        self.columns = [col for col in display_cols if col in self.all_columns]
        if not self.columns:
            self.columns = self.all_columns
        # 默认按入库时间降序
        if '入库时间' in self.all_columns:
            self.full.sort(key=lambda d: self._parse_datetime(
                d.get('入库时间', '0000-01-01 00:00:00')
            ), reverse=True)
        self._configure_tree_columns()
        # 重新应用筛选条件
        self.apply_filters()

    def apply_filters(self):
        filtered = []
        for d in self.orig:
            ok = True
            for c, e in self.filter_entries.items():
                v = e.get().strip().lower()
                if v and v not in str(d.get(c,"")).lower():
                    ok = False
                    break
            if ok:
                filtered.append(d)
        self.full = filtered
        self._redraw_tree_rows()
        self.update_metrics()
        self.update_invoice_button_state()

    def clear_filters(self):
        for e in self.filter_entries.values():
            e.delete(0, tk.END)
        self.apply_filters()

    def sort_by(self, col):
        asc = self.sort_states.get(col, True)
        try:
            self.full.sort(key=lambda x: float(x.get(col,"") or 0), reverse=not asc)
        except:
            self.full.sort(key=lambda x: x.get(col,""), reverse=not asc)
        self.sort_states[col] = not asc
        self._redraw_tree_rows()

    def _parse_datetime(self, date_str):
        """解析多种格式的日期字符串"""
        formats = [
            "%Y-%m-%d %H:%M:%S",  # 带秒的完整格式
            "%Y-%m-%d %H:%M",     # 不带秒的格式
            "%Y-%m-%d"           # 只有日期的格式
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # 如果所有格式都失败，返回一个很早的日期作为默认值
        return datetime(1900, 1, 1)
    
    def update_invoice_button_state(self):
        try:
            selected_iids = list(self.tree.selection())
            if selected_iids:
                selected_data = [self.row_items[i] for i in selected_iids if i in self.row_items]
            else:
                selected_data = list(self.full) if hasattr(self, 'full') else []
            if not selected_data:
                self.btn_invoice.state(["disabled"]) 
                return
            suppliers = {d.get('货商姓名','').strip() for d in selected_data if d.get('货商姓名','').strip()}
            if len(suppliers) == 1:
                self.btn_invoice.state(["!disabled"]) 
            else:
                self.btn_invoice.state(["disabled"]) 
        except Exception:
            self.btn_invoice.state(["disabled"]) 

    def generate_invoice(self):
        import uuid
        from datetime import datetime as _dt
        maker = self.controller.settings_model.get_document_maker_default()
        today = _dt.now().strftime('%Y-%m-%d')
        code = 'JHD' + _dt.now().strftime('%Y%m%d') + uuid.uuid4().hex[:6]

        selected_iids = list(self.tree.selection())
        data_src = [self.row_items[i] for i in selected_iids if i in self.row_items] if selected_iids else list(self.full)
        items = []
        total_amount = 0.0
        total_qty = 0
        for i, d in enumerate(data_src, 1):
            name = d.get('商品名称','')
            courier_no = d.get('入库快递单号','')
            try:
                qty = int(d.get('商品数量','') or 0)
            except:
                qty = 0
            try:
                buy_price = float(d.get('买价','') or 0)
            except:
                buy_price = 0.0
            try:
                commission = float(d.get('佣金','') or 0)
            except:
                commission = 0.0
            try:
                settle_price = float(d.get('结算价','') or (buy_price + commission))
            except:
                settle_price = buy_price + commission
            total_amount += settle_price
            total_qty += qty
            items.append((i, courier_no, name, qty, buy_price, commission, settle_price, d.get('备注','')))

        try:
            from PIL import Image, ImageDraw, ImageFont, ImageTk
            import tkinter as tk
            def _font(sz):
                paths = [
                    r"C:\Windows\Fonts\msyh.ttc",
                    r"C:\Windows\Fonts\msyh.ttf",
                    r"C:\Windows\Fonts\simhei.ttf",
                    r"C:\Windows\Fonts\simsun.ttc",
                    r"C:\Windows\Fonts\simsun.ttf",
                    r"C:\Windows\Fonts\Microsoft YaHei UI.ttf",
                ]
                for p in paths:
                    try:
                        return ImageFont.truetype(p, sz)
                    except Exception:
                        continue
                return ImageFont.load_default()
            # 先计算内容行数与基准区域
            width = 800
            title_font = _font(24)
            text_font = _font(14)
            small_font = _font(12)
            supplier = next((d.get('货商姓名','') for d in data_src if d.get('货商姓名','')), '')
            left = 20
            right_base = 780
            top = 120
            header_h = 30
            row_h = 28
            rows = max(len(items), 1)
            dynamic_h = max(600, top + header_h + row_h * rows + 120)
            # 列：序号 | 入库快递单号 | 商品名称 | 数量 | 买价 | 佣金 | 结算价 | 备注（动态列宽）
            cols = ['序号','入库快递单号','商品名称','数量','买价','佣金','结算价','备注']
            # 计算内容最大宽度
            temp_draw = ImageDraw.Draw(Image.new('RGB', (1,1)))
            def w(text, font):
                try:
                    box = temp_draw.textbbox((0,0), str(text), font=font)
                    return box[2]-box[0]
                except Exception:
                    return len(str(text))*10
            maxw = {
                '序号': w('序号', small_font),
                '入库快递单号': w('入库快递单号', small_font),
                '商品名称': w('商品名称', small_font),
                '数量': w('数量', small_font),
                '买价': w('买价', small_font),
                '佣金': w('佣金', small_font),
                '结算价': w('结算价', small_font),
                '备注': w('备注', small_font),
            }
            for row in items:
                maxw['序号'] = max(maxw['序号'], w(row[0], small_font))
                maxw['入库快递单号'] = max(maxw['入库快递单号'], w(row[1], small_font))
                maxw['商品名称'] = max(maxw['商品名称'], w(row[2], small_font))
                maxw['数量'] = max(maxw['数量'], w(row[3], small_font))
                maxw['买价'] = max(maxw['买价'], w(row[4], small_font))
                maxw['佣金'] = max(maxw['佣金'], w(row[5], small_font))
                maxw['结算价'] = max(maxw['结算价'], w(row[6], small_font))
                maxw['备注'] = max(maxw['备注'], w(row[7], small_font))
            # 基础最小/最大宽度与内边距
            pad = 16
            limits = {
                '序号': (60, 100),
                '入库快递单号': (120, 260),
                '商品名称': (220, 360),
                '数量': (70, 100),
                '买价': (90, 130),
                '佣金': (90, 130),
                '结算价': (100, 140),
                '备注': (160, 380),
            }
            # 初算宽度
            widths = {k: max(limits[k][0], min(maxw[k]+pad, limits[k][1])) for k in maxw}
            total = sum(widths.values())
            available = right_base - left
            # 调整：所有列参与缩放（保证不小于最小宽度、不超过最大宽度）
            if total > available:
                over = total - available
                order = ['备注','商品名称','入库快递单号','结算价','买价','佣金','数量','序号']
                idx = 0
                while over > 0 and idx < len(order):
                    key = order[idx]
                    reducible = widths[key] - limits[key][0]
                    if reducible > 0:
                        delta = min(reducible, max(1, over // (len(order) - idx)))
                        widths[key] -= delta
                        over -= delta
                    idx += 1
                # 如果仍有剩余，继续从第一列轮询直到消除
                while over > 0:
                    done = True
                    for key in order:
                        reducible = widths[key] - limits[key][0]
                        if reducible > 0 and over > 0:
                            widths[key] -= 1
                            over -= 1
                            done = False
                    if done:
                        break
            elif total < available:
                remain = available - total
                order = ['备注','商品名称','入库快递单号','结算价','买价','佣金','数量','序号']
                idx = 0
                while remain > 0 and idx < len(order):
                    key = order[idx]
                    expandable = limits[key][1] - widths[key]
                    if expandable > 0:
                        delta = min(expandable, max(1, remain // (len(order) - idx)))
                        widths[key] += delta
                        remain -= delta
                    idx += 1
                while remain > 0:
                    done = True
                    for key in order:
                        expandable = limits[key][1] - widths[key]
                        if expandable > 0 and remain > 0:
                            widths[key] += 1
                            remain -= 1
                            done = False
                    if done:
                        break
            # 生成列边界
            bounds = [left]
            for key in ['序号','入库快递单号','商品名称','数量','买价','佣金','结算价','备注']:
                bounds.append(bounds[-1] + widths[key])
            calc_right = bounds[-1]
            # 如果总宽超出基准，则扩展图片宽度，确保不截断
            width = max(width, calc_right + 20)
            right = width - 20
            img = Image.new('RGB', (width, dynamic_h), 'white')
            draw = ImageDraw.Draw(img)
            # 标题居中，日期与编号右对齐（根据宽度动态计算）
            title  = self.controller.settings_model.get_document_title_default()
            prefix = self.controller.settings_model.get_document_code_prefix_default().upper()
            code   = (prefix + _dt.now().strftime('%Y%m%d') + uuid.uuid4().hex[:6]).upper()
            draw.text((width//2, 20), title, fill='black', font=title_font, anchor='mm')
            draw.text((40, 60), f'供应商: {supplier}', fill='black', font=text_font)
            def _tw(s, f):
                try:
                    return draw.textbbox((0,0), s, font=f)[2]
                except Exception:
                    return len(s)*10
            right_x = width - 40
            date_str = f'单据日期: {today}'
            code_str = f'单据编号: {code}'
            draw.text((right_x - _tw(date_str, text_font), 60), date_str, fill='black', font=text_font)
            draw.text((right_x - _tw(code_str, text_font), 85), code_str, fill='black', font=text_font)
            # 绘制外框与列线
            draw.rectangle([left, top, calc_right, top + header_h + row_h * rows], outline='black', width=1)
            for j in range(len(bounds)-1):
                draw.line([(bounds[j], top), (bounds[j], top + header_h + row_h * rows)], fill='black', width=1)
            draw.line([(left, top + header_h), (calc_right, top + header_h)], fill='black', width=1)
            # 绘制表头
            for j, c in enumerate(cols):
                draw.text((bounds[j] + 6, top + 6), c, fill='black', font=small_font)
            y = top + header_h
            for row in items:
                y += 1
                draw.line([(left, y + row_h), (calc_right, y + row_h)], fill='black', width=1)
                for j, val in enumerate(row):
                    draw.text((bounds[j] + 6, y + 6), str(val), fill='black', font=small_font)
                y += row_h
            draw.text((left, y + 10), f'合计 数量: {total_qty}', fill='black', font=text_font)
            draw.text((left + 260, y + 10), f'合计金额: {total_amount:.2f}', fill='black', font=text_font)
            draw.text((left, y + 40), f'制单人: {maker}', fill='black', font=text_font)
            win = tk.Toplevel(self)
            win.title('票据预览')
            win.geometry(f'{width+20}x{dynamic_h+140}')
            tk_img = ImageTk.PhotoImage(img)
            lbl = tk.Label(win, image=tk_img)
            lbl.image = tk_img
            lbl.pack(padx=10, pady=10)
            btns = tk.Frame(win)
            btns.pack(pady=5)
            def save_as(ext):
                from tkinter import filedialog
                path = filedialog.asksaveasfilename(defaultextension=f'.{ext}', filetypes=[(ext.upper(), f'*.{ext}')])
                if path:
                    img.save(path)
            tk.Button(btns, text='保存PNG', command=lambda: save_as('png')).pack(side='left', padx=5)
            tk.Button(btns, text='保存JPG', command=lambda: save_as('jpg')).pack(side='left', padx=5)
            def copy_clipboard():
                try:
                    # 优先使用 pywin32（更稳定）
                    import io
                    from PIL import Image
                    import win32clipboard, win32con
                    output = io.BytesIO()
                    img.convert('RGB').save(output, 'BMP')
                    data = output.getvalue()[14:]
                    output.close()
                    win32clipboard.OpenClipboard()
                    win32clipboard.EmptyClipboard()
                    win32clipboard.SetClipboardData(win32con.CF_DIB, data)
                    win32clipboard.CloseClipboard()
                except Exception:
                    # 回退到 ctypes 实现
                    try:
                        import ctypes, io
                        output = io.BytesIO()
                        img.convert('RGB').save(output, 'BMP')
                        data = output.getvalue()[14:]
                        output.close()
                        CF_DIB = 8
                        GMEM_MOVEABLE = 0x0002
                        user32 = ctypes.windll.user32
                        kernel32 = ctypes.windll.kernel32
                        hGlobal = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                        pGlobal = kernel32.GlobalLock(hGlobal)
                        ctypes.memmove(pGlobal, data, len(data))
                        kernel32.GlobalUnlock(hGlobal)
                        user32.OpenClipboard(0)
                        user32.EmptyClipboard()
                        user32.SetClipboardData(CF_DIB, hGlobal)
                        user32.CloseClipboard()
                    except Exception:
                        pass
            tk.Button(btns, text='复制到剪贴板', command=copy_clipboard).pack(side='left', padx=5)
        except Exception:
            import tkinter as tk
            from tkinter import messagebox
            messagebox.showerror('错误', '未安装Pillow或系统缺少中文字体，无法生成票据图片')
        
    def update_metrics(self):
        sold_profit = settled_profit = inventory_value = shipping_cost = commission_cost = unsettled_amount = 0.0
        total_market = total_qty = 0.0
        for d in self.full:
            try: commission_cost += float(d.get('佣金','0') or 0)
            except: pass
            try: cost = float(d.get('结算价','0') or 0)
            except: cost = 0.0
            try: sale = float(d.get('行情价格','0') or 0)
            except: sale = 0.0
            try: ship = float(d.get('快递价格','0') or 0)
            except: ship = 0.0
            status = d.get('出库状态','')
            # 卖出总利润：当前页（筛选后）数据的 行情价格-结算价-快递价格
            sold_profit += (sale - cost - ship)
            shipping_cost += ship
            # 已出库已结算总利润：仅“全部出库”的商品
            if status == '全部出库':
                settled_profit += (sale - cost - ship)
            else:
                try: inventory_value += cost
                except: pass
            if d.get('结算状态') == '否':
                try: unsettled_amount += float(d.get('结算价','0') or 0)
                except: pass
            try: total_market += float(d.get('行情价格','0') or 0)
            except: pass
            try: total_qty    += float(d.get('商品数量','0') or 0)
            except: pass

        self.lbl_sold_profit     .config(text=f"卖出总利润: {sold_profit:.2f}")
        self.lbl_settled_profit  .config(text=f"已出库已结算总利润: {settled_profit:.2f}")
        self.lbl_inventory_value .config(text=f"库存价值: {inventory_value:.2f}")
        self.lbl_shipping_cost   .config(text=f"快递总费用: {shipping_cost:.2f}")
        self.lbl_commission_cost .config(text=f"佣金总费用: {commission_cost:.2f}")
        self.lbl_unsettled_amount.config(text=f"未结清金额: {unsettled_amount:.2f}")
        self.lbl_total_market    .config(text=f"行情价总和: {total_market:.2f}")
        self.lbl_total_rows      .config(text=f"总条数: {len(self.full)}")
        self.lbl_total_qty       .config(text=f"商品数量总和: {total_qty:.2f}")

    def on_tree_double_click(self, event):
        """处理表格双击事件"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        # 获取点击的列
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        
        col_name = self._identify_tree_column_name(event.x)
        
        # 只有点击出库记录列才弹出详细窗口
        if col_name == "出库记录":
            record_data = self.row_items.get(item)
            if record_data:
                self.show_outbound_details(record_data)
    
    def show_outbound_details(self, record_data):
        """显示出库记录详细窗口"""
        # 创建新窗口
        detail_window = tk.Toplevel(self)
        detail_window.title("出库记录详细")
        detail_window.geometry("600x400")
        detail_window.resizable(True, True)
        
        # 设置窗口图标
        try:
            from gui_view import ICON_BASE64
            icon = tk.PhotoImage(data=ICON_BASE64)
            detail_window.iconphoto(False, icon)
            # 保存引用，避免被垃圾回收
            detail_window._icon = icon
        except Exception as e:
            print("无法设置图标:", e)
        
        # 商品信息标题
        info_frame = ttk.Frame(detail_window)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        product_info = f"商品: {record_data.get('商品名称', '')} | 订单号: {record_data.get('订单号', '')} | 颜色配置: {record_data.get('颜色配置', '')}"
        ttk.Label(info_frame, text=product_info, font=("Arial", 10, "bold")).pack()
        
        # 出库记录表格
        tree_frame = ttk.Frame(detail_window)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # 创建表格
        detail_tree = ttk.Treeview(tree_frame, columns=("时间", "档口", "快递单号", "出库数量", "单价"), show="headings")
        detail_tree.pack(fill="both", expand=True)
        
        # 设置列标题和宽度
        detail_tree.heading("时间", text="出库时间")
        detail_tree.heading("档口", text="出库档口")
        detail_tree.heading("快递单号", text="快递单号")
        detail_tree.heading("出库数量", text="出库数量")
        detail_tree.heading("单价", text="单价")
        
        detail_tree.column("时间", width=150, anchor="center")
        detail_tree.column("档口", width=100, anchor="center")
        detail_tree.column("快递单号", width=120, anchor="center")
        detail_tree.column("出库数量", width=80, anchor="center")
        detail_tree.column("单价", width=80, anchor="center")
        
        # 添加滚动条
        detail_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=detail_tree.yview)
        detail_scrollbar.pack(side="right", fill="y")
        detail_tree.configure(yscrollcommand=detail_scrollbar.set)
        
        # 解析出库记录数据
        outbound_records_str = record_data.get('出库记录', '')
        if outbound_records_str:
            try:
                # 出库记录格式: "时间1|档口1|快递单号1|数量1|单价1;时间2|档口2|快递单号2|数量2|单价2"
                records = outbound_records_str.split(';')
                for record in records:
                    if record.strip():
                        parts = record.split('|')
                        if len(parts) >= 4:
                            time_str = parts[0] if len(parts) > 0 else ""
                            counter = parts[1] if len(parts) > 1 else ""
                            tracking = parts[2] if len(parts) > 2 else ""
                            quantity = parts[3] if len(parts) > 3 else ""
                            unit_price = parts[4] if len(parts) > 4 else ""
                            detail_tree.insert("", tk.END, values=(time_str, counter, tracking, quantity, unit_price))
            except Exception as e:
                # 如果解析失败，显示原始数据
                detail_tree.insert("", tk.END, values=("解析错误", "", "", "", ""))
                detail_tree.insert("", tk.END, values=(outbound_records_str, "", "", "", ""))
        else:
            # 如果没有出库记录，显示提示
            detail_tree.insert("", tk.END, values=("暂无出库记录", "", "", "", ""))
        
        # 关闭按钮
        button_frame = ttk.Frame(detail_window)
        button_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(button_frame, text="关闭", command=detail_window.destroy).pack(side="right")
