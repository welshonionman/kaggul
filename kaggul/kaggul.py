import json
import os
import random
import shutil
import subprocess
from pathlib import Path


def init(kaggle_json_path: str) -> None:
    """各関数を使うための前準備を行います。

    kaggleから取得したkaggle.jsonを~/.kaggleにコピーし、権限を600に設定します。
    kaggle.jsonを~/.kaggleにコピーし、権限を600に設定します。

    Args:
        kaggle_json_path (str): kaggle.jsonのパス

    """
    kaggle_dir = os.path.expanduser("~/.kaggle")
    os.makedirs(kaggle_dir, exist_ok=True)
    shutil.copy(kaggle_json_path, kaggle_dir)
    os.chmod(f"{kaggle_dir}/kaggle.json", 0o600)


def __subprocess_run(command: str) -> None:
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        raise RuntimeError() from e


def download_comp_datasets(comp_name: str, save_dir: str = "/kaggle/input") -> None:
    """指定したコンペティションのデータセットをダウンロードします。

    データセットはzipファイルでダウンロード後に解凍して格納されます。
    comp_nameはコンペティションのURLの末尾にある文字列です。

    Args:
        comp_name (str): コンペティション名
        save_dir (str): 保存先ディレクトリ (default: /kaggle/input)

    """

    __subprocess_run(
        f"kaggle competitions download '{comp_name}' --path '{save_dir}/{comp_name}/'"
    )

    shutil.unpack_archive(
        f"{save_dir}/{comp_name}/{comp_name}.zip", f"{save_dir}/{comp_name}/"
    )
    os.remove(f"{save_dir}/{comp_name}/{comp_name}.zip")


def download_datasets(dataset_id: str, save_dir: str = "/kaggle/input") -> None:
    """kaggle datasetをダウンロードします。

    dataset_idは<owner>/<dataset-name>の形式で指定します。
    <owner>/<dataset-name>はダウンロードしたいデータセットのURLの末尾にある文字列です。

    Args:
        dataset_id (str): データセットID
        save_dir (str): 保存先ディレクトリ (default: /kaggle/input)

    """
    dataset_name = dataset_id.split("/")[1]
    __subprocess_run(
        f"kaggle datasets download '{dataset_id}' --unzip --quiet --path '{save_dir}/{dataset_name}'"
    )


def create_datasets(userid: str, folder: str, title: str | None = None) -> None:
    """kaggle datasetを作成します。データセットはprivateの状態で作成されます。

    バージョンの更新については未対応です。

    Args:
        userid (str): kaggle ID
        folder (str): データセットのディレクトリ
        title (str | None): データセットのタイトル。指定しない場合はfolderの末尾のディレクトリ名がタイトルとして使用されます。
                           ディレクトリ名のアンダースコア(_)はハイフン(-)に置換されます。(default: None)
    """
    if title is None:
        title = folder.rstrip("/").split("/")[-1].replace("_", "-")
    print(title)

    metadata_dict = {}
    metadata_dict["licenses"] = [{"name": "CC0-1.0"}]
    metadata_dict["title"] = title
    metadata_dict["id"] = f"{userid}/{title}"

    with open(f"{folder}/dataset-metadata.json", "w") as js:
        json.dump(metadata_dict, js, indent=4)

    __subprocess_run(f"kaggle datasets create -p '{folder}' --quiet --dir-mode zip")
    os.remove(f"{folder}/dataset-metadata.json")


def pull_notebook(kernel_id: str, save_dir: str = "/kaggle/reference/") -> None:
    """public notebookをダウンロードします。

    kernel_idは<owner>/<kernel-name>の形式で指定します。
    <owner>/<kernel-name>はダウンロードしたいnotebookのURLの末尾にある文字列です。

    Args:
        kernel_id (str): notebookのID <owner>/<kernel-name>
        save_dir (str): 保存先ディレクトリ (default: /kaggle/reference)

    """
    os.makedirs(save_dir, exist_ok=True)
    kernel_name = kernel_id.rstrip("/").split("/")[-1]

    __subprocess_run(f"kaggle kernels pull '{kernel_id}' --path /tmp")

    shutil.move(f"/tmp/{kernel_name}.ipynb", f"{save_dir}/{kernel_name}.ipynb")


def push_notebook(
    userid: str,
    notebook_path: str,
    datasets: list[str | None] = [],
    comp: str = "",
    random_suffix: bool = True,
) -> None:
    """notebookをkaggleにprivateの状態でプッシュします。

    datasetsにはnotebookにアタッチするデータセットのリストを指定します。
    datasetsの要素は<owner>/<dataset-name>の形式で指定します。
    <owner>/<dataset-name>はアタッチしたいデータセットのURLの末尾にある文字列です。

    compにはコンペティション名を指定します。
    random_suffixにはランダムなサフィックス（notebookファイル名の末尾に付加）をつけるかどうかを指定します。

    Args:
        userid (str): kaggle ID
        notebook_path (str): notebookのパス
        datasets (list[str | None]): データセットのリスト [<owner>/<dataset-name>, ...]
        comp (str): コンペティション名
        random_suffix (bool): ランダムなサフィックスをつけるかどうか

    """
    shutil.copy(notebook_path, "/tmp/tmp.ipynb")
    fname = Path(notebook_path)
    rand = random.randint(1000, 9999) if random_suffix else ""

    metadata_dict = {}
    metadata_dict["id"] = f"{userid}/{fname.stem}{rand}"
    metadata_dict["title"] = f"{fname.stem}{rand}"
    metadata_dict["code_file"] = str(fname)
    metadata_dict["language"] = "python"
    metadata_dict["kernel_type"] = "notebook"
    metadata_dict["is_private"] = "true"
    metadata_dict["enable_gpu"] = "true"
    metadata_dict["enable_internet"] = "false"
    metadata_dict["dataset_sources"] = datasets
    metadata_dict["competition_sources"] = comp
    metadata_dict["kernel_sources"] = []

    os.chdir("/tmp")
    with open("/tmp/kernel-metadata.json", "w") as js:
        json.dump(metadata_dict, js, indent=4)
    __subprocess_run("kaggle kernels push")
    os.remove("/tmp/kernel-metadata.json")


def pull_model(url: str, save_dir: str = "/kaggle/input/") -> None:
    """kaggle modelをダウンロードします。

    Args:
        url (str): モデルのURL
        save_dir (str): モデルの保存先ディレクトリ (default: /kaggle/input)

    """

    owner = url.split("/")[4].lower()
    model_slug = url.split("/")[5].lower()
    framework = url.split("/")[7].lower()
    instance_slug = url.split("/")[9].lower()
    version_number = url.split("/")[11].lower()

    model = f"{owner}/{model_slug}/{framework}/{instance_slug}/{version_number}"
    print(model)

    save_path = f"{save_dir}/{model}"
    print(save_path)

    __subprocess_run(
        f"kaggle models instances versions download '{model}' --untar -p '{save_path}'"
    )


def submission(comp_name: str, file_path: str, description: str = "submission") -> None:
    """csv submission competitionでcsvファイルを提出します。

    code competitionでは使用できません。

    Args:
        comp_name (str): コンペティション名
        file_path (str): 提出ファイルのパス
        description (str): 提出ファイルの説明 (default: "submission")

    """
    __subprocess_run(
        f"kaggle competitions submit '{comp_name}' -f '{file_path}' -m '{description}'"
    )
