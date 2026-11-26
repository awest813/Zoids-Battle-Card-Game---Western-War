"""English for menu, deck, and name-entry labels (TXT-1853..1924)."""

KEYPAD_LAYOUT_IDS = {f"TXT-{number:04d}" for number in range(1894, 1907)}
ALBUM_HEADINGS = {
    "TXT-1884": (0x8001F238, 0x80065818, "ゾイドカード　　"),
    "TXT-1885": (0x8001F24C, 0x80065818, "カスタムカード　"),
    "TXT-1886": (0x8001F260, 0x80065818, "イベントカード　"),
    "TXT-1887": (0x8001F274, 0x80065850, "パイロットカード"),
}
MENU_DISPLAY = {
    "あなたの名前を入力してください": "Enter Name",
    "コマンダー": "Commander",
    "決定": "OK",
    "ゾイド　メイショウ": "ZOID NAME",
    "手　　札移　　動攻　　撃特　　殊": "HandMoveAtk Spcl",
}

# These bars are rasterized to textures that the game then slices at fixed
# glyph offsets. Each English segment takes exactly the original cell count.
PACKED_MENU = {
    "TXT-1883": (("適性能力", "Apt."), ("特殊能力", "Spcl")),
    "TXT-1908": (("変　更", "Chg"), ("消　去", "Del"), ("戻　る", "Bck"), ("デッキ数", "Deck")),
    "TXT-1913": (("全カード", "All"), ("パイロット", "Pilot"), ("カスタム", "Cust"), ("イベント", "Evnt")),
    "TXT-1916": (("攻撃", "AT"), ("射程", "RG"), ("移動", "MV")),
    "TXT-1918": (("決定", "OK"), ("戻る", "BK")),
    "TXT-1919": (("修　　復", "Fix"), ("情　　報", "Info"), ("終　　了", "End"), ("装　　備", "Gear")),
    "TXT-1920": (("取り外し", "Rmve"), ("は　い", "Yes"), ("いいえ", "No"), ("反　　撃", "Cntr")),
    "TXT-1921": (("交　　代", "Swap"), ("記　　録", "Save"), ("設　　定", "Opts"), ("捨て場", "Bin")),
    "TXT-1922": (("帝国軍基地", "EBase"), ("　　　", ""), ("共和国軍基地", "R Base")),
}

MENU = {
    "TXT-1853": "Add Zoid",
    "TXT-1854": "Change a Zoid",
    "TXT-1855": "Swap a Zoid",
    "TXT-1856": "Move a Zoid",
    "TXT-1857": "Delete a Zoid",
    "TXT-1858": "Deploy?",
    "TXT-1859": "Choose Zoids.",
    "TXT-1860": "When ready,",
    "TXT-1861": "press Start.",
    "TXT-1862": "Ocean World",
    "TXT-1863": "Island Park",
    "TXT-1864": "Rocky Area",
    "TXT-1865": "Forest Lake",
    "TXT-1866": "Title Logo",
    "TXT-1867": "Ancient",
    "TXT-1868": "Tightrope",
    "TXT-1869": "Octagon",
    "TXT-1870": "START to Trade",
    "TXT-1871": "YesNo ",
    "TXT-1872": "Trade cards?",
    "TXT-1873": "Exit Trade Mode?",
    "TXT-1874": "Model No.",
    "TXT-1875": "Type",
    "TXT-1876": "Length",
    "TXT-1877": "4-leg / 2-leg",
    "TXT-1878": "Height",
    "TXT-1879": "Weight",
    "TXT-1880": "Terrain",
    "TXT-1881": "Partner",
    "TXT-1882": "Crew Limit",
    "TXT-1884": "Zoids",
    "TXT-1885": "Custom",
    "TXT-1886": "Events",
    "TXT-1887": "Pilots",
    "TXT-1888": "Republic",
    "TXT-1889": "Empire",
    "TXT-1890": "Is this okay?",
    "TXT-1891": "Choose a Nation",
    "TXT-1892": "Hira",
    "TXT-1893": "Kata",
    "TXT-1907": "Enter Deck Name",
    "TXT-1909": "Select Deck",
    "TXT-1910": "Choose a Deck",
    "TXT-1911": "Empty Deck",
    "TXT-1912": "Register New Deck",
    "TXT-1914": "OK",
    "TXT-1915": "Add Cards",
    "TXT-1917": "YesNo ",
    "TXT-1923": "Jump Booster",
    "TXT-1924": "High-Speed Beagle",
}

for text_id, parts in PACKED_MENU.items():
    if any(len(english) > len(japanese) or not english.isascii()
           for japanese, english in parts):
        raise ValueError(f"{text_id} has a label that does not fit its glyph cells")
    MENU[text_id] = "".join(english.ljust(len(japanese)) for japanese, english in parts)
