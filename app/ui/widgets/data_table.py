"""Reusable data table with sorting, filtering, and pagination."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QPushButton, QLineEdit, QAbstractItemView,
)


class DataTable(QWidget):
    row_double_clicked = Signal(int)   # emits row index
    row_selected = Signal(int)

    def __init__(
        self,
        columns: List[str],
        parent=None,
        searchable: bool = True,
        page_size: int = 50,
    ):
        super().__init__(parent)
        self.columns = columns
        self.page_size = page_size
        self._all_data: List[List] = []
        self._filtered_data: List[List] = []
        self._current_page = 0

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        if searchable:
            search_row = QHBoxLayout()
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Search...")
            self.search_box.textChanged.connect(self._on_search)
            search_row.addWidget(self.search_box)
            search_row.addStretch()
            self.count_label = QLabel("0 records")
            self.count_label.setStyleSheet("color: #888; font-size: 12px;")
            search_row.addWidget(self.count_label)
            layout.addLayout(search_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.selectionModel().selectionChanged.connect(self._on_selection)
        layout.addWidget(self.table)

        # Pagination
        page_row = QHBoxLayout()
        self.prev_btn = QPushButton("< Prev")
        self.prev_btn.setObjectName("SecondaryBtn")
        self.prev_btn.setFixedWidth(80)
        self.prev_btn.clicked.connect(self._prev_page)
        self.next_btn = QPushButton("Next >")
        self.next_btn.setObjectName("SecondaryBtn")
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self._next_page)
        self.page_label = QLabel("Page 1")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_row.addWidget(self.prev_btn)
        page_row.addWidget(self.page_label)
        page_row.addWidget(self.next_btn)
        page_row.addStretch()
        layout.addLayout(page_row)

    def load_data(self, data: List[List]):
        self._all_data = data
        self._filtered_data = data
        self._current_page = 0
        self._render()

    def _on_search(self, text: str):
        text = text.lower()
        if not text:
            self._filtered_data = self._all_data
        else:
            self._filtered_data = [
                row for row in self._all_data
                if any(text in str(cell).lower() for cell in row)
            ]
        self._current_page = 0
        self._render()

    def _render(self):
        start = self._current_page * self.page_size
        end = start + self.page_size
        page_data = self._filtered_data[start:end]

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(page_data))
        for row_idx, row_data in enumerate(page_data):
            for col_idx, cell in enumerate(row_data):
                item = QTableWidgetItem(str(cell) if cell is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self.table.setItem(row_idx, col_idx, item)
        self.table.setSortingEnabled(True)

        total = len(self._filtered_data)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.page_label.setText(f"Page {self._current_page + 1} / {total_pages}")
        self.prev_btn.setEnabled(self._current_page > 0)
        self.next_btn.setEnabled(end < total)
        if hasattr(self, "count_label"):
            self.count_label.setText(f"{total} records")

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._render()

    def _next_page(self):
        total = len(self._filtered_data)
        if (self._current_page + 1) * self.page_size < total:
            self._current_page += 1
            self._render()

    def _on_double_click(self, index):
        actual_row = self._current_page * self.page_size + index.row()
        self.row_double_clicked.emit(actual_row)

    def _on_selection(self):
        rows = self.table.selectedIndexes()
        if rows:
            actual_row = self._current_page * self.page_size + rows[0].row()
            self.row_selected.emit(actual_row)

    def get_selected_row_data(self) -> Optional[List]:
        rows = self.table.selectedIndexes()
        if not rows:
            return None
        actual_row = self._current_page * self.page_size + rows[0].row()
        if actual_row < len(self._filtered_data):
            return self._filtered_data[actual_row]
        return None

    def clear(self):
        self.table.setRowCount(0)
        self._all_data = []
        self._filtered_data = []
