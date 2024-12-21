
import os

class File:
    __filename = None
    __mtime = None
    __size = None

    def __init__(self, fullpath):
        self.fullpath = fullpath

    def get_filename(self):
        if self.__filename is None:
            self.__filename = os.path.basename(self.fullpath)
        return self.__filename

    def get_mtime(self):
        if self.__mtime is None:
            self.__mtime = os.path.getmtime(self.fullpath)
        return self.__mtime

    def get_size(self):
        if self.__size is None:
            self.__size = os.path.getsize(self.fullpath)
        return self.__size
