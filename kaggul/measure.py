import time
from datetime import datetime, timezone

from kaggle.api.kaggle_api_extended import KaggleApi


def submission_elapsed(competition: str, idx: str = 0) -> None:
    """サブミットを行った時からの経過時間を計測します。

    idxには最新のサブミットから数えて何番目のサブミットかを指定します。
    idx = 0(default)の場合は最新のサブミットを指定します。

    Args:
        competition (str): コンペティション名
        idx (str): サブミット番号 (default: 0)

    Note:
        ~/.kaggle/kaggle.json が存在しない状態で実行するとエラーが発生します。

        kaggul.init() を実行して kaggle.json を ~/.kaggle に配置してから実行してください。

    References:
        ref: https://zenn.dev/currypurin/scraps/47d5f84a0ca89d
    """

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

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        elapsed_time = int((now - submit_time).seconds / 60) + 1
        if status == "complete":
            print("\r" f"run-time: {elapsed_time} min, LB: {result.publicScore}")
        else:
            print("\r", f"elapsed time: {elapsed_time} min", end="")
            time.sleep(60)
