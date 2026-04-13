# QAケース

## 目的

このファイルは、実務向けRAGプロトタイプの最初の手動QAセットです。  
retrieval の品質と `/ask` の挙動を評価するために使います。

## 使い方

各ケースについて、次の手順で確認します。

1. `POST /search` を実行する
2. 期待する chunk が上位に入っているか確認する
3. `POST /ask` を実行する
4. 期待する挙動になっているか確認する

## 現在の知識ベース

現在のサンプル知識ソース:

- `hr_policy_v1.pdf`
  - `chunk 0`: `有給休暇は社内システムから申請します。`
  - `chunk 1`: `上長承認後に申請が確定します。`
  - `chunk 2`: `繁忙期は申請期限に注意してください。`

## 手動QAケース

| ID | 質問 | 期待する retrieval | 期待する `/ask` の挙動 | メモ |
| --- | --- | --- | --- | --- |
| QA-001 | `有給休暇の申請方法は？` | `chunk 0` が top1 に来ること | 通常回答すること | 基本の正常系 |
| QA-002 | `有給申請はどうやる？` | `chunk 0` が top1 に来ること | 通常回答すること | 正常系の言い換え |
| QA-003 | `有給休暇は承認が必要ですか？` | `chunk 1` が top-k に入ること | 通常回答すること | 承認フロー確認 |
| QA-004 | `申請後はいつ確定しますか？` | `chunk 1` が top1 または上位に来ること | 通常回答すること | 確定条件の確認 |
| QA-005 | `繁忙期の注意点は？` | `chunk 2` が top1 に来ること | 通常回答すること | 注意事項の確認 |
| QA-006 | `申請期限で気をつけることは？` | `chunk 2` が top-k に入ること | 通常回答すること | `chunk 2` の言い換え |
| QA-007 | `育児休業の延長申請はどこから行いますか？` | 明確に関連する chunk がないこと | 回答拒否すること | 範囲外の質問 |
| QA-008 | `交通費の精算方法は？` | 明確に関連する chunk がないこと | 回答拒否すること | 別の範囲外質問 |
| QA-009 | `有給休暇の申請方法と承認条件を教えてください。` | `chunk 0` と `chunk 1` が top-k に入ること | 両方を使って通常回答すること | 複数chunk利用 |
| QA-010 | `有給申請時の注意点も含めて教えてください。` | `chunk 0` と `chunk 2` が top-k に入ること | 両方を使って通常回答すること | 注意事項を含む回答 |
| QA-011 | `育児休業の延長申請はどこから行いますか？` | `childcare_policy_v1.pdf` の延長申請に関する chunk が上位に来ること | 通常回答すること | 以前は範囲外だった質問の再評価 |
| QA-012 | `交通費の精算方法は？` | `expense_policy_v1.pdf` の申請方法に関する chunk が上位に来ること | 通常回答すること | 以前は範囲外だった質問の再評価 |
| QA-013 | `出張には承認が必要ですか？` | `business_trip_policy_v1.pdf` の承認に関する chunk が上位に来ること | 通常回答すること | 有給の承認と混同しないか確認 |
| QA-014 | `有給休暇の延長申請はどこから行いますか？` | 明確に関連する chunk がないこと | 回答拒否すること | 育児休業の延長申請と混同しないか確認 |
| QA-018 | `交通費精算の承認は必要ですか？` | `expense_policy_v1.pdf` の関連 chunk が上位に来ること | 慎重トーンの `yellow` 回答になること | 一部情報はあるが承認要否は断定できないケース |
| QA-019 | `出張申請の具体的な手順は？` | `business_trip_policy_v1.pdf` の申請方法に関する chunk が上位に来ること | `red` で回答拒否すること | 文書はあるが具体的手順は不足しているケース |
| QA-020 | `育児休業の延長申請に必要な書類は？` | `childcare_policy_v1.pdf` の延長申請・必要書類 chunk が上位に来ること | 慎重トーンの `yellow` 回答になること | 一部答えられるが書類一覧までは不明なケース |

## 評価チェックリスト

### Retrieval

- 最も関連する chunk が top1 に来ているか
- top1 でなくても top-k に入っているか
- 明らかに無関係な chunk が上位に来ていないか

### Ask API

- `enough_information` は妥当か
- `confidence`（`used_sources` 平均 score）の値は結果に対して自然か
- `answer_level` (`green` / `yellow` / `red`) は結果に対して自然か
- 回答は context の範囲内に収まっているか
- 根拠のない内容を勝手に補っていないか
- 返ってきた `sources` と回答内容が対応しているか
- `used_sources` が実際の回答内容と対応しているか
- `used_source_summaries` が `used_sources` の文書単位要約として自然か
- `sources` と `used_sources` の差分が説明可能か

### Document metadata / active control

- `GET /documents` で `version` / `is_active` / `created_at` / `updated_at` が見えるか
- `GET /documents/{document_id}` で特定文書の本文とメタデータを単体確認できるか
- 存在しない `document_id` に対する `GET /documents/{document_id}` が 404 を返すか
- `PATCH /documents/{document_id}/active` で `is_active` を切り替えられるか
- 存在しない `document_id` に対する `PATCH /documents/{document_id}/active` が 404 を返すか
- `PATCH /documents/{document_id}` で `title` / `source` / `content` / `version` / `is_active` を更新できるか
- 存在しない `document_id` に対する `PATCH /documents/{document_id}` が 404 を返すか
- 文書更新後に `GET /documents/{document_id}/chunks` が新しい chunk に置き換わるか
- 文書更新後の `/search` と `/ask` が新しい本文・`version`・`updated_at` を参照するか
- `is_active=False` にした文書が `/search` と `/ask` の対象から外れるか

### Access control

- `Document` が `access_level` を持ち、`GET /documents` / `GET /documents/{id}` で確認できるか
- `/search` が `user_role` に応じて権限外文書を候補から除外できるか
- `/ask` が `user_role` に応じて権限外文書を `sources` / `used_sources` に混入させないか
- 権限外文書しかない場合、`/ask` が安全側に倒して `red` になるか
- `hr` のような許可ロールでは、対応する制限文書を `/search` と `/ask` の両方で使えるか

## 判定ロジックに関するメモ

現在の `/ask` 判定:

- `green`: `top1 >= 0.65` かつ `top2 >= 0.55`
- `yellow`: `top1 >= 0.55`
- `red`: 上記以外

`confidence` は `used_sources` の平均 score を返すが、  
実際の通過判定は `top1` / `top2` の組み合わせで行う。

そのため、`confidence` は表示用の参考値であり、  
最終的な回答可否は `answer_level` と `enough_information` で判断する。

この値は仮であり、データやQAケースが増えたら再評価して調整する。

## メタデータ / active 制御に関するメモ

- `Document` は `version` / `is_active` / `created_at` / `updated_at` を持つ
- `GET /documents` は管理用の一覧として inactive 文書も返す
- `/search` と `/ask` は `is_active=True` の文書だけを対象にする
- `PATCH /documents/{document_id}/active` で無効化した文書は、削除せず残したまま検索対象から外せる
- `PATCH /documents/{document_id}` は文書本体を更新する API である
- `title` / `source` / `content` が変わった場合は chunk を再生成し、embedding も再作成する
- これにより `updated_at` は active フラグ更新だけでなく、文書内容更新の履歴としても意味を持つ
- `document_group` により、同じ系列の文書をまとめて扱えるようになった
- retrieval では同じ `document_group` の中から `updated_at` が新しい文書を優先し、旧版を混在させにくくした
- `updated_at` が同じ場合は `version` を補助判定に使い、`v2` を `v1` より新しいものとして扱う
- `used_source_summaries` は、回答に使った根拠を文書単位で `source / version / updated_at` つきで見やすく返すための表示用フィールドである
- `access_level` は文書単位の最小ACLとして使い、`public` は全員、その他は `user_role` 一致時のみ検索対象にする
- `user_role` は `/search` と `/ask` の request から受け取り、retrieval 前に権限外文書を落とす

## 次のステップ

手動QAに加えて、`/ask` の代表ケース、文書更新フロー、管理APIの正常系 / 異常系は pytest に少しずつ移せた。次は、残る評価観点をより機械的に見られるようにする。

1. `qa-cases.md` の代表ケースを小さな構造化データセットとして切り出す
2. retrieval の top-k / rerank 順位の回帰チェックを追加する
3. `version` / `updated_at` / `is_active` を使った最新版優先や運用ルールの検証ケースを増やす

## 自動化できた範囲

- `eval-cases.yaml` に `ask_cases` / `retrieval_cases` / `management_cases` の代表ケースを切り出した
- `/ask` では `green / yellow / red`、`used_sources`、`used_source_summaries` の重複排除まで pytest で見られる
- retrieval では代表ケースについて `top-k` の並び、top1 の `source`、`rerank_position` を pytest で見られる
- retrieval では `META-012` により、同じ `document_group` の旧版より最新版を優先する回帰も pytest で見られる
- retrieval では `META-013` により、`updated_at` が同じ場合に `version` を補助判定として使う回帰も pytest で見られる
- retrieval では `ACL-001` / `ACL-002` により、`user_role` ごとの文書出し分けを pytest で見られる
- `/ask` では `ACL-003` により、権限外文書しかないときに `red` で止まる回帰を pytest で見られる
- 文書管理では `GET /documents/{id}`、`PATCH /documents/{id}`、`PATCH /documents/{id}/active` の正常系 / 404 を pytest で見られる
- 文書更新では chunk 再生成と再 embedding、更新後の回答反映まで回帰テストの土台ができた



## 実行結果ログ

### QA-001
- 実行日: 2026-04-09
- `/search` top1: `chunk 0` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.7755088392429486`
- `/ask` confidence: `0.7017498537505099`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: `search` / `ask` ともに成立。回答には申請方法・承認・繁忙期注意が含まれた

### QA-002
- 実行日: 2026-04-10
- `/search` top1: `chunk 0` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.7138646563696103`
- `/ask` confidence: `0.71563347501306`
- `/ask` enough_information: `true`
- `/ask` answer_level: `green`
- 判定: OK
- メモ: query rewrite・hybrid・rerank により `chunk 0` が最上位となり、`ask` も `green` 判定で evidence-first な通常回答が返るようになった

### QA-003
- 実行日: 2026-04-10
- `/search` top1: `chunk 1` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.6215150144330562`
- `/ask` confidence: `0.5376299792340208`
- `/ask` enough_information: `true`
- `/ask` answer_level: `yellow`
- 判定: OK
- メモ: `chunk 1` が最上位となり、承認条件に対して `yellow` 判定の慎重トーンで evidence-first な回答が返るようになった

### QA-004
- 実行日: 2026-04-09
- `/search` top1: `chunk 1` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.4364646598649742`
- `/ask` confidence: `0.4790279868845738`
- `/ask` enough_information: `false`
- 判定: 部分OK
- メモ: `search` は確定条件の `chunk 1` を最上位にしたが、`ask` は拒否した

### QA-005
- 実行日: 2026-04-10
- `/search` top1: `chunk 2` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.5634020388887044`
- `/ask` confidence: `0.5634020388887044`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: `search` は期待どおり `chunk 2` を最上位にし、`ask` も注意点のみを簡潔に回答した

### QA-006
- 実行日: 2026-04-09
- `/search` top1: `chunk 2` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.5629980461060804`
- `/ask` confidence: `0.506098258464402`
- `/ask` enough_information: `false`
- 判定: 部分OK
- メモ: `search` は注意事項の `chunk 2` を最上位にしたが、`ask` は拒否した

### QA-007
- 実行日: 2026-04-09
- `/search` top1: `chunk 1` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.4254282445997449`
- `/ask` confidence: `0.4297071701984957`
- `/ask` enough_information: `false`
- 判定: OK
- メモ: 範囲外質問に対して候補は返ったが、threshold により回答拒否できた

### QA-008
- 実行日: 2026-04-09
- `/search` top1: `chunk 1` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.24172777374689555`
- `/ask` confidence: `0.24897522642972564`
- `/ask` enough_information: `false`
- 判定: OK
- メモ: 範囲外質問に対して十分に低い confidence で拒否できた

### QA-009
- 実行日: 2026-04-10
- `/search` top1: `chunk 0` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.679745775706314`
- `/ask` confidence: `0.679745775706314`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: 申請方法と承認条件の両方を含む質問に対し、`ask` が複数 chunk を使って通常回答できた

### QA-010
- 実行日: 2026-04-10
- `/search` top1: `chunk 0` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.5687477587964953`
- `/ask` confidence: `0.5687477587964953`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: 申請方法・注意点・承認条件を含む質問に対して通常回答したが、やや周辺情報を拾いすぎる傾向は残る

### QA-011
- 実行日: 2026-04-10
- `/search` top1: `chunk 1` (`childcare_policy_v1.pdf`)
- `/search` top1 score: `0.6133306505869025`
- `/ask` confidence: `0.5873554802379805`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: 以前は範囲外だった育児休業の延長申請について、`childcare_policy_v1.pdf` を正しく参照して通常回答できた

### QA-012
- 実行日: 2026-04-10
- `/search` top1: `chunk 0` (`expense_policy_v1.pdf`)
- `/search` top1 score: `0.6136298433168244`
- `/ask` confidence: `0.6494292519768617`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: 交通費精算の質問に対して `expense_policy_v1.pdf` を正しく最上位に取り、通常回答できた

### QA-013
- 実行日: 2026-04-10
- `/search` top1: `chunk 1` (`business_trip_policy_v1.pdf`)
- `/search` top1 score: `0.6357445725139045`
- `/ask` confidence: `0.5729932557645326`
- `/ask` enough_information: `true`
- 判定: OK
- メモ: 出張の承認条件について、`business_trip_policy_v1.pdf` を参照して通常回答できた。有給の承認と混同していない

### QA-014
- 実行日: 2026-04-10
- `/search` top1: `chunk 0` (`hr_policy_v1.pdf`)
- `/search` top1 score: `0.5582808063461537`
- `/ask` confidence: `0.5424595307434329`
- `/ask` enough_information: `false`
- `/ask` answer_level: `red`
- 判定: OK
- メモ: 有給休暇と育児休業の延長申請を混同せず、情報不足として回答拒否できた

### QA-015
- 実行日: 2026-04-10
- 質問: `有給休暇の承認者は誰ですか？`
- `/ask` confidence: `0.49120012010507863`
- `/ask` enough_information: `false`
- `/ask` answer_level: `red`
- 判定: OK
- メモ: 文書に「上長承認」はあるが、承認者の詳細定義まではないため、安全側に倒して回答拒否した

### QA-016
- 実行日: 2026-04-10
- 質問: `有給申請の具体的な手順は？`
- `/ask` confidence: `0.5983458971896048`
- `/ask` enough_information: `true`
- `/ask` answer_level: `yellow`
- 判定: OK
- メモ: `yellow` の慎重前置きつきで、申請方法は答えつつ具体的手順は不明と補足できており、中間ケースとして自然

### QA-017
- 実行日: 2026-04-10
- 質問: `出張申請の方法は？`
- `/ask` confidence: `0.43779030431310234`
- `/ask` enough_information: `false`
- `/ask` answer_level: `red`
- 判定: OK
- メモ: 出張関連文書は取得できたが、現在のしきい値では十分な根拠とみなさず拒否した

### QA-018
- 実行日: 2026-04-10
- 質問: `交通費精算の承認は必要ですか？`
- `/ask` confidence: `0.5844841499811079`
- `/ask` enough_information: `true`
- `/ask` answer_level: `yellow`
- 判定: OK
- メモ: 承認要否そのものは断定できないため、慎重トーンで「提示情報だけでは判断できない」と返せた

### QA-019
- 実行日: 2026-04-10
- 質問: `出張申請の具体的な手順は？`
- `/ask` confidence: `0.4519409791607707`
- `/ask` enough_information: `false`
- `/ask` answer_level: `red`
- 判定: OK
- メモ: 出張申請の存在は取れているが、具体的手順は不足しているため安全側に倒して拒否した

### QA-020
- 実行日: 2026-04-10
- 質問: `育児休業の延長申請に必要な書類は？`
- `/ask` confidence: `0.6636686395435668`
- `/ask` enough_information: `true`
- `/ask` answer_level: `yellow`
- 判定: OK
- メモ: 必要書類の添付までは答えつつ、具体的な書類一覧は不明と補足できており、`yellow` として自然

### META-001
- 実行日: 2026-04-10
- 確認内容: `GET /documents`
- 結果: 全4文書について `version` / `is_active` / `created_at` / `updated_at` を確認できた
- 判定: OK
- メモ: 文書メタデータの見える化はできている

### META-002
- 実行日: 2026-04-10
- 確認内容: `PATCH /documents/2/active` に `{ "is_active": false }`
- 結果: `hr_policy_v1.pdf` が `is_active=false` になり、`updated_at` も更新された
- 判定: OK
- メモ: 削除せず無効化できることを確認

### META-003
- 実行日: 2026-04-10
- 確認内容: `POST /search` with `有給申請はどうやる？`
- 結果: inactive にした `hr_policy_v1.pdf` は検索結果に出ず、active 文書のみが返った
- 判定: OK
- メモ: `is_active=False` が retrieval から除外条件として効いている

### META-004
- 実行日: 2026-04-11
- 確認内容: `PATCH /documents/1`
- 結果: `childcare_policy_v1.pdf` 相当の文書が `childcare_policy_v2.pdf` / `version=v2` / 新本文に更新され、`updated_at` も更新された
- 判定: OK
- メモ: 文書IDは維持したまま、本文とメタデータを上書き更新できた

### META-005
- 実行日: 2026-04-11
- 確認内容: `GET /documents/1/chunks`
- 結果: `document_id=1` の chunk 群が新しい本文ベースに置き換わり、`人事ポータル` / `本人確認書類` / `上長確認` を含む新 chunk が返った
- 判定: OK
- メモ: 古い chunk の使い回しではなく、更新後の本文から再 chunk されていることを確認

### META-006
- 実行日: 2026-04-11
- 確認内容: `POST /search` and `POST /ask` with `育児休業の延長申請はどこから行いますか？`
- 結果: `/search` は `childcare_policy_v2.pdf` の `人事ポータル` chunk を top1 とし、`/ask` も `version=v2` / 更新後 `updated_at` を持つ `used_sources` を使って `人事ポータル` ベースで回答した
- 判定: OK
- メモ: 文書更新 → chunk 再生成 → 再 embedding → retrieval → ask 回答まで end-to-end で反映された

### META-007
- 実行日: 2026-04-11
- 確認内容: `POST /ask` with `育児休業の延長申請はどこから行いますか？`
- 結果: `used_source_summaries` に `childcare_policy_v2.pdf (v2, 2026-04-11更新)` が1件だけ返り、同一文書から複数 chunk を使っていても重複表示されなかった
- 判定: OK
- メモ: `used_sources` は chunk 単位、`used_source_summaries` は文書単位という役割分担で見せられるようになった

### META-008
- 実行日: 2026-04-11
- 確認内容: `GET /documents/1`
- 結果: `title` / `source` / `content` / `version` / `is_active` / `created_at` / `updated_at` を1件で取得でき、更新後の `childcare_policy_v2.pdf` / `version=v2` / 新しい `updated_at` を確認できた
- 判定: OK
- メモ: 一覧APIを見なくても、特定文書の状態を単体で確認できるようになった

### META-009
- 実行日: 2026-04-11
- 確認内容: `GET /documents/9999`
- 結果: `404 Not Found` と `Document not found` を返した
- 判定: OK
- メモ: 管理APIの最低限の異常系として、存在しない文書IDへの単体取得を確認する

### META-010
- 実行日: 2026-04-11
- 確認内容: `PATCH /documents/9999`
- 結果: `404 Not Found` と `Document not found` を返した
- 判定: OK
- メモ: 存在しない文書IDへの更新要求が安全に失敗することを確認する

### META-011
- 実行日: 2026-04-11
- 確認内容: `PATCH /documents/9999/active`
- 結果: `404 Not Found` と `Document not found` を返した
- 判定: OK
- メモ: 存在しない文書IDへの active 切り替え要求が安全に失敗することを確認する

### ACL-001
- 実行日: 2026-04-12
- 確認内容: `POST /search` with `query=人事評価資料はどこで確認できますか？`, `user_role=employee`
- 結果: `hr_review_policy_v1.pdf` は返らず、`public_handbook_v1.pdf` / `hr_policy_v1.pdf` のみが候補となった
- 判定: OK
- メモ: 権限外の `hr` 文書を漏らさず、`public` 文書だけで検索結果を構成できた

### ACL-002
- 実行日: 2026-04-12
- 確認内容: `POST /search` with `query=人事評価資料はどこで確認できますか？`, `user_role=hr`
- 結果: `hr_review_policy_v1.pdf` の `人事ポータル` / `人事部のみ参照可能` chunk が top 2 に入り、`public` 文書も一緒に返った
- 判定: OK
- メモ: 許可ロールでは制限文書も `public` 文書も検索対象に含まれることを確認した

### ACL-003
- 実行日: 2026-04-12
- 確認内容: `POST /ask` with `query=人事評価資料はどこで確認できますか？` を `user_role=employee` / `user_role=hr` で比較
- 結果: `employee` では `hr_review_policy_v1.pdf` を使わず `red` で回答拒否し、`hr` では `hr_review_policy_v1.pdf` を `used_sources` / `used_source_summaries` に使って `green` 回答した
- 判定: OK
- メモ: 権限付き検索だけでなく、回答生成でも権限外文書を混入させないことを end-to-end で確認した


## 中間レビュー（rewrite / hybrid / rerank 反映後）

### 改善した点
- `QA-002` のような言い換え質問に対して、期待する `chunk 0` が最上位に来るようになった
- `QA-003` のような承認条件に関する質問では、`chunk 1` が最上位に来るようになり、質問意図により近い順位付けができるようになった
- `query rewrite` により、ユーザーの自然な質問を検索向けの表現に整えられるようになった
- `hybrid search` により、意味の近さだけでなく文字列の一致も補助的に使えるようになった
- `rerank` により、最終順位を質問への関連度ベースでより自然に調整できるようになった
- `rerank` の返り値に対して妥当性チェックを入れ、重複番号・欠番・余計な番号がある場合は元の順序にフォールバックするようにした

### 現時点の強み
- 直球の質問だけでなく、ある程度の言い換え質問にも対応しやすくなった
- 質問意図に合う chunk を上位に持ってくる精度が改善した
- `green / yellow / red` の3段階判定により、通常回答・慎重回答・拒否を分けられるようになった
- 追加した文書に対しても、制度ごとの違いをある程度識別して検索・回答できている
- 「有給休暇の延長申請」のような誤った制度混同を、回答拒否で防げている
- 「有給休暇の承認者は誰か」のような、文書に一部関連情報はあるが断定が危険な質問でも、安全側に倒して拒否できている
- `交通費精算の承認要否` や `育児休業の必要書類` のような中間ケースでも、`yellow` で慎重に情報提供できている
- `sources` と `used_sources` を分けたことで、検索候補と実際に回答に使った根拠を区別できるようになった
- `used_source_summaries` により、回答に使った根拠文書の版と更新日を、重複なく文書単位で見せられるようになった
- `version` / `is_active` / `updated_at` を文書メタデータとして持ち、inactive 文書を検索対象から外せるようになった
- `document_group` と `updated_at` により、同じ系列の文書が複数ある場合でも最新版を優先する最小ロジックが入った
- `updated_at` が同じ場合でも `version` を補助判定に使えるため、最新版優先の挙動が少し安定した
- `access_level` / `user_role` により、最小実装ながら `public` と制限文書を検索・回答の両方で出し分けられるようになった

### まだ残っている課題
- `score` は hybrid score のままで、表示順位は rerank 後の順序になっているため、利用者には少し分かりづらい
- `rerank` の出力パースは以前より安定したが、番号以外の説明文混入など、より広い揺れへの耐性は今後さらに強化余地がある
- 候補数やデータ量がまだ少ないため、現時点の改善がそのまま大規模データでも通用するかは未確認である
- `/ask` の confidence は表示用の平均 score で、実際の判定は `top1` / `top2` ベースのため、意味の違いをどう見せるかは今後の課題である
- `/ask` の context selection は改善し、不要な周辺情報は減ったが、ユーザー向け表示としての文体や情報密度はまだ調整余地がある
- `used_sources` は返せるようになったが、QAログではまだ個別ケースごとの使用根拠を詳細には記録していない

### 現時点の判断
- 現在のRAGは、初期の semantic-only 検索に比べて実務的な retrieval パイプラインにかなり近づいた
- 特に `query rewrite + hybrid search + rerank` の組み合わせは、今回の小規模QAケースでは有効だった
- `ask` は単一 threshold から `green / yellow / red` の3段階判定に移り、通常回答と慎重回答を分けられるようになった
- 文書数を増やしても、少なくとも今回の4文書構成では新規制度の識別と誤混同の拒否が機能している
- `yellow` の前置きを保守的にしたことで、中間ケースでも断定しすぎない返し方に寄せられている
- 現在のしきい値はやや保守的だが、`yellow` と `red` の役割分担は実務的に概ね自然である
- context selection と evidence-first prompt により、`/ask` の回答は以前より根拠に忠実で、不要な情報を含みにくくなった
- `used_sources` の導入により、検索候補全体と回答に採用した根拠を分けて評価できる段階に入った
- `used_source_summaries` により、回答で使った根拠文書の `version` / `updated_at` を UI 向けに見せる足場ができた
- `rerank` は最小実装から一段安定化し、出力が不正な場合でも retrieval 全体が壊れにくい構成になった
- 文書メタデータと active 制御により、「残すが使わない」という実務運用の第一歩が入った
- 文書更新 API により、既存文書の修正内容が chunk と回答にまで反映される更新フローを確認できた
- `document_group` と最新版優先ロジックにより、同じ系列の旧版・新版が混在しても、まずは新しい文書を取りやすい段階に入った
- `META-013` により、更新時刻が同じケースでも `version` タイブレークまで回帰テストで押さえられた
- `access_level` を使った最小ACLにより、`employee` と `hr` で `/search` と `/ask` の結果を出し分けられる段階に入った
- 次の段階では、inactive 文書を `/ask` でも使わないことの確認や、`version` / `updated_at` をどう回答に活かすかを整理するのが自然である
