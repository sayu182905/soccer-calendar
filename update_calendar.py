"""TimeTree公開カレンダーを iCal (.ics) にエクスポートするラッパー。

timetree-exporter の公開カレンダーモード（ログイン不要）を使い、
soccer.ics を更新する。

保護処理:
- まず一時ファイルに出力し、検証を通った場合のみ soccer.ics を置き換える
- エクスポート失敗・出力が空・イベントが1件も無い場合は既存ファイルを保持する
  （iPhone側の照会カレンダーが消えないようにするため）
- DTSTAMP（実行のたびに変わる生成時刻）を無視して前回分と比較し、
  予定に実質的な変更がある場合のみ置き換える
  （毎日コミットが発生するのを防ぎ、実変更のあった日だけ履歴に残す）
- 非公式APIのためリトライは最小限（計2回まで）
"""

import subprocess
import sys
import time
from pathlib import Path

CALENDAR_ID = "minohminamijfc"
OUTPUT = Path(__file__).resolve().parent / "soccer.ics"
TMP = OUTPUT.with_suffix(".ics.tmp")
MAX_ATTEMPTS = 2
RETRY_WAIT_SECONDS = 60
EXPORT_TIMEOUT_SECONDS = 300


def export_to(path: Path) -> bool:
    """timetree-exporter を1回実行する。成功なら True。"""
    cmd = [
        "timetree-exporter",
        "--public-calendar",
        "-c", CALENDAR_ID,
        "-o", str(path),
    ]
    print(f"実行: {' '.join(cmd)}", flush=True)
    try:
        result = subprocess.run(cmd, timeout=EXPORT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        print(f"エクスポートが{EXPORT_TIMEOUT_SECONDS}秒でタイムアウトしました", file=sys.stderr)
        return False
    if result.returncode != 0:
        print(f"timetree-exporter が終了コード {result.returncode} で失敗しました", file=sys.stderr)
        return False
    return True


def validate(path: Path) -> bool:
    """出力が購読カレンダーとして安全に公開できる内容か検証する。"""
    if not path.is_file() or path.stat().st_size == 0:
        print("検証NG: 出力ファイルが存在しないか空です", file=sys.stderr)
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text:
        print("検証NG: VCALENDARヘッダがありません（iCal形式ではない）", file=sys.stderr)
        return False
    event_count = text.count("BEGIN:VEVENT")
    if event_count == 0:
        # 予定ゼロは API 側の異常の可能性が高いので前回分を保持する
        print("検証NG: イベントが1件も含まれていません", file=sys.stderr)
        return False
    print(f"検証OK: イベント {event_count} 件", flush=True)
    return True


def significant_lines(path: Path) -> list[str]:
    """予定の実質的な内容だけを返す（実行ごとに変わる DTSTAMP 行を除外）。"""
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ln for ln in text.splitlines() if not ln.startswith("DTSTAMP")]


def main() -> int:
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print(f"{RETRY_WAIT_SECONDS}秒待ってリトライします ({attempt}/{MAX_ATTEMPTS})", flush=True)
            time.sleep(RETRY_WAIT_SECONDS)
        if export_to(TMP) and validate(TMP):
            if OUTPUT.is_file() and significant_lines(TMP) == significant_lines(OUTPUT):
                # DTSTAMP以外に変化なし = 予定は変わっていない。既存ファイルを据え置く
                TMP.unlink(missing_ok=True)
                print(f"予定に変更なし。{OUTPUT.name} を据え置きます", flush=True)
                return 0
            TMP.replace(OUTPUT)
            print(f"{OUTPUT.name} を更新しました", flush=True)
            return 0
        TMP.unlink(missing_ok=True)
    print(f"エクスポートに失敗しました。既存の {OUTPUT.name} を保持します", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
