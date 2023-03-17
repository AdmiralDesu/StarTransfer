import pathlib

from config import config
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import magic

magic_type = magic.Magic(mime=True)


def upload_file(
        file_path: pathlib.Path,
        folder_id: int
):
    mime_type = magic_type.from_file(str(file_path))
    print(file_path.parts[-1])
    print(mime_type)
    files = {
        "file": (
            file_path.parts[-1],
            open(f"{file_path}", "rb"),
            mime_type
        )
    }
    resp = requests.post(
        url=f"http://localhost:3561/file/upload_file_to_folder?folder_id={folder_id}",
        files=files
    )
    if resp.ok:
        return file_path.parts[-1]
    return Exception(f"Ошибка при закачке файла\n{resp.text}")


def main(
        dir_path: str,
        folder_id: int
):
    file_pathes = [
        pathlib.Path(os.path.join(dir_path, file)) for file in
        os.listdir(dir_path)
        if os.path.isfile(os.path.join(dir_path, file))
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        tasks = {
            executor.submit(upload_file, file_path, folder_id): file_path for file_path in file_pathes
        }
        for future in as_completed(tasks):
            try:
                result = future.result()
                print(result)
            except Exception as error:
                print(error)
            # if isinstance(result, Exception):
            #     raise result


if __name__ == '__main__':
    main(
        dir_path=r"E:\Downloads\Homework 3D\QOC\FF7\Tifa",
        folder_id=8
    )
