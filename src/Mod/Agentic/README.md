# Agentic CAD FreeCADプラグイン

これはAgentic CADワークベンチの外部FreeCADプラグイン版である。

型付きプランを通じて、FreeCADをローカルの`agentic-cad`バックエンドに接続する:

1. アクティブなFreeCAD文書と選択状態を読み取る。
2. プロンプト、文書コンテキスト、クライアントの能力を`POST /api/freecad/plan`に送信する。
3. 許可リストに載った操作のみを、FreeCADのトランザクション内で実行する。
4. コミット前に再計算を行い、計測されたShapeの根拠を返す。

このプラグインは、エージェントが返した任意のPythonコードを意図的に実行しない。

## 環境変数

```bash
export AGENTIC_CAD_API_URL=http://127.0.0.1:8000
export AGENTIC_CAD_API_KEY=optional-local-key
```

## 開発用インストール

リポジトリのルートから:

```bash
python3 scripts/freecad_plugin_smoke/install_freecad_plugin.py
```

これは`integrations/freecad_plugin`を、ユーザーのFreeCADの`Mod/AgenticCAD`
ディレクトリへシンボリックリンクする。パッケージ化したコピーをテストする場合は
シンボリックリンクの代わりに`--copy`を使う。

その後バックエンドを起動する:

```bash
uvicorn backend.api.app:app --port 8000
```

FreeCADを開き、`Agentic CAD`ワークベンチに切り替える。ワークベンチは、
ヘルスチェック、プロンプト入力、型付きプランのプレビュー、明示的な実行承認、
構造化されたプラン差分の専用プレビュー領域、変更を伴うプランのための承認
チェックボックス、計測された実行根拠、`document.undo`によるロールバックを
備えた右サイドのドックを表示する。ドックには`Hardware Report`と
`Resolution Plan`ボタンもあり、未解決のハードウェアの根拠を書き出し、
FreeCADを離れずに範囲の限定された次のアクションへ変換できる。

ツールバーには以下も含まれる:

- `Run Agentic Self Test`: バックエンドを必要とせずに、プラグインの能力、
  承認ゲート、危険な操作の拒否、現在の文書コンテキストを検証する。
- `Report Chat Panel State`: Agentic CADドックを開くか再利用し、期待される
  コントロールが存在するかを報告する。
- `Run Plan Execute Smoke`: バックエンドのプランナーを呼び出し、承認済みの
  型付きFreeCAD操作を実行し、GUIから計測されたジオメトリの根拠を報告する。
- `Run Selection Update Smoke`: ボックスを作成し、FreeCADの選択モデルを通じて
  それを選択し、選択コンテキストから更新をプランニングし、それを実行し、
  更新後の幅を検証する。
- `Import Page2/Page7 Architectural Scan`: 生成済みの
  `architectural_scan_rough_bim_ir.json`を読み込み、1階平面図の詳細な叩き台
  として、壁・柱・床仕上げ・ドア/窓・水回り・什器・天井グリッドなどを
  FreeCAD文書内のレビュー可能な個別オブジェクトとして作成する。これは
  施工確定モデルではなく、寸法レビューと開口ブーリアン化の前段階である。
- `Build Focused Reprobe Request`: 現在の木ネジ候補レポートを、より小さい
  範囲限定の材料経路プローブ要求に変換する。
- `Rebuild Wood Screw Candidate Report`: 永続化された材料経路プローブレポートと
  ハードウェアIRから、候補レポートを再構築する。
- `Run Focused Reprobe Pipeline`: 範囲限定要求を構築し、FreeCADのB-rep材料
  プローブを実行し、メインの全体候補レポートを上書きせずに`focused_reprobe/`
  配下へ範囲限定の出力を書き込む。
- `Build Hardware Unresolved Report`: 現在のハードウェアIR、ネジ候補レポート、
  任意のHuman Reviewプランから`hardware_unresolved_report.json`を書き込み、
  どのBOM数量にまだ根拠やレビューが必要かをユーザーに提示する。
- `Build Hardware Resolution Plan`: 未解決レポートと任意のHuman Reviewプラン
  から`hardware_resolution_plan.json`を書き込む。これはハードウェアを配置
  しない。残りの数量をレビュー・根拠取得・仕様不足のいずれかのアクションに
  変換するだけである。
- `Confirm Resolution Reject Action`: 現在の却下可能なハードウェア解決
  アクションについて、非破壊的な`hardware_resolution_decisions.v1`の決定を
  記録する。
- `Export Fastener Reject Decisions`: その却下アクションを、既存のHuman
  Review適用パイプラインが取り込める`fastener_human_review_decisions.v1`
  レコードに変換する。
- `Build Resolution Status Report`: `hardware_resolution_status_report.json`
  を書き込み、どのハードウェア解決アクションが準備完了・保留中・無効かを
  示す。
- `Build Resolution Pipeline Queue`: `hardware_resolution_pipeline_queue.json`
  を書き込み、準備完了の決定を下流のタスクレコードに変換する一方、
  ソース/仕様が不足しているアクションはブロックしたままにする。
- `Execute Resolution Pipeline Queue`:
  `hardware_resolution_pipeline_execution_report.json`を書き込み、
  fail-closedの準備完了タスクを実行し、ソース/仕様タスクは後続の
  再プローブや再生成のために保留する。
- `Prepare Resolution Regeneration`: 保留中のソース/仕様入力から再生成準備
  成果物を書き込む。保留中の入力がない場合は`blocked_no_staged_inputs`を
  報告し、有効な保留入力がある場合は、次のFreeCAD生成フェーズ向けの配置
  要求と部分的なハードウェアIRパッチを書き込む。
- `Check Resolution Regeneration`:
  `hardware_resolution_regeneration_check_report.json`を書き込み、ジオメトリ
  生成を許可する前に、配置ターゲットの解決とFreeCADのハードウェア生成器
  サポートを確認する。
- `Execute Resolution Regeneration`:
  `hardware_resolution_regeneration_execution_report.json`を書き込み、
  準備状況チェックが`ready_for_freecad_generation`のときのみFreeCADの
  ハードウェア生成を実行する。
- `Build Resolution Layout Patch Candidates`:
  `hardware_resolution_regeneration/hardware_layout_patch_candidates.json`
  を書き込み、マージ前にFreeCADの接触・衝突プローブをまだ必要とする、
  非コミット型のアセンブリ配置候補を作成する。
- `Probe Resolution Layout Patch Contacts`:
  `hardware_resolution_regeneration/layout_patch_contact_probe/hardware_layout_patch_contact_probe_report.json`
  を書き込み、レイアウトマージを許可する前に、候補アンカーの接触・アンカー
  交差体積・衝突を計測する。
- `Preview Resolution Layout Patch Merge`: 承認なしで
  `hardware_resolution_regeneration/hardware_layout_patch_merge_report.json`
  を書き込み、ユーザー/検証者が明示的に承認するまでマージ済みレイアウトIRが
  一切書き込まれないことを証明する。
- `Approve Resolution Layout Patch Merge`: 接触プローブで承認済みの候補が
  存在し、承認コマンドが使われた場合のみ
  `assembly_layout_ir.layout_patch_merged.json`を書き込む。
- `Regenerate Resolution Layout Patch Assembly`:
  `hardware_resolution_regeneration/layout_patch_downstream_regeneration/hardware_layout_patch_downstream_regeneration_report.json`
  を書き込み、承認済みのマージ済みレイアウトIRが存在する場合のみFCStd・
  STEP・拘束成果物を再生成/検証する。
- `Build Resolution Input Requests`: `hardware_resolution_input_requests.json`
  を書き込む。これは、残っているソース根拠・仕様不足ゲートのための記入
  可能なチェックリストである。
- `Build Resolution Input Template`:
  `hardware_resolution_input_submission_template.json`を書き込む。これは、
  CAD配置の前に検証CLI/APIを通じて記入・提出できるJSONファイルである。
- `Build Resolution Input Drafts`:
  `hardware_resolution_input_draft_report.json`と
  `hardware_resolution_input_draft_template.json`を、ローカルの参照事実から
  書き込む。数量バランス・暫定・画像由来・不完全な事実は、自動提出される
  代わりに警告/ブロッカーとして表示される。
- `Build Resolution Input Confirmations`:
  `hardware_resolution_input_confirmation_requests.json`を書き込み、明示的な
  人間の確認を必要とする草案候補のみを列挙する。
- `Confirm Input Candidate`: ユーザーが1つの適格な候補を選択・確認した後、
  `hardware_resolution_input_confirmed_template.json`を書き込む。CAD
  ジオメトリは配置しない。
- `Submit Confirmed Resolution Input`: 確認済みテンプレートを検証し、
  同じfail-closedの提出経路を通じて有効な`add_evidence` / `add_spec`の決定
  を記録する。
- `Submit Resolution Input Template`: 記入済みテンプレートを検証し、有効な
  `add_evidence` / `add_spec`の決定のみを記録する。空のテンプレート項目は
  スキップされ、無効な項目はfail-closedとなる。
  ソース/仕様のペイロードを記入した後、同じ下流フローを
  `scripts/hardware_resolution/run_hardware_resolution_submission_flow.py`でリポジトリから実行
  し、検証済みの接触根拠と承認が供給されない限り、入力を保留し、レイアウト
  候補を構築し、接触/マージゲートの手前で停止できる。
- `Visualize Human Review`: `fastener_human_review_plan.v1`のJSONファイルを
  読み込み、候補の軸・ターゲットの選択肢・ジオメトリ警告を、アクティブな
  FreeCAD文書内に描画する。
- `Approve Selected Review Target`: ターゲット選択肢のオーバーレイを選択し、
  `select_target`の決定を`human_review_decisions.json`へ保存する。
- `Reject Selected Review Candidate`: 候補のレビューオーバーレイを選択し、
  `reject`の決定を保存する。
- `Defer Selected Review Candidate`: 候補のレビューオーバーレイを選択し、
  `defer`の決定を保存する。
- `Apply Human Review Decisions`: 保存された決定を適用し、レビュー済みの
  アセンブリを再生成し、拘束検証を実行し、再生成された`.FCStd`を開く。

Human Reviewの決定は、デフォルトではアクティブな`.FCStd`の隣に
`fastener_human_review_decisions.v1`として保存される。別の場所に書き込むには
`AGENTIC_CAD_HUMAN_REVIEW_DECISIONS`を設定する。

決定を保存した後は、FreeCAD内で`Apply Human Review Decisions`を使うか、
リポジトリから同じバックエンドパイプラインを実行する:

```bash
python3 scripts/wheelchair/apply_fastener_human_review.py \
  --decisions out/product_workspaces/media_8884e164a4c0/cad/disruptor_assembly_candidate/human_review_visualization/human_review_decisions.json
```

この適用ステップは、レビュー済み候補レポート、レビュー済み適用プラン、
再生成された`.FCStd`、拘束検証レポートを書き込む。fail-closedのままである:
危険な、人間が承認済みのターゲットは、CAD生成の前に却下候補へ変換される。

バックエンドが稼働している場合、プラグインはまず
`POST /api/freecad/human-review/apply`を呼び出す。ローカル開発中に
バックエンドが利用できない場合は、ローカルのリポジトリパイプラインへ
フォールバックする。

プラグインは2段階のフローを使う:

1. `Plan`: プロンプト + 文書コンテキスト + 能力をバックエンドに送信する。
2. 変更を伴うプランについては、差分プレビューを確認した後に承認
   チェックボックスにチェックを入れる。
3. `Execute Approved Plan`: レビュー済みの型付きプランをFreeCAD内で実行する。

プラグインには2つのエージェントループ経路も含まれる:

- `Preview Agent Loop`: `POST /api/freecad/agent/episode`を呼び出し、
  FreeCAD文書を変更せずに、エージェントループのステータス・承認質問・
  トレースイベントを表示する。
- `Run Approved Agent Loop`: FreeCADプラグインのプロセス内でループを実行し、
  クリックを明示的なユーザー承認として扱い、ネイティブの型付きFreeCADツール
  を実行し、ツールの結果を検証し、エピソードトレースを報告する。レポートは、
  アクティブな`.FCStd`の隣の`agentic_episodes/`配下に保存される。文書が
  まだ保存されていない場合は`out/freecad_agent_episodes/`配下に保存される。

変更を伴う操作は、この明示的な承認経路を使わない限り、ネイティブの実行層に
よって拒否される。

## 手動GUIスモークの実行手順

実際のFreeCAD UIを手動で確認する際にこれを使う。ターミナルからFreeCADを起動
する場合は、モデルプロバイダーのAPIキーが起動前に環境変数から取り除かれて
いることを確認し、認証情報がFreeCADのログや診断に現れないようにする。

1. リポジトリのルートからプラグインをインストールする:

```bash
python3 scripts/freecad_plugin_smoke/install_freecad_plugin.py
```

2. バックエンドを起動する:

```bash
uvicorn backend.api.app:app --port 8000
```

3. FreeCADを開き、`Agentic CAD`ワークベンチに切り替え、
   `Open Agentic Chat`をクリックする。
4. `Report Chat Panel State`をクリックする。レポートには、ドックと必要な
   コントロールが存在することが示されるはずである。
5. `Health Check`をクリックする。ログにはバックエンドのヘルスが
   `ok=True`と報告されるはずである。
6. `長さ22mm、幅14mm、高さ9mmの箱を作って`のような簡単なプロンプトを入力し、
   `Plan`をクリックする。専用の差分プレビュー領域に、提案された変更の
   `Before`・`After`・`Verify`の根拠が表示され、ログにも型付き操作と
   `[diff]`の行が表示されるはずである。
7. 承認チェックボックスにチェックを入れ、`Execute Approved Plan`をクリック
   する。FreeCADの`Part::Box`が現れ、ログには計測されたShapeの根拠が
   報告されるはずである。
8. `Run Approved Agent Loop`をクリックする。小さなボックスが作成され、
   `agentic_episodes/`または`out/freecad_agent_episodes/`配下にエピソード
   トレースが永続化されるはずである。
9. Disruptorのワークスペース文書で`Hardware Report`をクリックする。
   ハードウェアのプレビュー領域には、残っている未配置のハードウェアが
   一覧表示され、`hardware_unresolved_report.json`が書き込まれるはずである。
10. `Run Selection Update Smoke`をクリックする。選択オブジェクトの幅の更新が
    `33.0mm`と報告されるはずである。
11. `元に戻して`と入力するか、生成されたUndoプランを使い、それを実行して
    `document.undo`によるロールバックを検証する。
12. Disruptorのワークスペース文書を開いた状態で`Run Focused Reprobe
    Pipeline`をクリックし、範囲限定プローブ入力を構築し、FreeCADの材料
    プローブを実行し、木ネジ候補レポートを再構築する。デフォルトでは
    ワークスペース内の`assembly_candidate.FCStd`をプローブし、
    `focused_reprobe/`配下に範囲限定の出力を書き込む。別のモデルを使う
    場合は`AGENTIC_CAD_ASSEMBLY_MODEL`を設定する。
13. `Build Hardware Unresolved Report`をクリックする。ワークスペースに
    `hardware_unresolved_report.json`が書き込まれ、残っている未配置の
    ハードウェア数量(どの項目がソース根拠や人間のレビューを必要とするか
    を含む)が要約されるはずである。
14. `Build Hardware Resolution Plan`をクリックする。ワークスペースに
    `hardware_resolution_plan.json`が書き込まれ、CAD配置が許可される前に
    必要なレビュー/根拠/仕様のアクションが要約されるはずである。
15. 解決プランに却下可能な締結具アクションがちょうど1件ある場合、
    `Confirm Reject Action`をクリックする。
    `hardware_resolution_decisions.json`が書き込まれるはずである。
16. `Export Fastener Rejects`をクリックする。現在の締結具Human Reviewプラン
    に対して、候補ごとの却下決定を含む
    `human_review_decisions_from_resolution.json`が書き込まれるはずである。
17. `Resolution Status`をクリックする。
    `hardware_resolution_status_report.json`が書き込まれ、準備完了/保留中の
    解決アクションが要約されるはずである。
18. `Pipeline Queue`をクリックする。
    `hardware_resolution_pipeline_queue.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、準備完了の締結具却下適用タスクが
    1件と、ブロック中のソース/仕様アクションが2件表示されるはずである。
19. `Execute Queue`をクリックする。
    `hardware_resolution_pipeline_execution_report.json`が書き込まれる
    はずである。現在のDisruptorワークスペースでは、ジオメトリを変更せずに
    準備完了の却下適用タスクを実行し、2件のソース/仕様アクションはブロック
    したままになる。
20. `Regeneration Prep`をクリックする。
    `hardware_resolution_regeneration/hardware_resolution_regeneration_prep_report.json`
    が書き込まれるはずである。現在のDisruptorワークスペースでは、有効な
    チューブ/フォームのソース/仕様提出がまだ記録されていないため、
    `blocked_no_staged_inputs`と報告されるはずである。
21. `Regeneration Check`をクリックする。
    `hardware_resolution_regeneration/hardware_resolution_regeneration_check_report.json`
    が書き込まれるはずである。現在のDisruptorワークスペースでは、
    `no_staged_inputs`を伴う`blocked_before_freecad_generation`と報告される
    はずである。
22. `Execute Regeneration`をクリックする。
    `hardware_resolution_regeneration/hardware_resolution_regeneration_execution_report.json`
    が書き込まれるはずである。現在のDisruptorワークスペースでは、FreeCAD
    生成を実行せず、`blocked_before_freecad_generation`と報告されるはずで
    ある。
23. `Layout Patch Candidates`をクリックする。
    `hardware_resolution_regeneration/hardware_layout_patch_candidates.json`
    が書き込まれるはずである。現在のDisruptorワークスペースでは、有効な
    チューブ/フォームのソース根拠付き配置ターゲットがまだ保留されていない
    ため、候補`0`件の`blocked_no_resolved_targets`と報告されるはずである。
24. `Probe Layout Contacts`をクリックする。
    `hardware_resolution_regeneration/layout_patch_contact_probe/hardware_layout_patch_contact_probe_report.json`
    が書き込まれるはずである。現在のDisruptorワークスペースでは、計測
    すべきレイアウトパッチ候補がまだないため、`blocked_no_candidates`と
    報告されるはずである。
25. `Preview Layout Merge`をクリックする。
    `hardware_resolution_regeneration/hardware_layout_patch_merge_report.json`
    が書き込まれ、`blocked_user_approval_required`と報告されるはずである。
    マージ済みレイアウトIRを書き込んではならない。
26. `Approve Layout Merge`をクリックする。現在のDisruptorワークスペースでは、
    接触プローブで承認済みのレイアウト候補がまだ存在しないため、
    `blocked_no_approved_candidates`と報告されるはずである。
27. `Regenerate Layout Patch Assembly`をクリックする。現在のDisruptor
    ワークスペースでは、
    `hardware_resolution_regeneration/layout_patch_downstream_regeneration/hardware_layout_patch_downstream_regeneration_report.json`
    が書き込まれ、承認済みのマージ済みレイアウトIRがまだ存在しないため、
    `generated=false`を伴う`blocked_no_merged_layout`と報告されるはずである。
28. `Input Requests`をクリックする。CAD配置の前に供給する必要がある残りの
    ソース根拠・仕様不足の項目を含む
    `hardware_resolution_input_requests.json`が書き込まれるはずである。
29. `Input Template`をクリックする。保留中の要求ごとに1つの記入可能な
    ペイロードを含む`hardware_resolution_input_submission_template.json`
    が書き込まれるはずである。
30. `Input Drafts`をクリックする。
    `hardware_resolution_input_draft_report.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、ローカルの参照事実が残っている
    チューブ/フォームの要求に対するソース確認済みのペイロードを提供
    しないため、`needs_human_input`と報告される。
31. `Blocker Packet`をクリックする。
    `hardware_resolution_blocker_packet.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、残っているチューブの役割に対する
    ソース根拠ブロッカー1件と、フォームパッドの仕様不足ブロッカー1件を
    伴う`needs_human_input`と報告される。
32. `Answer Candidates`をクリックする。
    `hardware_resolution_answer_candidates.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、ローカルの事実にはチューブ/フォームの
    候補が含まれるが、ソース確認済みの回答として自動提出できる準備が
    整ったものはないため、`needs_human_confirmation`と報告される。
33. `Evidence Pack`をクリックする。
    `hardware_resolution_evidence_pack.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、`2`件の項目、カバー済みの必須
    フィールド`6`件、未カバーの必須フィールド`2`件を伴う
    `needs_human_confirmation`と報告される。これは非コミット型のレビュー
    パケットである: `source_backed=true`を設定せず、決定を記録せず、CAD
    ジオメトリを変更しない。
34. `Draft Manual From Evidence`をクリックする。
    `hardware_resolution_manual_completion_evidence_draft_report.json`と
    `hardware_resolution_manual_completion_review_template.json`が書き込まれる
    はずである。現在のDisruptorワークスペースでは、草案`2`行、完全な
    ペイロード`0`件、不完全なペイロード`2`件、`source_backed=0`を伴う
    `drafted_requires_review`と報告される。これはレビューの補助にすぎない:
    草案のペイロードは、人間/検証者が明示的に確認・補完するまで
    `source_backed=false`のままである。
35. `HITL Questions`をクリックする。
    `hardware_resolution_hitl_question_packet.json`と
    `hardware_resolution_hitl_answer_template.json`が書き込まれるはずである。
    現在のDisruptorワークスペースでは、質問`7`件(不足フィールド値の質問
    `3`件、ソース確認の質問`2`件、根拠の質問`2`件)を伴う`needs_user_input`
    と報告される。回答テンプレートには、候補の根拠が存在する場合、
    レビュー専用の`answer_options`も含まれる。現在はチューブの取り付け質問
    に`3`件の選択肢があり、フォーム材料と配置にはまだソース根拠付きの選択肢
    がない。これらの選択肢は自動選択されず、人間/検証者がテンプレートを
    編集するまで回答値は空のままである。
36. `HITL Patch Template`をクリックする。
    `hardware_resolution_hitl_answer_patch_template.json`が書き込まれ、
    残っている未回答のHITL行と、行ごとの推奨パッチ形状のみを列挙する。
    現在のDisruptorワークスペースでは、チューブ候補の草案選択の後、
    `6`件の残っている明示回答指示を伴う`needs_answers`と報告される。
37. `HITL Evidence Review`をクリックする。
    `hardware_resolution_hitl_evidence_review_packet.json`が書き込まれ、
    残っているHITL質問を、現在のペイロード値・候補の根拠・不足している
    ソース/仕様フィールドと組み合わせる。現在のDisruptorワークスペースでは、
    `2`件の項目、未回答の質問`6`件、ブロック中の項目`2`件を伴う
    `needs_review`と報告される。
38. 任意で`hardware_resolution_hitl_answer_patch.json`を記入し、
    `Preflight HITL Patch`をクリックするか、
    `python3 scripts/hardware_resolution/preflight_hardware_resolution_hitl_answer_patch.py`を実行
    する。プレフライトは、パッチが現在の根拠レビューパケットとまだ一致
    しているか、`source_confirmation=true`のパッチに対応する、または既存の
    根拠があるかを確認する。現在のDisruptorワークスペースでは、既存の部分的な
    チューブフィールドパッチが`ready_for_patch_apply`、`ok=true`、
    `valid_patch_count=1`、`remaining_unanswered_count=6`と報告される。
    これでもモデルが完成するわけではない。
39. `HITL Source Assertions`をクリックするか、
    `python3 scripts/hardware_resolution/build_hardware_resolution_hitl_source_assertion_packet.py`
    を実行して`hardware_resolution_hitl_source_assertion_packet.json`を書き込む。
    これは、残っているソース根拠付きの主張についての、範囲を絞った
    レビュアー/エージェント用チェックリストである: 必須のソース確認・根拠・
    フォーム材料・フォーム配置基準を、候補の根拠と警告とともにグループ化する。
    現在のDisruptorワークスペースでは、ブロック中の項目`2`件、ソース確認
    `2`件、根拠`2`件、フィールド値`2`件を伴う`needs_source_assertions`と
    報告される。これも非コミット型である。
40. `HITL Source Response Template`をクリックするか、
    `python3 scripts/hardware_resolution/build_hardware_resolution_hitl_source_assertion_response_template.py`
    を実行して
    `hardware_resolution_hitl_source_assertion_response_template.json`を書き込む。
    これは、レビュアー/検証者の回答のための記入可能な回答シートである。
    現在のDisruptorワークスペースでは、`2`件の回答を伴い`fillable`となる。
41. その回答ファイルを記入した後、`Apply HITL Source Response`をクリックする
    か、
    `python3 scripts/hardware_resolution/apply_hardware_resolution_hitl_source_assertion_response.py`
    を実行する。これは、記入済みのソースレビュー回答を
    `hardware_resolution_hitl_answer_patch.json`に変換する。空の回答は
    `status=empty`の
    `hardware_resolution_hitl_source_assertion_response_apply_report.json`を
    生成し、既存の回答パッチを上書きしない。根拠のない
    `source_confirmed=true`の回答はfail-closedとなる。
42. `Patch HITL Answers`をクリックするか、
    `python3 scripts/hardware_resolution/patch_hardware_resolution_hitl_answer_template.py`を実行
    する。このパッチは、選択された`answer_options[].option_id`または明示的な
    レビュアーの回答を`hardware_resolution_hitl_answer_template.json`に
    コピーできるが、HITL回答シートを編集するだけである。決定を記録せず、
    ソース根拠を信頼済みに設定せず、CADを変更しない。
43. `Apply HITL Answers`をクリックする。記入済みの回答が
    `hardware_resolution_manual_completion_review_template.json`にコピーされ、
    `hardware_resolution_hitl_answer_apply_report.json`が書き込まれるはずで
    ある。現在の空の回答テンプレートでは`empty`と報告され、`0`件の回答が
    適用され、手動プレフライトはブロックされたままとなる。
44. `Run Guarded HITL Submission`をクリックする。HITL回答を適用し、手動
    プレフライトを実行し、プレフライトが準備完了の場合のみガード付き提出を
    実行するはずである。現在の空の回答テンプレートでは、
    `hardware_resolution_hitl_guarded_submission/hardware_resolution_hitl_guarded_submission_report.json`
    を書き込み、`blocked_by_preflight`と報告する。決定を記録したりCAD再生成
    を開始したりしてはならない。
45. `Run Guarded HITL Patch Submission`をクリックする。
    `hardware_resolution_hitl_answer_patch.json`からガード付き提出までを
    1つのfail-closedなエントリーポイントで実行したい場合に使う。まず
    パッチを検証/適用し、その後同じHITLガード付きフローを実行する。現在の
    部分的なDisruptorパッチでは、`blocked_by_preflight`、
    `patch_status=patched`、`submission_flow_ran=false`と報告される。
46. `Manual Completion Template`をクリックする。
    `hardware_resolution_manual_completion_template.json`が書き込まれる
    はずである。これは、ローカルの候補だけでは解決できないブロッカー要求
    のための、直接のソース/仕様補完シートである。
47. `Apply Manual Completion`をクリックする。`source_backed=true`、空でない
    根拠、完全な必須フィールドを持つ項目のみが、CADジオメトリをコミット
    せずに`hardware_resolution_blocker_response_template.json`にコピーされる
    はずである。現在の空のDisruptor手動補完テンプレートでは`empty`と
    報告される。`Draft Manual From Evidence`がレビューテンプレートを作成した
    後は、`source_backed=true`・根拠・不足フィールドが供給されるまで、
    代わりに`invalid`と報告されるはずである。
48. `Preflight Manual Completion`をクリックする。
    `hardware_resolution_manual_completion_preflight_report.json`が書き込ま
    れ、手動で供給されたソース/仕様のペイロードが提出検証に合格するかを
    報告するはずである。現在の空のDisruptor手動補完テンプレートでは
    `no_valid_submission`と`ok_to_submit=false`が報告される。現在の根拠草案
    レビューテンプレートでは`invalid_manual_completion`と`ok_to_submit=false`
    が報告される。
45. `Run Guarded Manual Submission`をクリックする。手動補完プレフライトが
    準備完了の場合のみ実行されるはずである。現在の空のDisruptor手動補完
    テンプレートでは、
    `hardware_resolution_manual_completion_guarded_submission/hardware_resolution_guarded_submission_report.json`
    が`blocked_by_preflight`とともに書き込まれる。決定を記録したりCAD再生成
    を開始したりしてはならない。
46. `Answer Selection Template`をクリックする。
    `hardware_resolution_answer_selection_template.json`が書き込まれる
    はずである。これは、ユーザー/エージェントが候補を選択し、必要な場合は
    `human_confirmed=true`を設定し、`payload_override`を記入できる、記入
    可能な選択シートである。
47. `Apply Answer Selection`をクリックする。選択された、完全な候補の
    ペイロードが、CADジオメトリをコミットせずに
    `hardware_resolution_blocker_response_template.json`にコピーされる
    はずである。現在の未選択のDisruptor選択テンプレートでは`empty`と
    報告される。
48. `Preflight Answer`をクリックする。
    `hardware_resolution_answer_preflight_report.json`が書き込まれ、選択
    された回答が提出検証に合格するかを報告するはずである。現在の未選択の
    Disruptor選択テンプレートでは`no_valid_submission`と
    `ok_to_submit=false`が報告される。
49. `Run Guarded Submission`をクリックする。回答プレフライトが準備完了の
    場合のみ実行されるはずである。現在の未選択のDisruptor選択テンプレート
    では、
    `hardware_resolution_guarded_submission/hardware_resolution_guarded_submission_report.json`
    が`blocked_by_preflight`とともに書き込まれる。決定を記録したりCAD再生成
    を開始したりしてはならない。
50. `Blocker Response Template`をクリックする。
    `hardware_resolution_blocker_response_template.json`が書き込まれる
    はずである。これは、現在のブロッカーパケットのための記入可能な回答
    テンプレートである。
51. `Apply Blocker Responses`をクリックする。記入済みのブロッカー回答
    テンプレートを検証し、有効な回答を
    `hardware_resolution_input_submission_template.json`にコピーするはずで
    ある。現在の空のDisruptor回答テンプレートでは`empty`と報告され、決定を
    記録したりCADジオメトリを配置したりしない。
52. `Input Confirmations`をクリックする。
    `hardware_resolution_input_confirmation_requests.json`が書き込まれる
    はずである。現在のDisruptorワークスペースでは、以前のロックナットの
    確認がすでに昇格済みであり、残っているチューブ/フォームの要求は確認
    段階の前にブロックされているため、`no_confirmation_requests`と
    報告される。
53. ユーザー/検証者が一覧の候補に同意する場合、`Confirm Input Candidate`を
    クリックする。`hardware_resolution_input_confirmed_template.json`が
    書き込まれる。候補が複数存在する場合、コマンドは黙って1つを選ぶ代わりに
    どの候補を確認するかを尋ねる。
54. `Submit Confirmed Input`をクリックする。確認済みテンプレートを検証し、
    CADジオメトリを配置せずに有効なソース/仕様の決定を記録する。
55. 外部で通常のテンプレートを記入した後、`Submit Input Template`をクリック
    する。ペイロードを検証し、CADジオメトリを配置せずに有効な決定のみを
    記録するはずである。

## スモークテスト

FreeCADランタイムのスモークテストを実行する:

```bash
python3 scripts/freecad_plugin_smoke/smoke_freecad_plugin.py --workspace out/freecad_plugin_smoke
```

このスモークランナーは、プラグインの`services.native_tools`、
`services.self_test`、`services.local_agent_loop`、`services.fastener_reports`
をインポートするFreeCAD側スクリプトを生成し、承認されていない変更が拒否
されることを検証し、明示的な承認を伴うボックスを作成し、その幅を更新し、
Undoを実行し、`Hardware Report`・`Resolution Plan`・`Plan -> 承認チェックボックス
-> Execute`のチャットパネルウィジェットフローを検証し、承認済みのローカル
エージェントループを実行し、小さなフィクスチャに対して範囲限定の再プローブ
パイプラインを実行し、FreeCADランタイムでのハードウェア未解決/ハードウェア
解決レポート生成を検証し、機械可読なレポートとエージェントのエピソード
トレースを書き込む。

レポートのパス:

```text
out/freecad_plugin_smoke/freecad_plugin_smoke_report.json
```

互換性のあるFreeCADランタイムが利用できない場合、レポートのステータスは
`failed`となり、`runtime_failure.kind = freecad_runtime_unusable`となる。

Disruptorのリファレンスモデルに対して、実際のFreeCAD GUIスモークテストを
実行する:

```bash
python3 scripts/freecad_plugin_smoke/smoke_freecad_plugin_gui.py --wait-s 60
```

これは`/Applications/FreeCAD.app/Contents/MacOS/FreeCAD`を起動し、Disruptorの
`assembly_candidate.FCStd`を開き、`Agentic CAD`ワークベンチをアクティブに
し、ドックを開き、ドックの`Hardware Report`経路を実行し、ツールバーの
`Build Hardware Unresolved Report`と`Build Hardware Resolution Plan`コマンドが
登録・実行可能であることを検証し、解決却下の決定を記録し、締結具の却下
決定をエクスポートし、解決入力要求を構築し、ツールバーの`Build Resolution
Input Template`コマンドを実行し、ツールバーの`Run Focused Reprobe Pipeline`
コマンドを実行し、`Submit Resolution Input Template`が登録済みで空の
テンプレートに対して安全であることを検証し、ドックのスクリーンショットと
モデルビュー画像の両方を保存する。

レポートのパス:

```text
out/freecad_plugin_gui_smoke/freecad_plugin_gui_smoke_report.json
```

スクリーンショットのパス:

```text
out/freecad_plugin_gui_smoke/freecad_plugin_gui_smoke.png
```

モデルビュー画像のパス:

```text
out/freecad_plugin_gui_smoke/freecad_plugin_gui_model_view.png
```

Human Review可視化のスモークテストを実行する:

```bash
python3 scripts/freecad_plugin_smoke/smoke_freecad_human_review_visualization.py
```

これはレビューモデルを開き、Human-in-the-Loopのオーバーレイを描画し、
可視化済みのFCStdを保存する。

レポートのパス:

```text
out/product_workspaces/media_8884e164a4c0/cad/disruptor_assembly_candidate/human_review_visualization/human_review_visualization_report.json
```

対応している最初のツール群:

- `document.inspect`
- `document.undo`
- `primitive.create_box`
- `primitive.create_cylinder`
- `bim.create_element`（IFC分類・根拠参照付きの編集可能なsemantic element）
- `object.update_parameters`
- `object.translate`
