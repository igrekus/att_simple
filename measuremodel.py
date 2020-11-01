from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant


class MeasureModel(QAbstractTableModel):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)

        self._controller = controller

        self._data = list()
        self._headers = list()

        self._init()

    def _init(self):
        self._initHeader()

    def _initHeader(self):
        self.beginResetModel()
        self._headers = self._controller.result.headers
        self.endResetModel()

    def update(self):
        self._init()
        self.beginResetModel()
        # self._data = self._controller.result.data
        self.endResetModel()

    def headerData(self, section, orientation, role=None):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                if section < len(self._headers):
                    return QVariant(self._headers[section])
        return QVariant()

    def rowCount(self, parent=None, *args, **kwargs):
        if parent.isValid():
            return 0
        return 1

    def columnCount(self, parent=None, *args, **kwargs):
        return len(self._headers)

    def data(self, index, role=None):
        if not index.isValid():
            return QVariant()
        if role == Qt.DisplayRole:
            try:
                return QVariant(self._data[index.column()])
            except LookupError:
                return QVariant()
        return QVariant()
