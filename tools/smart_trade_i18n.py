"""Smart Treaties: every player-facing string, in the 11 languages Victoria 3
ships. tools/gen_smart_trade_gui.py expands the @@TOKENS@@ and writes one
localization file per language, so the eleven cannot drift apart.

Game terms come from vanilla's own localization (2026-10-06, game 1.13.11),
as Build All's did, so the mod reads like the panel around it:
  shipping lane    concept_shipping_lane     merchant marine  merchant_marine
  treasury         concept_treasury          market           concept_market
  money transfer   money_transfer            port             building_port
  acceptance       TREATY_ARTICLE_DRAFT_ACCEPTANCE_TOOLTIP (the treaty sense;
                   concept_acceptance is the CULTURAL one, e.g. Russian
                   "Терпимость", and would be wrong here)
Register follows Build All: French "vous", German "Sie", Spanish "tú".

Rules for editing:
- Keep every [...] and @@TOKEN@@ exactly as in English
  (check_translations_match_english compares the calls per key).
- No literal square brackets as decoration, no double quotes.
- "(ST)" stays as is in every language: it names the mod.
- Button labels (ST_BTN_*) must fit the 58px button; keep them to 7 Latin
  characters or 3 CJK characters (check_st_button_labels_fit).
"""

LANGS = ["english", "french", "german", "spanish", "braz_por", "polish",
         "russian", "simp_chinese", "japanese", "korean", "turkish"]

# {TQ} is replaced per key (signed article vs draft); everything else is a token.
S = {}

S["ST_A_HEADER"] = {
    "english": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] a week to [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "french": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] par semaine vers [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "german": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] pro Woche an [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "spanish": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] por semana a [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "braz_por": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] por semana para [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "polish": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] na tydzień, odbiorca: [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "russian": "#header [Article.GetGoods.GetName], [Article.GetQuantity|0] в неделю, получатель: [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "simp_chinese": "#header [Article.GetGoods.GetName]，每周[Article.GetQuantity|0]，输往[Article.GetTargetCountry.GetNameNoFormatting]#!",
    "japanese": "#header [Article.GetGoods.GetName]、週[Article.GetQuantity|0]、[Article.GetTargetCountry.GetNameNoFormatting]へ#!",
    "korean": "#header [Article.GetGoods.GetName], 주당 [Article.GetQuantity|0], 수령국: [Article.GetTargetCountry.GetNameNoFormatting]#!",
    "turkish": "#header [Article.GetGoods.GetName], haftada [Article.GetQuantity|0], alıcı: [Article.GetTargetCountry.GetNameNoFormatting]#!",
}
S["ST_A_PAID_BY"] = {
    "english": "Paid for by [Article.GetSourceCountry.GetNameNoFormatting]. No cost to you.",
    "french": "Payé par [Article.GetSourceCountry.GetNameNoFormatting]. Gratuit pour vous.",
    "german": "Bezahlt von [Article.GetSourceCountry.GetNameNoFormatting]. Für Sie kostenlos.",
    "spanish": "Lo paga [Article.GetSourceCountry.GetNameNoFormatting]. Sin coste para ti.",
    "braz_por": "Pago por [Article.GetSourceCountry.GetNameNoFormatting]. Sem custo para você.",
    "polish": "Płaci: [Article.GetSourceCountry.GetNameNoFormatting]. Dla ciebie bez kosztów.",
    "russian": "Платит: [Article.GetSourceCountry.GetNameNoFormatting]. Для вас бесплатно.",
    "simp_chinese": "由[Article.GetSourceCountry.GetNameNoFormatting]支付，你无需花费。",
    "japanese": "[Article.GetSourceCountry.GetNameNoFormatting]が支払います。あなたの負担はありません。",
    "korean": "[Article.GetSourceCountry.GetNameNoFormatting]이(가) 지불합니다. 비용이 들지 않습니다.",
    "turkish": "[Article.GetSourceCountry.GetNameNoFormatting] öder. Size maliyeti yok.",
}
S["ST_A_SALE"] = {
    "english": "Sale: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "french": "Vente : @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "german": "Verkauf: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "spanish": "Venta: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "braz_por": "Venda: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "polish": "Sprzedaż: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "russian": "Продажа: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "simp_chinese": "出售：@money![@@A_SALE@@|D+=]（[Article.GetQuantity|0] x @money![@@A_PP@@|2]）",
    "japanese": "売却：@money![@@A_SALE@@|D+=]（[Article.GetQuantity|0] x @money![@@A_PP@@|2]）",
    "korean": "판매: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
    "turkish": "Satış: @money![@@A_SALE@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PP@@|2])",
}
S["ST_A_PURCHASE"] = {
    "english": "Purchase: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "french": "Achat : @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "german": "Einkauf: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "spanish": "Compra: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "braz_por": "Compra: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "polish": "Zakup: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "russian": "Закупка: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "simp_chinese": "购买：@money![@@NEG_A_BUY@@|D+=]（[Article.GetQuantity|0] x @money![@@A_PH@@|2]）",
    "japanese": "購入：@money![@@NEG_A_BUY@@|D+=]（[Article.GetQuantity|0] x @money![@@A_PH@@|2]）",
    "korean": "구매: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
    "turkish": "Alış: @money![@@NEG_A_BUY@@|D+=] ([Article.GetQuantity|0] x @money![@@A_PH@@|2])",
}
_LANE = "[Article.GetShippingLane.GetBeginState.GetName]"
_LANE2 = "[Article.GetShippingLane.GetEndState.GetName]"
S["ST_A_SHIP"] = {
    "english": f"Shipping: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} to {_LANE2})",
    "french": f"Voie de navigation : @money![@@NEG_A_SHIP@@|D+=] (de {_LANE} à {_LANE2})",
    "german": f"Schifffahrtsweg: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} nach {_LANE2})",
    "spanish": f"Ruta marítima: @money![@@NEG_A_SHIP@@|D+=] (de {_LANE} a {_LANE2})",
    "braz_por": f"Via de Embarcações: @money![@@NEG_A_SHIP@@|D+=] (de {_LANE} a {_LANE2})",
    "polish": f"Szlak żeglugowy: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} → {_LANE2})",
    "russian": f"Маршрут поставок: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} → {_LANE2})",
    "simp_chinese": f"船运线路：@money![@@NEG_A_SHIP@@|D+=]（{_LANE} → {_LANE2}）",
    "japanese": f"航路：@money![@@NEG_A_SHIP@@|D+=]（{_LANE} → {_LANE2}）",
    "korean": f"항로: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} → {_LANE2})",
    "turkish": f"Nakliye Rotası: @money![@@NEG_A_SHIP@@|D+=] ({_LANE} → {_LANE2})",
}
S["ST_SHIP_NONE"] = {
    "english": "Shipping: none, the markets touch",
    "french": "Voie de navigation : aucune, les marchés se touchent",
    "german": "Schifffahrtsweg: keiner, die Märkte grenzen aneinander",
    "spanish": "Ruta marítima: ninguna, los mercados son vecinos",
    "braz_por": "Via de Embarcações: nenhuma, os mercados são vizinhos",
    "polish": "Szlak żeglugowy: brak, rynki graniczą ze sobą",
    "russian": "Маршрут поставок: не нужен, рынки граничат",
    "simp_chinese": "船运线路：无，两个市场相邻",
    "japanese": "航路：なし、市場が隣接しています",
    "korean": "항로: 없음, 시장이 맞닿아 있습니다",
    "turkish": "Nakliye Rotası: yok, pazarlar komşu",
}
_NET_WEEK_UNIT = {
    # (label, "a week" phrase with {X}, "a unit" phrase with {Y})
    "english": ("Net:", "{X} a week", "{Y} a unit"),
    "french": ("Net :", "{X} par semaine", "{Y} l'unité"),
    "german": ("Netto:", "{X} pro Woche", "{Y} pro Einheit"),
    "spanish": ("Neto:", "{X} por semana", "{Y} por unidad"),
    "braz_por": ("Saldo:", "{X} por semana", "{Y} por unidade"),
    "polish": ("Netto:", "{X} na tydzień", "{Y} za jednostkę"),
    "russian": ("Итог:", "{X} в неделю", "{Y} за единицу"),
    "simp_chinese": ("净额：", "每周{X}", "每单位{Y}"),
    "japanese": ("収支：", "週{X}", "1単位あたり{Y}"),
    "korean": ("수지:", "주당 {X}", "단위당 {Y}"),
    "turkish": ("Net:", "haftada {X}", "birim başına {Y}"),
}
for key, net, pu in (("ST_A_NET_LANE", "A_NET_LANE", "PU_LANE"), ("ST_A_NET_LAND", "A_NET_LAND", "PU_LAND")):
    S[key] = {}
    for lang, (label, week, unit) in _NET_WEEK_UNIT.items():
        sep = "" if lang in ("simp_chinese", "japanese") else " "
        x = f"@money![@@{net}@@|D+=]"
        y = f"@money![@@{pu}@@|2+=]"
        S[key][lang] = f"#bold {label}{sep}{week.format(X=x)}#! ({unit.format(Y=y)})"
for key, x in (("ST_D_NET_LAND", "@money![@@D_MARGIN@@|D+=]"), ("ST_D_NET_SEA", "~@money![@@D_NET_MID@@|D+=]")):
    S[key] = {}
    for lang, (label, week, unit) in _NET_WEEK_UNIT.items():
        sep = "" if lang in ("simp_chinese", "japanese") else " "
        S[key][lang] = f"#bold {label}{sep}{week.format(X=x)}#!"

S["ST_MM_NOTE"] = {   # {TQ} -> traded quantity, filled per key
    "english": "Shipping costs 1 merchant marine per [{TQ}|0] units, at @money![@@MMP@@|2] each in your market. More ports at home lower that price.",
    "french": "Le transport coûte 1 marine marchande toutes les [{TQ}|0] unités, à @money![@@MMP@@|2] l'unité sur votre marché. Plus de ports chez vous font baisser ce prix.",
    "german": "Der Transport kostet 1 Handelsmarine je [{TQ}|0] Einheiten, zu je @money![@@MMP@@|2] auf Ihrem Markt. Mehr Häfen im eigenen Land senken diesen Preis.",
    "spanish": "El transporte cuesta 1 de marina mercante por cada [{TQ}|0] unidades, a @money![@@MMP@@|2] cada una en tu mercado. Más puertos propios bajan ese precio.",
    "braz_por": "O transporte custa 1 de marinha mercante a cada [{TQ}|0] unidades, a @money![@@MMP@@|2] cada uma no seu mercado. Mais portos no seu país baixam esse preço.",
    "polish": "Transport kosztuje 1 marynarkę handlową na każde [{TQ}|0] jednostek, po @money![@@MMP@@|2] za sztukę na twoim rynku. Więcej portów w kraju obniża tę cenę.",
    "russian": "Перевозка требует 1 торговый корабль на каждые [{TQ}|0] ед. по цене @money![@@MMP@@|2] за штуку на вашем рынке. Больше портов в стране снижает эту цену.",
    "simp_chinese": "每[{TQ}|0]单位需要1单位商船，在你的市场中每单位@money![@@MMP@@|2]。本国港口越多，这个价格越低。",
    "japanese": "輸送には[{TQ}|0]単位ごとに商船1単位が必要で、あなたの市場では1単位@money![@@MMP@@|2]です。自国の港が多いほどこの価格は下がります。",
    "korean": "운송에는 [{TQ}|0]단위마다 상선 1단위가 필요하며, 당신의 시장에서 단위당 @money![@@MMP@@|2]입니다. 자국 항구가 많을수록 이 가격이 내려갑니다.",
    "turkish": "Nakliye her [{TQ}|0] birim için 1 Denizci Tüccar gerektirir, pazarınızda tanesi @money![@@MMP@@|2]. Ülkenizdeki limanlar arttıkça bu fiyat düşer.",
}
S["ST_T_HEADER"] = {
    "english": "#header Net to your treasury, per week#!",
    "french": "#header Net pour votre Trésor, par semaine#!",
    "german": "#header Netto für Ihre Landeskasse, pro Woche#!",
    "spanish": "#header Neto para tu Tesoro, por semana#!",
    "braz_por": "#header Saldo para o seu Tesouro, por semana#!",
    "polish": "#header Netto dla skarbca, na tydzień#!",
    "russian": "#header Итог для казны, в неделю#!",
    "simp_chinese": "#header 国库每周净额#!",
    "japanese": "#header 国庫の週収支#!",
    "korean": "#header 국고 주간 수지#!",
    "turkish": "#header Hazineye haftalık net#!",
}
S["ST_T_GOODS_LANE"] = {
    "english": "Goods you send: @money![@@T_GOODS_LANE@@|D+=] (after shipping)",
    "french": "Biens envoyés : @money![@@T_GOODS_LANE@@|D+=] (après transport)",
    "german": "Gesendete Waren: @money![@@T_GOODS_LANE@@|D+=] (nach Transport)",
    "spanish": "Bienes que envías: @money![@@T_GOODS_LANE@@|D+=] (tras el transporte)",
    "braz_por": "Mercadorias enviadas: @money![@@T_GOODS_LANE@@|D+=] (após o transporte)",
    "polish": "Wysyłane towary: @money![@@T_GOODS_LANE@@|D+=] (po transporcie)",
    "russian": "Отправляемые товары: @money![@@T_GOODS_LANE@@|D+=] (после перевозки)",
    "simp_chinese": "你输出的商品：@money![@@T_GOODS_LANE@@|D+=]（扣除运费后）",
    "japanese": "送る商品：@money![@@T_GOODS_LANE@@|D+=]（輸送費差引後）",
    "korean": "보내는 상품: @money![@@T_GOODS_LANE@@|D+=] (운송비 차감 후)",
    "turkish": "Gönderdiğiniz mallar: @money![@@T_GOODS_LANE@@|D+=] (nakliye sonrası)",
}
_GOODS_SENT = {k: v.split(":")[0].split("：")[0] for k, v in S["ST_T_GOODS_LANE"].items()}
S["ST_T_GOODS_LAND"] = {}
for lang, label in _GOODS_SENT.items():
    colon = {"french": " :", "simp_chinese": "：", "japanese": "："}.get(lang, ":")
    sp = "" if lang in ("simp_chinese", "japanese") else " "
    S["ST_T_GOODS_LAND"][lang] = f"{label.rstrip()}{colon}{sp}@money![@@T_MARGIN@@|D+=]"
S["ST_T_MONEY"] = {
    "english": "Money transfers: @money![@@T_MONEY@@|D+=]",
    "french": "Transferts d'argent : @money![@@T_MONEY@@|D+=]",
    "german": "Geldübereignungen: @money![@@T_MONEY@@|D+=]",
    "spanish": "Transferencias de dinero: @money![@@T_MONEY@@|D+=]",
    "braz_por": "Transferências de Dinheiro: @money![@@T_MONEY@@|D+=]",
    "polish": "Przekazy pieniężne: @money![@@T_MONEY@@|D+=]",
    "russian": "Передача денег: @money![@@T_MONEY@@|D+=]",
    "simp_chinese": "资金转让：@money![@@T_MONEY@@|D+=]",
    "japanese": "お金の譲渡：@money![@@T_MONEY@@|D+=]",
    "korean": "자금 양도: @money![@@T_MONEY@@|D+=]",
    "turkish": "Para Transferleri: @money![@@T_MONEY@@|D+=]",
}
_D_G = "[ArticleDraft.GetGoods.GetName]"
_D_Q = "[ArticleDraft.GetQuantity|0]"
_D_C = "[ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]"
S["ST_D_HEADER"] = {lang: v.replace("[Article.GetGoods.GetName]", _D_G).replace("[Article.GetQuantity|0]", _D_Q)
                    .replace("[Article.GetTargetCountry.GetNameNoFormatting]", _D_C)
                    for lang, v in S["ST_A_HEADER"].items()}
_PP, _PH = "@money![@@D_PP1@@|2]", "@money![@@D_PH1@@|2]"
S["ST_D_MARGIN"] = {
    "english": f"Sale minus purchase: @money![@@D_MARGIN@@|D+=] ({_PP} vs {_PH} a unit, first-week prices)",
    "french": f"Vente moins achat : @money![@@D_MARGIN@@|D+=] ({_PP} contre {_PH} l'unité, prix de la première semaine)",
    "german": f"Verkauf minus Einkauf: @money![@@D_MARGIN@@|D+=] ({_PP} gegen {_PH} pro Einheit, Preise der ersten Woche)",
    "spanish": f"Venta menos compra: @money![@@D_MARGIN@@|D+=] ({_PP} frente a {_PH} por unidad, precios de la primera semana)",
    "braz_por": f"Venda menos compra: @money![@@D_MARGIN@@|D+=] ({_PP} contra {_PH} por unidade, preços da primeira semana)",
    "polish": f"Sprzedaż minus zakup: @money![@@D_MARGIN@@|D+=] ({_PP} wobec {_PH} za jednostkę, ceny z pierwszego tygodnia)",
    "russian": f"Продажа минус закупка: @money![@@D_MARGIN@@|D+=] ({_PP} против {_PH} за единицу, цены первой недели)",
    "simp_chinese": f"出售减购买：@money![@@D_MARGIN@@|D+=]（每单位{_PP}对{_PH}，首周价格）",
    "japanese": f"売却－購入：@money![@@D_MARGIN@@|D+=]（1単位あたり{_PP}対{_PH}、初週の価格）",
    "korean": f"판매 - 구매: @money![@@D_MARGIN@@|D+=] (단위당 {_PP} 대 {_PH}, 첫 주 가격)",
    "turkish": f"Satış eksi alış: @money![@@D_MARGIN@@|D+=] (birim başına {_PP} / {_PH}, ilk hafta fiyatları)",
}
_SM, _SL, _SH = "~@money![@@NEG_D_SHIP_MID@@|D+=]", "@money![@@NEG_D_SHIP_LO@@|D+=]", "@money![@@NEG_D_SHIP_HI@@|D+=]"
S["ST_D_SHIP_SEA"] = {
    "english": f"Shipping: {_SM} ({_SL} to {_SH} by route length, known once signed)",
    "french": f"Voie de navigation : {_SM} (de {_SL} à {_SH} selon la longueur de la route, connue à la signature)",
    "german": f"Schifffahrtsweg: {_SM} ({_SL} bis {_SH} je nach Routenlänge, bekannt nach Unterzeichnung)",
    "spanish": f"Ruta marítima: {_SM} (de {_SL} a {_SH} según la longitud de la ruta, conocida al firmar)",
    "braz_por": f"Via de Embarcações: {_SM} (de {_SL} a {_SH} conforme o comprimento da rota, conhecida ao assinar)",
    "polish": f"Szlak żeglugowy: {_SM} (od {_SL} do {_SH} zależnie od długości trasy, znanej po podpisaniu)",
    "russian": f"Маршрут поставок: {_SM} (от {_SL} до {_SH} в зависимости от длины маршрута, известной после подписания)",
    "simp_chinese": f"船运线路：{_SM}（视航线长度在{_SL}到{_SH}之间，签署后可知）",
    "japanese": f"航路：{_SM}（航路の長さにより{_SL}～{_SH}、締結後に確定）",
    "korean": f"항로: {_SM} (항로 길이에 따라 {_SL} ~ {_SH}, 체결 후 확정)",
    "turkish": f"Nakliye Rotası: {_SM} (rota uzunluğuna göre {_SL} ile {_SH} arası, imzadan sonra belli olur)",
}
S["ST_D_NO_PROFIT"] = {
    "english": "No quantity makes a profit.",
    "french": "Aucune quantité n'est rentable.",
    "german": "Keine Menge bringt Gewinn.",
    "spanish": "Ninguna cantidad da beneficio.",
    "braz_por": "Nenhuma quantidade dá lucro.",
    "polish": "Żadna ilość nie przynosi zysku.",
    "russian": "Ни одно количество не приносит прибыли.",
    "simp_chinese": "任何数量都无法盈利。",
    "japanese": "どの数量でも利益は出ません。",
    "korean": "어떤 수량으로도 이익이 나지 않습니다.",
    "turkish": "Hiçbir miktar kâr getirmiyor.",
}
_CG, _CC = "[Goods.GetName]", "[ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]"
S["ST_C_TIP"] = {
    "english": f"The most you can earn a week sending {_CG} to {_CC}, at the most profitable quantity they accept (estimate). Picking it starts at that quantity.",
    "french": f"Le maximum que vous pouvez gagner par semaine en envoyant {_CG} à {_CC}, à la quantité la plus rentable qu'il accepte (estimation). Le choisir part de cette quantité.",
    "german": f"Das Meiste, was Sie pro Woche verdienen können, wenn Sie {_CG} an {_CC} senden, bei der profitabelsten Menge, die angenommen wird (Schätzung). Die Auswahl beginnt mit dieser Menge.",
    "spanish": f"Lo máximo que puedes ganar por semana enviando {_CG} a {_CC}, con la cantidad más rentable que acepta (estimación). Al elegirlo, empieza con esa cantidad.",
    "braz_por": f"O máximo que você pode ganhar por semana enviando {_CG} para {_CC}, na quantidade mais lucrativa que ele aceita (estimativa). Ao escolher, começa nessa quantidade.",
    "polish": f"Najwięcej, ile możesz zarobić tygodniowo, wysyłając {_CG} do: {_CC}, przy najbardziej opłacalnej akceptowanej ilości (szacunek). Wybór zaczyna od tej ilości.",
    "russian": f"Максимум, который можно заработать в неделю, отправляя {_CG} получателю {_CC}, при самом выгодном приемлемом количестве (оценка). При выборе ставится это количество.",
    "simp_chinese": f"向{_CC}输送{_CG}每周最多可赚取的金额，按对方接受的最有利数量计算（估算）。选择后将从该数量开始。",
    "japanese": f"{_CC}へ{_CG}を送って週に稼げる最大額です。相手が受け入れる最も利益の出る数量で計算します（推定）。選ぶとその数量から始まります。",
    "korean": f"{_CC}에게 {_CG}을(를) 보내 주당 벌 수 있는 최대 금액입니다. 상대가 받아들이는 가장 이익이 큰 수량 기준(추정). 선택하면 그 수량으로 시작합니다.",
    "turkish": f"{_CC} ülkesine {_CG} göndererek haftada kazanabileceğiniz en yüksek tutar, kabul edilen en kârlı miktarda (tahmin). Seçince bu miktarla başlar.",
}
S["ST_BEST_TIP"] = {
    "english": "Set the quantity to the most profitable volume.",
    "french": "Règle la quantité sur le volume le plus rentable.",
    "german": "Setzt die Menge auf das profitabelste Volumen.",
    "spanish": "Ajusta la cantidad al volumen más rentable.",
    "braz_por": "Define a quantidade para o volume mais lucrativo.",
    "polish": "Ustawia ilość na najbardziej opłacalną.",
    "russian": "Устанавливает самое выгодное количество.",
    "simp_chinese": "将数量设为最有利可图的规模。",
    "japanese": "数量を最も利益の出る量に設定します。",
    "korean": "수량을 가장 이익이 큰 양으로 설정합니다.",
    "turkish": "Miktarı en kârlı hacme ayarlar.",
}
S["ST_BEST_TIP_GAIN"] = {
    "english": "Profit per week, about:",
    "french": "Bénéfice par semaine, environ :",
    "german": "Gewinn pro Woche, etwa:",
    "spanish": "Beneficio por semana, aprox.:",
    "braz_por": "Lucro por semana, aprox.:",
    "polish": "Zysk tygodniowo, około:",
    "russian": "Прибыль в неделю, около:",
    "simp_chinese": "每周利润约为：",
    "japanese": "週の利益、約：",
    "korean": "주간 이익, 약:",
    "turkish": "Haftalık kâr, yaklaşık:",
}
S["ST_BTN_BEST"] = {
    "english": "Best", "french": "Optimal", "german": "Optimal", "spanish": "Óptimo",
    "braz_por": "Ótimo", "polish": "Optimum", "russian": "Оптимум", "simp_chinese": "最优",
    "japanese": "最適", "korean": "최적", "turkish": "En iyi",
}
S["ST_BTN_MAX"] = {
    "english": "Max", "french": "Max", "german": "Max", "spanish": "Máx.",
    "braz_por": "Máx.", "polish": "Maks.", "russian": "Макс.", "simp_chinese": "最大",
    "japanese": "最大", "korean": "최대", "turkish": "Maks.",
}
_NET_SHORT = {"english": "Net", "french": "Net", "german": "Netto", "spanish": "Neto", "braz_por": "Saldo",
              "polish": "Netto", "russian": "Итог", "simp_chinese": "净额", "japanese": "収支",
              "korean": "수지", "turkish": "Net"}
for key, x in (("ST_ROW_A_LANE", "@money![@@A_NET_LANE@@|D+=]"), ("ST_ROW_A_LAND", "@money![@@A_NET_LAND@@|D+=]"),
               ("ST_ROW_T_LANE", "@money![@@T_NET_LANE@@|D+=]"), ("ST_ROW_T_LAND", "@money![@@T_NET_LAND@@|D+=]"),
               ("ST_ROW_D_LAND", "@money![@@D_MARGIN@@|D+=]"), ("ST_ROW_D_SEA", "~@money![@@D_NET_MID@@|D+=]")):
    S[key] = {lang: f"{label} {x}" for lang, label in _NET_SHORT.items()}
S["ST_NO_SHIPPING"] = {
    "english": "No shipping", "french": "Sans transport", "german": "Kein Transport", "spanish": "Sin transporte",
    "braz_por": "Sem transporte", "polish": "Bez transportu", "russian": "Без перевозки", "simp_chinese": "无需船运",
    "japanese": "輸送不要", "korean": "운송 없음", "turkish": "Nakliye yok",
}
S["SMART_TRADE_OVERLAND_TT"] = {
    "english": "Your markets border each other: goods transfers go overland and pay no shipping.",
    "french": "Vos marchés se touchent : les transferts de marchandises passent par voie terrestre et ne paient aucun transport.",
    "german": "Ihre Märkte grenzen aneinander: Warenübereignungen gehen über Land und zahlen keinen Transport.",
    "spanish": "Tus mercados son vecinos: las transferencias de bienes van por tierra y no pagan transporte.",
    "braz_por": "Seus mercados são vizinhos: as transferências de mercadorias vão por terra e não pagam transporte.",
    "polish": "Wasze rynki graniczą ze sobą: transfery towarów idą lądem i nie płacą za transport.",
    "russian": "Ваши рынки граничат: передача товаров идёт по суше без оплаты перевозки.",
    "simp_chinese": "你们的市场相邻：商品输送走陆路，无需支付运费。",
    "japanese": "市場が隣接しています。商品の譲渡は陸路で行われ、輸送費はかかりません。",
    "korean": "두 시장이 맞닿아 있습니다. 상품 양도는 육로로 이뤄지며 운송비가 없습니다.",
    "turkish": "Pazarlarınız komşu: mal transferleri karadan gider ve nakliye ödemez.",
}
_SEC = "[ArticleDraft.GetSecondOrTarget.GetNameNoFormatting]"
_FIR = "[ArticleDraft.GetFirstOrSource.GetNameNoFormatting]"
S["SMART_TRADE_MAX_SEND_TT"] = {
    "english": f"Set the quantity to [@@D_QMAX_SEND@@|0], filling {_SEC}'s shortage without going over your surplus.",
    "french": f"Règle la quantité sur [@@D_QMAX_SEND@@|0] : comble la pénurie de {_SEC} sans dépasser votre excédent.",
    "german": f"Setzt die Menge auf [@@D_QMAX_SEND@@|0]: deckt die Knappheit von {_SEC}, ohne Ihren Überschuss zu überschreiten.",
    "spanish": f"Ajusta la cantidad a [@@D_QMAX_SEND@@|0]: cubre la escasez de {_SEC} sin pasar de tu excedente.",
    "braz_por": f"Define a quantidade para [@@D_QMAX_SEND@@|0]: cobre a escassez de {_SEC} sem passar do seu excedente.",
    "polish": f"Ustawia ilość na [@@D_QMAX_SEND@@|0]: pokrywa niedobór u odbiorcy ({_SEC}) bez przekraczania twojej nadwyżki.",
    "russian": f"Устанавливает количество [@@D_QMAX_SEND@@|0]: покрывает дефицит получателя ({_SEC}), не превышая ваш излишек.",
    "simp_chinese": f"将数量设为[@@D_QMAX_SEND@@|0]：填补{_SEC}的短缺，且不超过你的盈余。",
    "japanese": f"数量を[@@D_QMAX_SEND@@|0]に設定します。あなたの余剰を超えずに{_SEC}の不足を埋めます。",
    "korean": f"수량을 [@@D_QMAX_SEND@@|0](으)로 설정합니다. 당신의 잉여를 넘지 않고 {_SEC}의 품귀를 채웁니다.",
    "turkish": f"Miktarı [@@D_QMAX_SEND@@|0] yapar: fazlanızı aşmadan {_SEC} kıtlığını kapatır.",
}
S["SMART_TRADE_ACCEPT_SEND_TT"] = {
    "english": "Set the quantity for the highest acceptance, at the best profit or the smallest loss.",
    "french": "Règle la quantité pour l'acceptation la plus haute, au meilleur bénéfice ou à la plus petite perte.",
    "german": "Setzt die Menge auf die höchste Akzeptanz, mit dem besten Gewinn oder dem kleinsten Verlust.",
    "spanish": "Ajusta la cantidad para la máxima aceptación, con el mayor beneficio o la menor pérdida.",
    "braz_por": "Define a quantidade para a maior aceitação, com o maior lucro ou o menor prejuízo.",
    "polish": "Ustawia ilość na najwyższą akceptację, przy największym zysku lub najmniejszej stracie.",
    "russian": "Устанавливает количество с наибольшей приемлемостью, при наибольшей прибыли или наименьшем убытке.",
    "simp_chinese": "将数量设为接受度最高的值，同时利润最大或亏损最小。",
    "japanese": "受諾が最も高くなる数量に設定します。利益は最大、または損失は最小です。",
    "korean": "수용도가 가장 높은 수량으로 설정합니다. 이익은 최대, 손실은 최소로.",
    "turkish": "Miktarı en yüksek kabule ayarlar, en iyi kârla ya da en küçük zararla.",
}
S["SMART_TRADE_MAX_RECV_TT"] = {
    "english": f"Set the quantity to [@@D_QMAX_RECV@@|0], filling your shortage without going over what {_FIR} spares.",
    "french": f"Règle la quantité sur [@@D_QMAX_RECV@@|0] : comble votre pénurie sans dépasser ce que {_FIR} peut céder.",
    "german": f"Setzt die Menge auf [@@D_QMAX_RECV@@|0]: deckt Ihre Knappheit, ohne mehr zu verlangen, als {_FIR} entbehren kann.",
    "spanish": f"Ajusta la cantidad a [@@D_QMAX_RECV@@|0]: cubre tu escasez sin pasar de lo que {_FIR} puede ceder.",
    "braz_por": f"Define a quantidade para [@@D_QMAX_RECV@@|0]: cobre sua escassez sem passar do que {_FIR} pode ceder.",
    "polish": f"Ustawia ilość na [@@D_QMAX_RECV@@|0]: pokrywa twój niedobór bez przekraczania tego, co może oddać nadawca ({_FIR}).",
    "russian": f"Устанавливает количество [@@D_QMAX_RECV@@|0]: покрывает ваш дефицит, не превышая того, что может отдать отправитель ({_FIR}).",
    "simp_chinese": f"将数量设为[@@D_QMAX_RECV@@|0]：填补你的短缺，且不超过{_FIR}能提供的量。",
    "japanese": f"数量を[@@D_QMAX_RECV@@|0]に設定します。{_FIR}が出せる量を超えずにあなたの不足を埋めます。",
    "korean": f"수량을 [@@D_QMAX_RECV@@|0](으)로 설정합니다. {_FIR}이(가) 내줄 수 있는 양을 넘지 않고 당신의 품귀를 채웁니다.",
    "turkish": f"Miktarı [@@D_QMAX_RECV@@|0] yapar: {_FIR} ülkesinin verebileceğini aşmadan kıtlığınızı kapatır.",
}
S["SMART_TRADE_ACCEPT_RECV_TT"] = {
    "english": "Set the quantity to [@@D_QACC_RECV@@|0] for the highest acceptance.",
    "french": "Règle la quantité sur [@@D_QACC_RECV@@|0] pour l'acceptation la plus haute.",
    "german": "Setzt die Menge auf [@@D_QACC_RECV@@|0] für die höchste Akzeptanz.",
    "spanish": "Ajusta la cantidad a [@@D_QACC_RECV@@|0] para la máxima aceptación.",
    "braz_por": "Define a quantidade para [@@D_QACC_RECV@@|0] para a maior aceitação.",
    "polish": "Ustawia ilość na [@@D_QACC_RECV@@|0] dla najwyższej akceptacji.",
    "russian": "Устанавливает количество [@@D_QACC_RECV@@|0] для наибольшей приемлемости.",
    "simp_chinese": "将数量设为[@@D_QACC_RECV@@|0]，接受度最高。",
    "japanese": "受諾が最も高くなるよう数量を[@@D_QACC_RECV@@|0]に設定します。",
    "korean": "수용도가 가장 높도록 수량을 [@@D_QACC_RECV@@|0](으)로 설정합니다.",
    "turkish": "En yüksek kabul için miktarı [@@D_QACC_RECV@@|0] yapar.",
}
S["SMART_TRADE_TREATIES_TT"] = {
    "english": "#header Net treaty income#!\nGoods you send: @money![@@P_TRADE@@|D+=]\nShipping lane costs: @money![@@NEG_P_SHIP@@|D+=] (estimate)\nMoney transfers: @money![@@P_MONEY@@|D+=]\nShipping is paid in merchant marine at your market price; more ports lower it.\nSee the outliner's treaty list for details.",
    "french": "#header Revenu net des traités#!\nBiens envoyés : @money![@@P_TRADE@@|D+=]\nCoût des voies de navigation : @money![@@NEG_P_SHIP@@|D+=] (estimation)\nTransferts d'argent : @money![@@P_MONEY@@|D+=]\nLe transport se paie en marine marchande au prix de votre marché ; plus de ports le font baisser.\nDétails dans la liste des traités du tableau de bord.",
    "german": "#header Nettoeinnahmen aus Verträgen#!\nGesendete Waren: @money![@@P_TRADE@@|D+=]\nKosten der Schifffahrtswege: @money![@@NEG_P_SHIP@@|D+=] (Schätzung)\nGeldübereignungen: @money![@@P_MONEY@@|D+=]\nDer Transport wird in Handelsmarine zu Ihrem Marktpreis bezahlt; mehr Häfen senken ihn.\nDetails in der Vertragsliste der Pinnwand.",
    "spanish": "#header Ingreso neto de tratados#!\nBienes que envías: @money![@@P_TRADE@@|D+=]\nCoste de rutas marítimas: @money![@@NEG_P_SHIP@@|D+=] (estimación)\nTransferencias de dinero: @money![@@P_MONEY@@|D+=]\nEl transporte se paga en marina mercante al precio de tu mercado; más puertos lo abaratan.\nDetalles en la lista de tratados del esquematizador.",
    "braz_por": "#header Receita líquida de tratados#!\nMercadorias enviadas: @money![@@P_TRADE@@|D+=]\nCusto das Vias de Embarcações: @money![@@NEG_P_SHIP@@|D+=] (estimativa)\nTransferências de Dinheiro: @money![@@P_MONEY@@|D+=]\nO transporte é pago em marinha mercante ao preço do seu mercado; mais portos o barateiam.\nDetalhes na lista de tratados dos Destaques.",
    "polish": "#header Dochód netto z traktatów#!\nWysyłane towary: @money![@@P_TRADE@@|D+=]\nKoszt szlaków żeglugowych: @money![@@NEG_P_SHIP@@|D+=] (szacunek)\nPrzekazy pieniężne: @money![@@P_MONEY@@|D+=]\nTransport opłaca się marynarką handlową po cenie twojego rynku; więcej portów ją obniża.\nSzczegóły na liście traktatów w Przyborniku.",
    "russian": "#header Чистый доход по договорам#!\nОтправляемые товары: @money![@@P_TRADE@@|D+=]\nРасходы на маршруты поставок: @money![@@NEG_P_SHIP@@|D+=] (оценка)\nПередача денег: @money![@@P_MONEY@@|D+=]\nПеревозка оплачивается торговыми кораблями по цене вашего рынка; больше портов снижает её.\nПодробности в списке договоров в Планировщике.",
    "simp_chinese": "#header 条约净收入#!\n你输出的商品：@money![@@P_TRADE@@|D+=]\n船运线路费用：@money![@@NEG_P_SHIP@@|D+=]（估算）\n资金转让：@money![@@P_MONEY@@|D+=]\n运费以你市场价格的商船支付；港口越多越便宜。\n详情见概览窗口中的条约列表。",
    "japanese": "#header 条約の純収入#!\n送る商品：@money![@@P_TRADE@@|D+=]\n航路の費用：@money![@@NEG_P_SHIP@@|D+=]（推定）\nお金の譲渡：@money![@@P_MONEY@@|D+=]\n輸送費は自国市場価格の商船で支払います。港が多いほど安くなります。\n詳細はアウトライナーの条約一覧へ。",
    "korean": "#header 조약 순수입#!\n보내는 상품: @money![@@P_TRADE@@|D+=]\n항로 비용: @money![@@NEG_P_SHIP@@|D+=] (추정)\n자금 양도: @money![@@P_MONEY@@|D+=]\n운송비는 자국 시장 가격의 상선으로 지불합니다. 항구가 많을수록 싸집니다.\n자세한 내용은 아웃라이너의 조약 목록을 보세요.",
    "turkish": "#header Net antlaşma geliri#!\nGönderdiğiniz mallar: @money![@@P_TRADE@@|D+=]\nNakliye rotası maliyeti: @money![@@NEG_P_SHIP@@|D+=] (tahmin)\nPara Transferleri: @money![@@P_MONEY@@|D+=]\nNakliye, pazar fiyatınızdan Denizci Tüccar ile ödenir; daha çok liman fiyatı düşürür.\nAyrıntılar Yan Bilgi'deki antlaşma listesinde.",
}
# The treasury line's own label, prepended to vanilla's expenses headers.
NET_TREATY_INCOME = {
    "english": "(ST) Net treaty income:", "french": "(ST) Revenu net des traités :",
    "german": "(ST) Nettoeinnahmen aus Verträgen:", "spanish": "(ST) Ingreso neto de tratados:",
    "braz_por": "(ST) Receita líquida de tratados:", "polish": "(ST) Dochód netto z traktatów:",
    "russian": "(ST) Чистый доход по договорам:", "simp_chinese": "(ST) 条约净收入：",
    "japanese": "(ST) 条約の純収入：", "korean": "(ST) 조약 순수입:", "turkish": "(ST) Net antlaşma geliri:",
}

for _k, _v in S.items():
    assert set(_v) == set(LANGS), (_k, set(LANGS) ^ set(_v))
assert set(NET_TREATY_INCOME) == set(LANGS)
