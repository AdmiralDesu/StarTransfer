import requests
import shutil


# url = "http://localhost:3560/test_upload"
# files = {'file': open(r"C:\Users\Saint\OneDrive\Desktop\test_multi.7z", 'rb')}
# res = requests.post(url, files=files)

def download_file(url):
    local_filename = "test.zip"
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
    return local_filename


download_file(url="http://localhost:3560/download_file?md5_hash=a177425fd01c9be358cd820f310214f3")

