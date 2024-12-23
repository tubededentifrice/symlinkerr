import os


class File:
    __filename: str = None
    __mtime = None
    __size: int = None
    __readlink: str = None

    def __init__(self, fullpath: str):
        self.fullpath = fullpath

    def get_filename(self) -> str:
        if self.__filename is None:
            self.__filename = os.path.basename(self.fullpath)
        return self.__filename

    def get_mtime(self) -> int:
        if self.__mtime is None:
            self.__mtime = round(os.path.getmtime(self.fullpath))
        return self.__mtime

    def get_size(self) -> int:
        if self.__size is None:
            self.__size = os.path.getsize(self.fullpath)
        return self.__size

    def get_readlink(self) -> str:
        if self.__readlink is None:
            self.__readlink = os.readlink(self.fullpath)
        return self.__readlink

    def is_link(self) -> bool:
        return os.path.islink(self.fullpath)

    def is_file(self) -> bool:
        return os.path.isfile(self.fullpath)

    def remove(self) -> None:
        if self.is_file():
            return os.remove(self.fullpath)
