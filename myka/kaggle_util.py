import importlib.resources as pkg_resources
import json
import os
import random
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from kaggle.api.kaggle_api_extended import KaggleApi


def init(kaggle_json_path: str) -> None:
    os.makedirs("~/.kaggle", exist_ok=True)
    shutil.copy(kaggle_json_path, "~/.kaggle")
    os.chmod("~/.kaggle/kaggle.json", 0o600)


def date():
    day = datetime.today().day
    month = datetime.today().month
    date = f"{month:02}{day:02}"
    return date


def subprocess_run(command: str) -> None:
    try:
        subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        raise RuntimeError()


def download_comp_datasets(comp_name: str, save_dir: str = "/kaggle/input") -> None:
    subprocess_run(
        f"kaggle competitions download {comp_name} --path {save_dir}/{comp_name}/"
    )

    shutil.unpack_archive(
        f"{save_dir}/{comp_name}/{comp_name}.zip", f"{save_dir}/{comp_name}/"
    )
    os.remove(f"{save_dir}/{comp_name}/{comp_name}.zip")


def download_datasets(dataset_id: str, save_dir: str = "/kaggle/input") -> None:
    dataset_name = dataset_id.split("/")[1]
    subprocess_run(
        f"kaggle datasets download {dataset_id} --unzip --quiet --path {save_dir}/{dataset_name}"
    )


def create_datasets(userid: str, folder: str) -> None:
    title = folder.rstrip("/").split("/")[-1].replace("_", "-")
    print(title)

    with pkg_resources.open_text("myka.template", "dataset-metadata.json") as js:
        dict_json = json.load(js)
    dict_json["title"] = title
    dict_json["id"] = f"{userid}/{title}"

    with open(f"{folder}/dataset-metadata.json", "w") as js:
        json.dump(dict_json, js, indent=4)

    subprocess_run(f"kaggle datasets create -p {folder} --quiet --dir-mode zip")
    os.remove(f"{folder}/dataset-metadata.json")


def pull_kernel(kernel_id: str, save_dir: str = "/kaggle/reference/") -> None:
    os.makedirs(save_dir, exist_ok=True)
    fname = kernel_id.rstrip("/").split("/")[-1]

    subprocess_run(f"kaggle kernels pull {kernel_id} --path /tmp")

    shutil.move(f"/tmp/{fname}.ipynb", f"{save_dir}/{fname}.ipynb")


def push_kernel(
    userid: str,
    path: str,
    datasets: list[str | None] = [],
    comp: str = "",
    random_suffix: bool = True,
) -> None:
    shutil.copy(path, "/tmp/tmp.ipynb")
    fname = Path(path)
    rand = random.randint(1000, 9999) if random_suffix else ""

    with pkg_resources.open_text("myka.template", "kernel-metadata.json") as js:
        dict_json = json.load(js)

    dict_json["id"] = f"{userid}/{fname.stem}{rand}"
    dict_json["title"] = f"{fname.stem}{rand}"
    dict_json["code_file"] = str(fname)
    dict_json["competition_sources"] = comp
    dict_json["dataset_sources"] = datasets

    os.chdir("/tmp")
    with open("/tmp/kernel-metadata.json", "w") as js:
        json.dump(dict_json, js, indent=4)
    subprocess_run("kaggle kernels push")
    os.remove("/tmp/kernel-metadata.json")


def pull_model(url: str, save_dir: str = "/kaggle/input/") -> None:
    owner = url.split("/")[4].lower()
    model_slug = url.split("/")[5].lower()
    framework = url.split("/")[7].lower()
    instance_slug = url.split("/")[9].lower()
    version_number = url.split("/")[11].lower()

    model = f"{owner}/{model_slug}/{framework}/{instance_slug}/{version_number}"
    print(model)

    save_path = f"{save_dir}/{model}"
    print(save_path)

    subprocess_run(
        f"kaggle models instances versions download {model} --untar -p {save_path}"
    )


def submission(comp_name: str, file_path: str, message: str = "submission") -> None:
    subprocess_run(
        f"kaggle competitions submit {comp_name} -f {file_path} -m {message}"
    )


def measure_submission_elapsed(competition: str, idx: str = 0) -> None:
    api = KaggleApi()
    api.authenticate()

    result_ = api.competition_submissions(competition)[idx]
    latest_ref = str(result_)  # 最新のサブミット番号
    submit_time = result_.date
    description = result_.description
    print(f"submission description: {description}")

    status = ""
    while status != "complete":
        list_of_submission = api.competition_submissions(competition)
        for result in list_of_submission:
            if str(result.ref) == latest_ref:
                break
        status = result.status

        now = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_time = int((now - submit_time).seconds / 60) + 1
        if status == "complete":
            print("\r" f"run-time: {elapsed_time} min, LB: {result.publicScore}")
        else:
            print("\r", f"elapsed time: {elapsed_time} min", end="")
            time.sleep(60)
