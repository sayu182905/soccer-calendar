# soccer-calendar

箕面南JFCのTimeTree公開カレンダーを毎日自動でiCal形式（.ics）にエクスポートし、
iPhone標準カレンダーの「照会カレンダー」として購読できるようにするリポジトリ。

- 元データ: [TimeTree公開カレンダー](https://timetr.ee/p/minohminamijfc)（公開カレンダーID: `minohminamijfc`）
- 毎朝 **7:00（JST）** にGitHub Actionsが [timetree-exporter](https://pypi.org/project/timetree-exporter/) で `soccer.ics` を再生成
- 差分がある場合のみコミットされ、下記の購読URLに反映される

## 購読URL

```
https://raw.githubusercontent.com/sayu182905/soccer-calendar/main/soccer.ics
```

## iPhoneでの設定手順（初回のみ）

1. **設定** → **アプリ** → **カレンダー** → **カレンダーアカウント**
2. **アカウントを追加** → **その他**
3. **照会カレンダーを追加** をタップ
4. サーバー欄に上記の購読URLを貼り付けて **次へ** → **保存**

以降はiOSが自動でフェッチするので何もしなくてよい。
購読方式のため毎回フェッチ内容で丸ごと置き換わり、予定が重複することはない。

> フェッチ間隔はiOS側の設定に依存する（設定 → アプリ → カレンダー → カレンダーアカウント → データの取得方法）。
> 朝7時の更新がiPhoneに反映されるまで多少のラグがある。

## 仕組み

```
TimeTree公開カレンダー
   │  timetree-exporter --public-calendar（ログイン不要）
   ▼
update_calendar.py（検証・保護処理付きラッパー）
   │  GitHub Actions（毎日 UTC 22:00 = JST 7:00）
   ▼
soccer.ics（差分がある時のみコミット）
   │  raw.githubusercontent.com
   ▼
iPhone 照会カレンダー
```

### 保護処理（update_calendar.py）

- 一時ファイルに出力し、検証を通った場合のみ `soccer.ics` を置き換える
- エクスポート失敗・出力が空・イベント0件の場合は**既存のファイルを保持**する
  （iPhone側のカレンダーが突然消えるのを防ぐ）
- エクスポート結果は毎回 `DTSTAMP`（生成時刻）が書き換わるため、
  この行を無視して前回分と比較し、**予定に実変更がある日だけ**置き換える
  （毎日無意味なコミットが積み上がるのを防ぐ）
- 非公式APIのためリトライは最小限（60秒間隔で最大2回）

## 手動実行

- **GitHub上で**: Actions タブ → `Update calendar` → `Run workflow`
- **ローカルで**:

  ```bash
  pip install -r requirements.txt
  python update_calendar.py
  ```

  Python 3.10以上が必要。

## 制約・注意

- `timetree-exporter` は非公式ツール（リバースエンジニアリングAPI）のため、
  TimeTree側の仕様変更で突然動かなくなる可能性がある。
  Actionsの実行が失敗し続ける場合はまずここを疑う。
- 公開カレンダーモードではラベル・アラート・繰り返し設定・UUIDが含まれない場合がある。
- 照会カレンダーは**読み取り専用**（iPhoneから予定の編集は不可）。
- GitHubの仕様で、**リポジトリに60日間コミットが無いとscheduleが自動停止**する。
  オフシーズン等で予定の変更が長期間無いと止まることがあるので、
  その場合はActionsタブに出る「Enable workflow」で再開する。
