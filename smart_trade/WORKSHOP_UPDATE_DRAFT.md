# Workshop description update: Smart Treaties 0.13 (draft)

Dev-only file, not shipped (package_release.py only copies the mod folders).
Compared against `STEAM_WORKSHOP_DESCRIPTION.bbcode`, synced with the live
page on 2026-11-10. If you edited the live page since, apply the edits there.

## English: the edits only

Everything not listed stays as it is.

### Edit 1 (optional): first line

Current:

    See the total profit and cost of treaties before you sign them (including shipping lanes), and get smart default quantities with [b]Smart Treaties mod[/b].

New:

    See the total profit and cost of treaties before you sign them (including shipping lanes), get smart default quantities, and find the best deals to make with [b]Smart Treaties mod[/b].

### Edit 2b: "Real net profit or loss on all your treaties after you sign", one bullet added at the end

    [*][b]A warning when a goods transfer loses money[/b] 6 months in a row, naming the good and the weekly loss. Once per losing streak; renegotiating the treaty resets it.

### Edit 2: new section, between "Real net profit or loss on all your treaties after you sign" and "Where the numbers come from"

    [h2]Which deals to make[/h2]

    [list]
    [*][b]Top 5 goods transfers[/b] in your market's Trade tab: what to send, to whom, how much, and the weekly profit. Recomputed every month and when you open the tab.
    [*][b]Top 3 partners for each good[/b] in that good's panel (your market's tab).
    [*][b]Only partners likely to accept.[/b] Each row shows the partner's base acceptance in brackets (hover for the game's own breakdown). Countries below 0 are left out (I never managed to get them to accept).
    [*][b]One click to the treaty.[/b] The treaty button opens a draft with that country, and the good is already picked when you add a Goods Transfer.
    [/list]

### Edit 3: "Where the numbers come from", one sentence added at the end

    Suggestions use the same rule, at the best quantity your partner fully accepts.

### Edit 4: "No cheating"

Current:

    Display only. The buttons set the slider, exactly as you would by hand. Nothing changes your economy, your treaties or the AI.

New:

    Display only. The buttons set the slider or open a treaty draft, exactly as you would by hand. Nothing changes your economy, your treaties or the AI.

### Edit 5: "Compatibility", three lines

Save-safe, current:

    [*][b]Save-safe.[/b] Add or remove it mid-campaign; it stores nothing in your save.

New (the old line is no longer true: the suggestions and each partner's acceptance are kept in the save):

    [*][b]Save-safe.[/b] Add or remove it mid-campaign; it keeps a few numbers in your save (the suggestions and each partner's acceptance), unused if you remove it.

Single-player, current:

    [*][b]Single-player.[/b] The treaty totals assume one human player.

New:

    [*][b]Single-player.[/b] The treaty totals and suggestions assume one human player.

Conflicts, current:

    [*][b]Conflicts:[/b] it replaces the goods transfer picker, the treaty article and influence cells, the outliner's treaty rows, and two lines of the treasury tooltip. Another mod changing those same pieces will clash.

New (the market panel and the goods panel are now replaced too):

    [*][b]Conflicts:[/b] it replaces the goods transfer picker, the treaty article and influence cells, the outliner's treaty rows, two lines of the treasury tooltip, the market panel and the goods panel. Another mod changing those same pieces will clash.

## Simplified Chinese: the full description, ready to paste

Includes edits 1 to 5 and 2b. If you skip edit 1 in English, keep the live Chinese
first line instead of the first line below.

```
使用 [b]Smart Treaties（智能条约）[/b]，在签署条约之前就能看到总利润和总成本（含船运线路），获得更聪明的默认数量，并找到最值得做的交易。

不再有每周悄悄亏损数千却毫不知情的坏交易，也不用再来回点击寻找合适的数量。

[h2]签署前：预测净盈亏[/h2]

[list]
[*][b]每种商品的预测利润。[/b]商品选择界面中的每张卡片以绿色显示该商品的每周最佳利润，点开之前就能看出哪些商品值得输送。
[*][b]更聪明的默认数量。[/b]选中一种商品时，数量直接从最赚钱的规模开始，而不是游戏默认的 25%。
[*][b]滑块下方的三个按钮。[/b][b]最优[/b]：在对方仍接受该商品的前提下利润最高。[b]最大[/b]：填补对方的短缺，且不超过你的盈余。[b]👍[/b]：接受度最高，同时成本最低。
[*][b]滑块下方显示净利润和成本[/b]，拖动时实时更新。悬停可查看出售、购买和船运费用（两国市场相邻时无运费）。
[/list]

[h2]签署后：所有条约的实际净盈亏[/h2]

[list]
[*][b]每项条约的净额[/b]显示在概览窗口中，总额显示在"条约"标题上。
[*][b]每种商品的净额[/b]显示在条约面板中。悬停可查看完整明细，包含船运线路费用。
[*][b]条约净收入[/b]显示在国库提示框中，紧挨着游戏自带的收入和支出（不用再悬停 3 个不同位置来判断条约是否亏钱）。
[*][b]商品输送连续 6 个月亏损时发出提醒[/b]，注明商品和每周亏损额。每段亏损期只提醒一次；重新谈判条约后会重置。
[/list]

[h2]该做哪些交易[/h2]

[list]
[*][b]最佳 5 项商品输送[/b]显示在你的市场的"贸易"标签页中：输送什么、给谁、多少，以及每周利润。每月重新计算，打开该标签页时也会重新计算。
[*][b]每种商品的最佳 3 个伙伴[/b]显示在该商品的面板中（你的市场标签页）。
[*][b]只列出可能接受的伙伴。[/b]每行在括号中显示对方的基础接受度（悬停可查看游戏自带的明细）。低于 0 的国家不会列出（我从来没能让它们接受）。
[*][b]一键打开条约。[/b]条约按钮会打开与该国的条约草案，添加商品输送时该商品已自动选好。
[/list]

[h2]数字从何而来[/h2]

预测价格使用游戏自身的价格规则，按首周价格计算。已签署的条约使用实际的购买、出售和船运线路费用。草案还没有航线（游戏在签署时才选定航线），因此草案按中等长度的航线估算（签署后改用实际费用）。建议使用同样的规则，按对方完全接受的最优数量计算。

[h2]不作弊[/h2]

仅显示信息。按钮只是设置滑块或打开条约草案，和你手动操作完全一样。不会改变你的经济、条约或 AI。

[h2]兼容性[/h2]

[list]
[*][b]游戏版本 1.15。[/b]
[*][b]兼容成就。[/b]
[*][b]存档安全。[/b]可在战役中途添加或移除；它会在存档中保存少量数值（建议和各伙伴的接受度），移除后这些数值不会被使用。
[*][b]单人游戏。[/b]条约总额和建议假设只有一名人类玩家。
[*][b]支持《维多利亚3》自带的全部 11 种语言：[/b]English、Français、Deutsch、Español、Português do Brasil、Polski、Русский、简体中文、日本語、한국어、Türkçe。术语取自游戏原文，但并非母语译者翻译。欢迎指出错误，我会采纳。
[*][b]冲突：[/b]本模组替换了商品输送选择界面、条约条款和影响力单元格、概览窗口中的条约行、国库提示框中的两行、市场面板以及商品面板。修改相同部分的其他模组会产生冲突。
[/list]

[h2]反馈[/h2]
有任何问题请在评论区留言，我会修复。也欢迎提出建议和评分（截图下方的点赞按钮）！
```
