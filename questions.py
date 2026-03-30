import json
import random
import sqlite3 as _sqlite3

import db
from config import DB_PATH

# ── Math helpers ──────────────────────────────────────────────────────────────

def _make_int_options(correct: int, spread: int = 15) -> tuple[list[str], int]:
    candidates: set[int] = {correct}
    attempts = 0
    while len(candidates) < 4 and attempts < 60:
        delta = random.randint(1, max(spread, 5))
        if random.random() < 0.5:
            delta = -delta
        c = correct + delta
        if c > 0:
            candidates.add(c)
        attempts += 1
    for i in range(1, 20):
        if len(candidates) >= 4:
            break
        candidates.add(correct + i)
    opts = list(candidates)[:4]
    random.shuffle(opts)
    return [str(o) for o in opts], opts.index(correct)


def _tier1() -> dict:
    a, b = random.randint(11, 99), random.randint(11, 99)
    op = random.choice(["+", "−"])
    if op == "−" and b > a:
        a, b = b, a
    correct = a + b if op == "+" else a - b
    opts, idx = _make_int_options(correct, spread=12)
    return {"type": "math", "text": f"{a} {op} {b} = ?", "options": opts, "correct_index": idx}


def _tier2() -> dict:
    a = random.randint(12, 99)
    b = random.randint(2, 9)
    correct = a * b
    opts, idx = _make_int_options(correct, spread=max(b * 3, 10))
    return {"type": "math", "text": f"{a} × {b} = ?", "options": opts, "correct_index": idx}


def _tier3() -> dict:
    variant = random.choice(["percent", "fraction", "division"])
    if variant == "percent":
        pct = random.choice([10, 15, 20, 25, 30, 40, 50])
        base = random.choice([20, 40, 50, 60, 80, 100, 120, 200])
        correct = int(pct * base / 100)
        opts, idx = _make_int_options(correct, spread=10)
        return {"type": "math", "text": f"What is {pct}% of {base}?", "options": opts, "correct_index": idx}
    elif variant == "fraction":
        fracs = [
            (1, 4, 0.25), (1, 2, 0.5), (3, 4, 0.75),
            (1, 5, 0.2), (2, 5, 0.4), (3, 5, 0.6), (4, 5, 0.8),
        ]
        n, d, val = random.choice(fracs)
        all_vals = [f[2] for f in fracs]
        distractors = random.sample([v for v in all_vals if v != val], 3)
        pool = [val] + distractors
        random.shuffle(pool)
        return {
            "type": "math",
            "text": f"What is {n}/{d} as a decimal?",
            "options": [str(o) for o in pool],
            "correct_index": pool.index(val),
        }
    else:
        divisor = random.randint(2, 12)
        quotient = random.randint(2, 20)
        opts, idx = _make_int_options(quotient, spread=8)
        return {"type": "math", "text": f"{divisor * quotient} ÷ {divisor} = ?", "options": opts, "correct_index": idx}


def _tier4() -> dict:
    variant = random.choice(["two_digit_mult", "multi_step"])
    if variant == "two_digit_mult":
        a, b = random.randint(11, 30), random.randint(11, 30)
        correct = a * b
        opts, idx = _make_int_options(correct, spread=50)
        return {"type": "math", "text": f"{a} × {b} = ?", "options": opts, "correct_index": idx}
    else:
        a = random.randint(10, 25)
        b = random.randint(5, 15)
        c = random.randint(2, 8)
        correct = (a + b) * c
        opts, idx = _make_int_options(correct, spread=30)
        return {"type": "math", "text": f"({a} + {b}) × {c} = ?", "options": opts, "correct_index": idx}


def generate_math_questions() -> list[dict]:
    """4 math questions: one each from tiers 1–4."""
    return [_tier1(), _tier2(), _tier3(), _tier4()]


# ── Static question pools ─────────────────────────────────────────────────────

GEOGRAPHY_POOL: list[dict] = [
    {"text": "Which country has the capital Paris?", "options": ["France", "Belgium", "Spain", "Italy"], "correct_index": 0},
    {"text": "Which country has the capital Berlin?", "options": ["Austria", "Germany", "Switzerland", "Poland"], "correct_index": 1},
    {"text": "Which country has the capital Tokyo?", "options": ["China", "South Korea", "Japan", "Vietnam"], "correct_index": 2},
    {"text": "Which country has the capital Canberra?", "options": ["New Zealand", "Australia", "Canada", "South Africa"], "correct_index": 1},
    {"text": "Which country has the capital Ottawa?", "options": ["USA", "Canada", "Mexico", "Australia"], "correct_index": 1},
    {"text": "Which country has the capital Brasília?", "options": ["Argentina", "Colombia", "Brazil", "Chile"], "correct_index": 2},
    {"text": "Which country has the capital Cairo?", "options": ["Morocco", "Tunisia", "Libya", "Egypt"], "correct_index": 3},
    {"text": "Which country has the capital Nairobi?", "options": ["Tanzania", "Uganda", "Kenya", "Ethiopia"], "correct_index": 2},
    {"text": "Which country has the capital Bangkok?", "options": ["Myanmar", "Cambodia", "Laos", "Thailand"], "correct_index": 3},
    {"text": "Which country has the capital Jakarta?", "options": ["Malaysia", "Philippines", "Indonesia", "Singapore"], "correct_index": 2},
    {"text": "Which country has the capital Seoul?", "options": ["North Korea", "Japan", "China", "South Korea"], "correct_index": 3},
    {"text": "Which country has the capital Beijing?", "options": ["Japan", "China", "South Korea", "Taiwan"], "correct_index": 1},
    {"text": "Which country has the capital Moscow?", "options": ["Ukraine", "Belarus", "Russia", "Kazakhstan"], "correct_index": 2},
    {"text": "Which country has the capital Ankara?", "options": ["Greece", "Iran", "Turkey", "Iraq"], "correct_index": 2},
    {"text": "Which country has the capital Buenos Aires?", "options": ["Chile", "Uruguay", "Brazil", "Argentina"], "correct_index": 3},
    {"text": "Which country has the capital Lima?", "options": ["Bolivia", "Ecuador", "Colombia", "Peru"], "correct_index": 3},
    {"text": "Which country has the capital Bogotá?", "options": ["Venezuela", "Ecuador", "Colombia", "Peru"], "correct_index": 2},
    {"text": "Which country has the capital Santiago?", "options": ["Argentina", "Bolivia", "Peru", "Chile"], "correct_index": 3},
    {"text": "Which country has the capital Pretoria?", "options": ["Zimbabwe", "Mozambique", "Namibia", "South Africa"], "correct_index": 3},
    {"text": "Which country has the capital Accra?", "options": ["Nigeria", "Senegal", "Côte d'Ivoire", "Ghana"], "correct_index": 3},
    {"text": "Which country has the capital Addis Ababa?", "options": ["Somalia", "Sudan", "Ethiopia", "Eritrea"], "correct_index": 2},
    {"text": "Which country has the capital Algiers?", "options": ["Morocco", "Tunisia", "Libya", "Algeria"], "correct_index": 3},
    {"text": "Which country has the capital Rabat?", "options": ["Algeria", "Tunisia", "Morocco", "Libya"], "correct_index": 2},
    {"text": "Which country has the capital Riyadh?", "options": ["UAE", "Kuwait", "Qatar", "Saudi Arabia"], "correct_index": 3},
    {"text": "Which country has the capital Tehran?", "options": ["Iraq", "Afghanistan", "Iran", "Pakistan"], "correct_index": 2},
    {"text": "Which country has the capital Baghdad?", "options": ["Syria", "Iran", "Jordan", "Iraq"], "correct_index": 3},
    {"text": "Which country has the capital Islamabad?", "options": ["India", "Afghanistan", "Pakistan", "Bangladesh"], "correct_index": 2},
    {"text": "Which country has the capital New Delhi?", "options": ["Pakistan", "Nepal", "Bangladesh", "India"], "correct_index": 3},
    {"text": "Which country has the capital Dhaka?", "options": ["India", "Myanmar", "Sri Lanka", "Bangladesh"], "correct_index": 3},
    {"text": "Which country has the capital Kathmandu?", "options": ["Bhutan", "Nepal", "Tibet", "India"], "correct_index": 1},
    {"text": "Which country has the capital Colombo?", "options": ["Maldives", "India", "Sri Lanka", "Myanmar"], "correct_index": 2},
    {"text": "Which country has the capital Hanoi?", "options": ["Laos", "Cambodia", "Myanmar", "Vietnam"], "correct_index": 3},
    {"text": "Which country has the capital Kuala Lumpur?", "options": ["Thailand", "Indonesia", "Malaysia", "Brunei"], "correct_index": 2},
    {"text": "Which country has the capital Manila?", "options": ["Indonesia", "Malaysia", "Taiwan", "Philippines"], "correct_index": 3},
    {"text": "Which country has the capital Taipei?", "options": ["China", "South Korea", "Japan", "Taiwan"], "correct_index": 3},
    {"text": "Which country has the capital Ulaanbaatar?", "options": ["Kazakhstan", "Kyrgyzstan", "Mongolia", "Tajikistan"], "correct_index": 2},
    {"text": "Which country has the capital Kabul?", "options": ["Iran", "Pakistan", "Tajikistan", "Afghanistan"], "correct_index": 3},
    {"text": "Which country has the capital Rome?", "options": ["Spain", "Portugal", "Greece", "Italy"], "correct_index": 3},
    {"text": "Which country has the capital Madrid?", "options": ["Portugal", "Spain", "France", "Italy"], "correct_index": 1},
    {"text": "Which country has the capital Lisbon?", "options": ["Spain", "Portugal", "France", "Brazil"], "correct_index": 1},
    {"text": "Which country has the capital Athens?", "options": ["Turkey", "Bulgaria", "Cyprus", "Greece"], "correct_index": 3},
    {"text": "Which country has the capital Warsaw?", "options": ["Czech Republic", "Hungary", "Slovakia", "Poland"], "correct_index": 3},
    {"text": "Which country has the capital Prague?", "options": ["Slovakia", "Austria", "Czech Republic", "Hungary"], "correct_index": 2},
    {"text": "Which country has the capital Vienna?", "options": ["Germany", "Switzerland", "Austria", "Hungary"], "correct_index": 2},
    {"text": "Which country has the capital Bern?", "options": ["Austria", "Liechtenstein", "Switzerland", "Luxembourg"], "correct_index": 2},
    {"text": "Which country has the capital Amsterdam?", "options": ["Belgium", "Denmark", "Luxembourg", "Netherlands"], "correct_index": 3},
    {"text": "Which country has the capital Brussels?", "options": ["Netherlands", "Luxembourg", "France", "Belgium"], "correct_index": 3},
    {"text": "Which country has the capital Copenhagen?", "options": ["Sweden", "Norway", "Finland", "Denmark"], "correct_index": 3},
    {"text": "Which country has the capital Stockholm?", "options": ["Norway", "Sweden", "Finland", "Denmark"], "correct_index": 1},
    {"text": "Which country has the capital Oslo?", "options": ["Sweden", "Norway", "Denmark", "Finland"], "correct_index": 1},
    {"text": "Which country has the capital Helsinki?", "options": ["Estonia", "Latvia", "Sweden", "Finland"], "correct_index": 3},
    {"text": "Which country has the capital Reykjavik?", "options": ["Norway", "Greenland", "Faroe Islands", "Iceland"], "correct_index": 3},
    {"text": "Which country has the capital Dublin?", "options": ["Scotland", "Wales", "Northern Ireland", "Ireland"], "correct_index": 3},
    {"text": "Which country has the capital Kyiv?", "options": ["Belarus", "Moldova", "Russia", "Ukraine"], "correct_index": 3},
    {"text": "Which country has the capital Minsk?", "options": ["Ukraine", "Belarus", "Lithuania", "Latvia"], "correct_index": 1},
    {"text": "Which country has the capital Bucharest?", "options": ["Bulgaria", "Hungary", "Moldova", "Romania"], "correct_index": 3},
    {"text": "Which country has the capital Sofia?", "options": ["Romania", "Serbia", "Bulgaria", "North Macedonia"], "correct_index": 2},
    {"text": "Which country has the capital Belgrade?", "options": ["Croatia", "Bosnia", "Slovenia", "Serbia"], "correct_index": 3},
    {"text": "Which country has the capital Zagreb?", "options": ["Slovenia", "Bosnia", "Serbia", "Croatia"], "correct_index": 3},
    {"text": "Which country has the capital Sarajevo?", "options": ["Serbia", "Montenegro", "Croatia", "Bosnia and Herzegovina"], "correct_index": 3},
    {"text": "Which country has the capital Podgorica?", "options": ["Serbia", "Albania", "Montenegro", "Kosovo"], "correct_index": 2},
    {"text": "Which country has the capital Tirana?", "options": ["Kosovo", "North Macedonia", "Albania", "Montenegro"], "correct_index": 2},
    {"text": "Which country has the capital Skopje?", "options": ["Albania", "Bulgaria", "Kosovo", "North Macedonia"], "correct_index": 3},
    {"text": "Which country has the capital Tallinn?", "options": ["Latvia", "Lithuania", "Finland", "Estonia"], "correct_index": 3},
    {"text": "Which country has the capital Riga?", "options": ["Estonia", "Latvia", "Lithuania", "Belarus"], "correct_index": 1},
    {"text": "Which country has the capital Vilnius?", "options": ["Latvia", "Estonia", "Belarus", "Lithuania"], "correct_index": 3},
    {"text": "Which country has the capital Astana?", "options": ["Uzbekistan", "Kyrgyzstan", "Turkmenistan", "Kazakhstan"], "correct_index": 3},
    {"text": "Which country has the capital Tashkent?", "options": ["Kazakhstan", "Uzbekistan", "Tajikistan", "Kyrgyzstan"], "correct_index": 1},
    {"text": "Which country has the capital Baku?", "options": ["Armenia", "Georgia", "Turkey", "Azerbaijan"], "correct_index": 3},
    {"text": "Which country has the capital Yerevan?", "options": ["Georgia", "Turkey", "Armenia", "Azerbaijan"], "correct_index": 2},
    {"text": "Which country has the capital Tbilisi?", "options": ["Armenia", "Azerbaijan", "Georgia", "Turkey"], "correct_index": 2},
    {"text": "Which country has the capital Muscat?", "options": ["UAE", "Bahrain", "Qatar", "Oman"], "correct_index": 3},
    {"text": "Which country has the capital Abu Dhabi?", "options": ["Qatar", "Bahrain", "Kuwait", "UAE"], "correct_index": 3},
    {"text": "Which country has the capital Doha?", "options": ["UAE", "Kuwait", "Bahrain", "Qatar"], "correct_index": 3},
    {"text": "Which country has the capital Kuwait City?", "options": ["Iraq", "Bahrain", "Qatar", "Kuwait"], "correct_index": 3},
    {"text": "Which country has the capital Amman?", "options": ["Syria", "Lebanon", "Palestine", "Jordan"], "correct_index": 3},
    {"text": "Which country has the capital Beirut?", "options": ["Syria", "Jordan", "Cyprus", "Lebanon"], "correct_index": 3},
    {"text": "Which country has the capital Damascus?", "options": ["Lebanon", "Jordan", "Iraq", "Syria"], "correct_index": 3},
    {"text": "Which country has the capital Nicosia?", "options": ["Malta", "Greece", "Lebanon", "Cyprus"], "correct_index": 3},
    {"text": "Which country has the capital Valletta?", "options": ["Cyprus", "Malta", "Monaco", "San Marino"], "correct_index": 1},
    {"text": "Which country has the capital Luxembourg City?", "options": ["Belgium", "Netherlands", "France", "Luxembourg"], "correct_index": 3},
    {"text": "Which country has the capital Windhoek?", "options": ["Botswana", "Zambia", "Angola", "Namibia"], "correct_index": 3},
    {"text": "Which country has the capital Gaborone?", "options": ["Zimbabwe", "Namibia", "Botswana", "Lesotho"], "correct_index": 2},
    {"text": "Which country has the capital Lusaka?", "options": ["Zimbabwe", "Zambia", "Malawi", "Tanzania"], "correct_index": 1},
    {"text": "Which country has the capital Harare?", "options": ["Zambia", "Mozambique", "Botswana", "Zimbabwe"], "correct_index": 3},
    {"text": "Which country has the capital Maputo?", "options": ["Tanzania", "Zimbabwe", "Mozambique", "Madagascar"], "correct_index": 2},
    {"text": "Which country has the capital Antananarivo?", "options": ["Mozambique", "Réunion", "Comoros", "Madagascar"], "correct_index": 3},
    {"text": "Which country has the capital Dar es Salaam?", "options": ["Kenya", "Uganda", "Rwanda", "Tanzania"], "correct_index": 3},
    {"text": "Which country has the capital Kampala?", "options": ["Rwanda", "Kenya", "Uganda", "Tanzania"], "correct_index": 2},
    {"text": "Which country has the capital Kigali?", "options": ["Burundi", "Uganda", "Congo", "Rwanda"], "correct_index": 3},
    {"text": "Which country has the capital Kinshasa?", "options": ["Congo-Brazzaville", "Angola", "Cameroon", "DR Congo"], "correct_index": 3},
    {"text": "Which country has the capital Yaoundé?", "options": ["Gabon", "Congo", "Nigeria", "Cameroon"], "correct_index": 3},
    {"text": "Which country has the capital Libreville?", "options": ["Congo", "Equatorial Guinea", "Cameroon", "Gabon"], "correct_index": 3},
    {"text": "Which country has the capital Dakar?", "options": ["Guinea", "Gambia", "Mali", "Senegal"], "correct_index": 3},
    {"text": "Which country has the capital Bamako?", "options": ["Senegal", "Burkina Faso", "Guinea", "Mali"], "correct_index": 3},
    {"text": "Which country has the capital Ouagadougou?", "options": ["Mali", "Niger", "Senegal", "Burkina Faso"], "correct_index": 3},
    {"text": "Which country has the capital Niamey?", "options": ["Mali", "Chad", "Burkina Faso", "Niger"], "correct_index": 3},
    {"text": "Which country has the capital N'Djamena?", "options": ["Niger", "Sudan", "CAR", "Chad"], "correct_index": 3},
    {"text": "Which country has the capital Khartoum?", "options": ["Ethiopia", "Egypt", "Chad", "Sudan"], "correct_index": 3},
    {"text": "Which country has the capital Mogadishu?", "options": ["Eritrea", "Djibouti", "Ethiopia", "Somalia"], "correct_index": 3},
    {"text": "Which country has the capital Wellington?", "options": ["Australia", "Fiji", "Samoa", "New Zealand"], "correct_index": 3},
    {"text": "Which country has the capital Port Moresby?", "options": ["Timor-Leste", "Solomon Islands", "Vanuatu", "Papua New Guinea"], "correct_index": 3},
    {"text": "Which country has the capital Washington D.C.?", "options": ["Canada", "Mexico", "Cuba", "USA"], "correct_index": 3},
    {"text": "Which country has the capital Mexico City?", "options": ["Guatemala", "Cuba", "USA", "Mexico"], "correct_index": 3},
    {"text": "Which country has the capital Havana?", "options": ["Dominican Republic", "Jamaica", "Haiti", "Cuba"], "correct_index": 3},
    {"text": "Which country has the capital Bogotá?", "options": ["Venezuela", "Ecuador", "Peru", "Colombia"], "correct_index": 3},
    {"text": "Which country has the capital Caracas?", "options": ["Colombia", "Guyana", "Ecuador", "Venezuela"], "correct_index": 3},
    {"text": "Which country has the capital Quito?", "options": ["Peru", "Bolivia", "Colombia", "Ecuador"], "correct_index": 3},
    {"text": "Which country has the capital La Paz?", "options": ["Peru", "Paraguay", "Chile", "Bolivia"], "correct_index": 3},
    {"text": "Which country has the capital Asunción?", "options": ["Bolivia", "Uruguay", "Argentina", "Paraguay"], "correct_index": 3},
    {"text": "Which country has the capital Montevideo?", "options": ["Argentina", "Paraguay", "Brazil", "Uruguay"], "correct_index": 3},
    {"text": "Which country has the capital Phnom Penh?", "options": ["Laos", "Myanmar", "Vietnam", "Cambodia"], "correct_index": 3},
    {"text": "Which country has the capital Vientiane?", "options": ["Vietnam", "Cambodia", "Myanmar", "Laos"], "correct_index": 3},
    {"text": "Which country has the capital Naypyidaw?", "options": ["Laos", "Thailand", "Cambodia", "Myanmar"], "correct_index": 3},
    {"text": "Which country has the capital Pyongyang?", "options": ["South Korea", "China", "Mongolia", "North Korea"], "correct_index": 3},
    {"text": "Which country has the capital Bishkek?", "options": ["Tajikistan", "Uzbekistan", "Kazakhstan", "Kyrgyzstan"], "correct_index": 3},
    {"text": "Which country has the capital Dushanbe?", "options": ["Kyrgyzstan", "Uzbekistan", "Afghanistan", "Tajikistan"], "correct_index": 3},
    {"text": "Which country has the capital Ashgabat?", "options": ["Uzbekistan", "Afghanistan", "Iran", "Turkmenistan"], "correct_index": 3},
    {"text": "Which country has the capital Thimphu?", "options": ["Nepal", "India", "Sikkim", "Bhutan"], "correct_index": 3},
    {"text": "Which country has the capital Male?", "options": ["Sri Lanka", "Seychelles", "Comoros", "Maldives"], "correct_index": 3},
    {"text": "Which country has the capital Budapest?", "options": ["Romania", "Slovakia", "Austria", "Hungary"], "correct_index": 3},
    {"text": "Which country has the capital Bratislava?", "options": ["Hungary", "Austria", "Czech Republic", "Slovakia"], "correct_index": 3},
    {"text": "Which country has the capital Ljubljana?", "options": ["Croatia", "Bosnia", "Serbia", "Slovenia"], "correct_index": 3},
    {"text": "Which country has the capital Luanda?", "options": ["Congo", "Zambia", "Namibia", "Angola"], "correct_index": 3},
    {"text": "Which country has the capital Lilongwe?", "options": ["Zambia", "Tanzania", "Mozambique", "Malawi"], "correct_index": 3},
    {"text": "Which country has the capital Abuja?", "options": ["Ghana", "Cameroon", "Benin", "Nigeria"], "correct_index": 3},
    {"text": "Which country has the capital Freetown?", "options": ["Liberia", "Guinea", "Gambia", "Sierra Leone"], "correct_index": 3},
    {"text": "Which country has the capital Monrovia?", "options": ["Sierra Leone", "Côte d'Ivoire", "Guinea", "Liberia"], "correct_index": 3},
    {"text": "Which country has the capital Conakry?", "options": ["Gambia", "Sierra Leone", "Senegal", "Guinea"], "correct_index": 3},
    {"text": "Which country has the capital Tripoli?", "options": ["Tunisia", "Egypt", "Algeria", "Libya"], "correct_index": 3},
    {"text": "Which country has the capital Maseru?", "options": ["Eswatini", "Botswana", "Zimbabwe", "Lesotho"], "correct_index": 3},
    {"text": "Which country has the capital Mbabane?", "options": ["Lesotho", "Botswana", "Namibia", "Eswatini"], "correct_index": 3},
    {"text": "Which country has the capital Asmara?", "options": ["Somalia", "Djibouti", "Ethiopia", "Eritrea"], "correct_index": 3},
    {"text": "Which country has the capital Djibouti?", "options": ["Eritrea", "Somalia", "Ethiopia", "Djibouti"], "correct_index": 3},
    {"text": "Which country has the capital Suva?", "options": ["Tonga", "Samoa", "Vanuatu", "Fiji"], "correct_index": 3},
    {"text": "Which country has the capital Honiara?", "options": ["Vanuatu", "Fiji", "Papua New Guinea", "Solomon Islands"], "correct_index": 3},
    {"text": "Which country has the capital Port Vila?", "options": ["Solomon Islands", "Fiji", "Samoa", "Vanuatu"], "correct_index": 3},
    {"text": "Which country has the capital Guatemala City?", "options": ["Honduras", "El Salvador", "Belize", "Guatemala"], "correct_index": 3},
    {"text": "Which country has the capital Tegucigalpa?", "options": ["Guatemala", "Nicaragua", "El Salvador", "Honduras"], "correct_index": 3},
    {"text": "Which country has the capital San Salvador?", "options": ["Costa Rica", "Honduras", "Nicaragua", "El Salvador"], "correct_index": 3},
    {"text": "Which country has the capital Managua?", "options": ["Honduras", "Costa Rica", "Panama", "Nicaragua"], "correct_index": 3},
    {"text": "Which country has the capital San José?", "options": ["Panama", "Nicaragua", "Guatemala", "Costa Rica"], "correct_index": 3},
    {"text": "Which country has the capital Panama City?", "options": ["Colombia", "Costa Rica", "Nicaragua", "Panama"], "correct_index": 3},
    {"text": "Which country has the capital Georgetown?", "options": ["Suriname", "Trinidad", "Belize", "Guyana"], "correct_index": 3},
    {"text": "Which country has the capital Paramaribo?", "options": ["Guyana", "French Guiana", "Brazil", "Suriname"], "correct_index": 3},
    {"text": "Which country has the capital Kingston?", "options": ["Cuba", "Haiti", "Barbados", "Jamaica"], "correct_index": 3},
    {"text": "Which country has the capital Port-au-Prince?", "options": ["Jamaica", "Cuba", "Dominican Republic", "Haiti"], "correct_index": 3},
    {"text": "Which country has the capital Santo Domingo?", "options": ["Haiti", "Puerto Rico", "Cuba", "Dominican Republic"], "correct_index": 3},
    {"text": "Which country has the capital Bandar Seri Begawan?", "options": ["Malaysia", "Timor-Leste", "Indonesia", "Brunei"], "correct_index": 3},
    {"text": "Which country has the capital Nuku'alofa?", "options": ["Samoa", "Vanuatu", "Fiji", "Tonga"], "correct_index": 3},
    {"text": "Which country has the capital Apia?", "options": ["Tonga", "Fiji", "Vanuatu", "Samoa"], "correct_index": 3},
    {"text": "Which country has the capital Dili?", "options": ["Papua New Guinea", "Vanuatu", "Solomon Islands", "Timor-Leste"], "correct_index": 3},
    {"text": "Which country has the capital Singapore?", "options": ["Malaysia", "Indonesia", "Brunei", "Singapore"], "correct_index": 3},
    {"text": "Which country has the capital Tunis?", "options": ["Algeria", "Tunisia", "Morocco", "Libya"], "correct_index": 1},
    {"text": "Which country has the capital Manama?", "options": ["Kuwait", "Qatar", "UAE", "Bahrain"], "correct_index": 3},
    {"text": "Which country has the capital Muscat?", "options": ["UAE", "Bahrain", "Qatar", "Oman"], "correct_index": 3},
    {"text": "Which country has the capital Ngerulmud?", "options": ["Micronesia", "Nauru", "Marshall Islands", "Palau"], "correct_index": 3},
    {"text": "Which country has the capital Palikir?", "options": ["Palau", "Marshall Islands", "Kiribati", "Micronesia"], "correct_index": 3},
    {"text": "Which country has the capital Majuro?", "options": ["Kiribati", "Nauru", "Palau", "Marshall Islands"], "correct_index": 3},
    {"text": "Which country has the capital Tarawa?", "options": ["Tuvalu", "Marshall Islands", "Nauru", "Kiribati"], "correct_index": 3},
    {"text": "Which country has the capital Funafuti?", "options": ["Kiribati", "Nauru", "Marshall Islands", "Tuvalu"], "correct_index": 3},
    {"text": "Which country has the capital Yaren?", "options": ["Palau", "Tuvalu", "Kiribati", "Nauru"], "correct_index": 3},
    {"text": "Which country has the capital Moroni?", "options": ["Maldives", "Seychelles", "Mauritius", "Comoros"], "correct_index": 3},
    {"text": "Which country has the capital Victoria?", "options": ["Comoros", "Mauritius", "Maldives", "Seychelles"], "correct_index": 3},
    {"text": "Which country has the capital Port Louis?", "options": ["Seychelles", "Comoros", "Réunion", "Mauritius"], "correct_index": 3},
    {"text": "Which country has the capital Vaduz?", "options": ["San Marino", "Monaco", "Andorra", "Liechtenstein"], "correct_index": 3},
    {"text": "Which country has the capital Andorra la Vella?", "options": ["Monaco", "Liechtenstein", "San Marino", "Andorra"], "correct_index": 3},
    {"text": "Which country has the capital Valletta?", "options": ["Cyprus", "Malta", "Monaco", "San Marino"], "correct_index": 1},
    {"text": "Which country has the capital Bujumbura?", "options": ["Rwanda", "Congo", "Tanzania", "Burundi"], "correct_index": 3},
    {"text": "Which country has the capital Brazzaville?", "options": ["DR Congo", "Gabon", "Cameroon", "Republic of Congo"], "correct_index": 3},
    {"text": "Which country has the capital Malabo?", "options": ["Gabon", "Cameroon", "São Tomé", "Equatorial Guinea"], "correct_index": 3},
    {"text": "Which country has the capital Praia?", "options": ["São Tomé", "Gambia", "Guinea-Bissau", "Cape Verde"], "correct_index": 3},
    {"text": "Which country has the capital Bissau?", "options": ["Gambia", "Senegal", "Guinea", "Guinea-Bissau"], "correct_index": 3},
    {"text": "Which country has the capital Banjul?", "options": ["Senegal", "Guinea-Bissau", "Sierra Leone", "Gambia"], "correct_index": 3},
    {"text": "Which country has the capital Yamoussoukro?", "options": ["Ghana", "Guinea", "Liberia", "Côte d'Ivoire"], "correct_index": 3},
    {"text": "Which country has the capital São Tomé?", "options": ["Equatorial Guinea", "Cape Verde", "Gabon", "São Tomé and Príncipe"], "correct_index": 3},
    {"text": "Which country has the capital Nur-Sultan?", "options": ["Uzbekistan", "Kyrgyzstan", "Tajikistan", "Kazakhstan"], "correct_index": 3},
]

WORD_POOL: list[dict] = [
    {"text": "What does 'ubiquitous' mean?", "options": ["Rare and hard to find", "Present everywhere", "Relating to cities", "Extremely beautiful"], "correct_index": 1},
    {"text": "What does 'ephemeral' mean?", "options": ["Lasting a very short time", "Extremely heavy", "Related to ghosts", "Having a strong smell"], "correct_index": 0},
    {"text": "What does 'loquacious' mean?", "options": ["Very quiet", "Tending to talk a lot", "Extremely logical", "Moving quickly"], "correct_index": 1},
    {"text": "What does 'tenacious' mean?", "options": ["Very thin", "Generous with money", "Holding firmly to something", "Easy to break"], "correct_index": 2},
    {"text": "What does 'gregarious' mean?", "options": ["Fond of company", "Very aggressive", "Extremely greedy", "Relating to sheep"], "correct_index": 0},
    {"text": "What does 'ambiguous' mean?", "options": ["Very clear", "Open to more than one interpretation", "Extremely large", "Moving in both directions"], "correct_index": 1},
    {"text": "What does 'benevolent' mean?", "options": ["Well meaning and kind", "Very wealthy", "Extremely fast", "Hard to understand"], "correct_index": 0},
    {"text": "What does 'malevolent' mean?", "options": ["Extremely kind", "Having or showing a wish to do evil", "Very poorly made", "Relating to illness"], "correct_index": 1},
    {"text": "What does 'verbose' mean?", "options": ["Using too many words", "Completely silent", "Relating to verbs", "Extremely truthful"], "correct_index": 0},
    {"text": "What does 'laconic' mean?", "options": ["Very talkative", "Using very few words", "Relating to lakes", "Extremely lazy"], "correct_index": 1},
    {"text": "What does 'diligent' mean?", "options": ["Very careless", "Having a careful and persistent effort", "Extremely difficult", "Relating to digestion"], "correct_index": 1},
    {"text": "What does 'pragmatic' mean?", "options": ["Dealing with things practically", "Extremely dramatic", "Very idealistic", "Related to Prague"], "correct_index": 0},
    {"text": "What does 'stoic' mean?", "options": ["Very emotional", "Enduring pain without complaint", "Extremely loud", "Relating to storage"], "correct_index": 1},
    {"text": "What does 'erudite' mean?", "options": ["Very rude", "Having great knowledge", "Extremely red", "Related to eruptions"], "correct_index": 1},
    {"text": "What does 'pedantic' mean?", "options": ["Overly concerned with minor details", "Related to feet", "Very generous", "Extremely fast"], "correct_index": 0},
    {"text": "What does 'candid' mean?", "options": ["Very formal", "Truthful and straightforward", "Relating to candles", "Extremely shy"], "correct_index": 1},
    {"text": "What does 'cynical' mean?", "options": ["Very optimistic", "Distrustful of people's motives", "Relating to cycles", "Extremely kind"], "correct_index": 1},
    {"text": "What does 'pensive' mean?", "options": ["Very expensive", "Engaged in deep thought", "Extremely happy", "Relating to pens"], "correct_index": 1},
    {"text": "What does 'arduous' mean?", "options": ["Very easy", "Involving great effort", "Relating to music", "Extremely cold"], "correct_index": 1},
    {"text": "What does 'frugal' mean?", "options": ["Very generous", "Sparing or economical", "Relating to fruit", "Extremely wasteful"], "correct_index": 1},
    {"text": "What does 'nonchalant' mean?", "options": ["Very excited", "Casually calm and relaxed", "Extremely nervous", "Related to France"], "correct_index": 1},
    {"text": "What does 'resilient' mean?", "options": ["Very fragile", "Able to recover quickly from difficulty", "Relating to silence", "Extremely loud"], "correct_index": 1},
    {"text": "What does 'eloquent' mean?", "options": ["Very quiet", "Fluent and persuasive in speaking", "Extremely logical", "Related to electricity"], "correct_index": 1},
    {"text": "What does 'aloof' mean?", "options": ["Very friendly", "Not friendly or forthcoming", "Relating to rooftops", "Extremely loud"], "correct_index": 1},
    {"text": "What does 'covert' mean?", "options": ["Very open", "Not openly acknowledged", "Relating to covers", "Extremely obvious"], "correct_index": 1},
    {"text": "What does 'overt' mean?", "options": ["Hidden from view", "Done openly", "Relating to ovens", "Extremely covert"], "correct_index": 1},
    {"text": "What does 'innate' mean?", "options": ["Learned over time", "Inborn or natural", "Related to interior design", "Extremely complex"], "correct_index": 1},
    {"text": "What does 'obsolete' mean?", "options": ["Cutting edge", "No longer in use", "Extremely stubborn", "Very obvious"], "correct_index": 1},
    {"text": "What does 'astute' mean?", "options": ["Very slow", "Having a sharp mind", "Relating to stars", "Extremely stubborn"], "correct_index": 1},
    {"text": "What does 'frivolous' mean?", "options": ["Very serious", "Not having any serious purpose", "Relating to cold", "Extremely hungry"], "correct_index": 1},
    {"text": "What does 'furtive' mean?", "options": ["Very brave", "Attempting to avoid notice", "Relating to fur", "Extremely fast"], "correct_index": 1},
    {"text": "What does 'altruistic' mean?", "options": ["Selfishly motivated", "Showing concern for others", "Relating to altitude", "Extremely artistic"], "correct_index": 1},
    {"text": "What does 'ostentatious' mean?", "options": ["Very modest", "Showing off wealth or knowledge", "Related to bones", "Extremely quiet"], "correct_index": 1},
    {"text": "What does 'reticent' mean?", "options": ["Very talkative", "Not revealing one's thoughts readily", "Related to nets", "Extremely recent"], "correct_index": 1},
    {"text": "What does 'succinct' mean?", "options": ["Very long and detailed", "Briefly and clearly expressed", "Relating to success", "Extremely complex"], "correct_index": 1},
    {"text": "What does 'sycophant' mean?", "options": ["A type of tree", "A person who flatters to gain favour", "A musical instrument", "A medical condition"], "correct_index": 1},
    {"text": "What does 'vindictive' mean?", "options": ["Very forgiving", "Having a desire for revenge", "Relating to wine", "Extremely victorious"], "correct_index": 1},
    {"text": "What does 'wary' mean?", "options": ["Very trusting", "Feeling cautious about possible dangers", "Extremely warm", "Related to war"], "correct_index": 1},
    {"text": "What does 'zealous' mean?", "options": ["Completely indifferent", "Having great energy and enthusiasm", "Very jealous", "Relating to zebras"], "correct_index": 1},
    {"text": "What does 'acumen' mean?", "options": ["A type of plant", "The ability to make good judgements", "A sharp pain", "A type of exercise"], "correct_index": 1},
    {"text": "What does 'banal' mean?", "options": ["Very exciting", "So lacking in originality as to be boring", "Relating to bananas", "Extremely useful"], "correct_index": 1},
    {"text": "What does 'capricious' mean?", "options": ["Very predictable", "Given to sudden changes of mood", "Related to goats", "Extremely careful"], "correct_index": 1},
    {"text": "What does 'deft' mean?", "options": ["Very clumsy", "Neatly skilful and quick", "Relating to deafness", "Extremely slow"], "correct_index": 1},
    {"text": "What does 'enigmatic' mean?", "options": ["Very obvious", "Mysterious and difficult to understand", "Related to engines", "Extremely magnetic"], "correct_index": 1},
    {"text": "What does 'fallacious' mean?", "options": ["Based on truth", "Based on a mistaken belief", "Very graceful", "Relating to falling"], "correct_index": 1},
    {"text": "What does 'garrulous' mean?", "options": ["Very quiet", "Excessively talkative", "Related to garlic", "Extremely strong"], "correct_index": 1},
    {"text": "What does 'hapless' mean?", "options": ["Very lucky", "Unfortunate and unlucky", "Related to happiness", "Extremely energetic"], "correct_index": 1},
    {"text": "What does 'impetuous' mean?", "options": ["Very cautious", "Acting quickly without thinking", "Related to the emperor", "Extremely patient"], "correct_index": 1},
    {"text": "What does 'inept' mean?", "options": ["Very skilled", "Lacking skill", "Related to insects", "Extremely quick"], "correct_index": 1},
    {"text": "What does 'jocular' mean?", "options": ["Very serious", "Fond of joking", "Related to joints", "Extremely popular"], "correct_index": 1},
    {"text": "What does 'languid' mean?", "options": ["Very energetic", "Weak or slow from tiredness", "Related to language", "Extremely angry"], "correct_index": 1},
    {"text": "What does 'mendacious' mean?", "options": ["Very honest", "Not telling the truth", "Related to medicine", "Extremely polite"], "correct_index": 1},
    {"text": "What does 'nebulous' mean?", "options": ["Very clear", "Not clearly defined", "Related to clouds", "Extremely negative"], "correct_index": 1},
    {"text": "What does 'opulent' mean?", "options": ["Very poor", "Ostentatiously rich", "Related to optics", "Extremely open"], "correct_index": 1},
    {"text": "What does 'parsimonious' mean?", "options": ["Very generous", "Unwilling to spend money", "Related to parsons", "Extremely patient"], "correct_index": 1},
    {"text": "What does 'querulous' mean?", "options": ["Very happy", "Complaining persistently", "Related to questions", "Extremely quiet"], "correct_index": 1},
    {"text": "What does 'rancorous' mean?", "options": ["Very forgiving", "Feeling bitterness or resentment", "Related to ranches", "Extremely random"], "correct_index": 1},
    {"text": "What does 'sagacious' mean?", "options": ["Very foolish", "Having great wisdom", "Related to sage", "Extremely aggressive"], "correct_index": 1},
    {"text": "What does 'taciturn' mean?", "options": ["Very talkative", "Reserved or uncommunicative", "Related to tactics", "Extremely fast"], "correct_index": 1},
    {"text": "What does 'unctuous' mean?", "options": ["Very sincere", "Excessively flattering", "Related to uncles", "Extremely unusual"], "correct_index": 1},
    {"text": "What does 'vehement' mean?", "options": ["Very calm", "Showing strong feeling", "Related to vehicles", "Extremely vague"], "correct_index": 1},
    {"text": "What does 'wistful' mean?", "options": ["Very angry", "Having a feeling of vague longing", "Related to wisdom", "Extremely wishful"], "correct_index": 1},
    {"text": "What does 'acrimonious' mean?", "options": ["Very pleasant", "Angry and bitter", "Related to acid", "Extremely accurate"], "correct_index": 1},
    {"text": "What does 'blithe' mean?", "options": ["Very sad", "Showing casual indifference", "Related to blindness", "Extremely bright"], "correct_index": 1},
    {"text": "What does 'clandestine' mean?", "options": ["Very public", "Kept secret", "Related to clans", "Extremely clean"], "correct_index": 1},
    {"text": "What does 'diffident' mean?", "options": ["Very confident", "Modest or shy", "Related to differences", "Extremely different"], "correct_index": 1},
    {"text": "What does 'exacerbate' mean?", "options": ["To improve", "To make worse", "To exaggerate", "To examine carefully"], "correct_index": 1},
    {"text": "What does 'fortuitous' mean?", "options": ["Very unfortunate", "Happening by lucky chance", "Related to fortresses", "Extremely strong"], "correct_index": 1},
    {"text": "What does 'ignominious' mean?", "options": ["Very honourable", "Deserving disgrace", "Related to ignorance", "Extremely illuminated"], "correct_index": 1},
    {"text": "What does 'laudable' mean?", "options": ["Very loud", "Deserving praise", "Related to laughter", "Extremely lavish"], "correct_index": 1},
    {"text": "What does 'magnanimous' mean?", "options": ["Very petty", "Generous in forgiving", "Related to magnets", "Extremely large"], "correct_index": 1},
    {"text": "What does 'nefarious' mean?", "options": ["Very virtuous", "Wicked or criminal", "Related to nerves", "Extremely nervous"], "correct_index": 1},
    {"text": "What does 'obsequious' mean?", "options": ["Very assertive", "Excessively eager to serve", "Related to obstacles", "Extremely obvious"], "correct_index": 1},
    {"text": "What does 'perfidious' mean?", "options": ["Very loyal", "Deceitful and untrustworthy", "Related to perfume", "Extremely perfect"], "correct_index": 1},
    {"text": "What does 'recalcitrant' mean?", "options": ["Very cooperative", "Stubbornly resistant to authority", "Related to calcium", "Extremely calm"], "correct_index": 1},
    {"text": "What does 'sardonic' mean?", "options": ["Very sincere", "Grimly mocking", "Related to sardines", "Extremely sad"], "correct_index": 1},
    {"text": "What does 'trepidation' mean?", "options": ["Great confidence", "A feeling of fear about something", "A type of journey", "Extreme excitement"], "correct_index": 1},
    {"text": "What does 'vacuous' mean?", "options": ["Full of meaning", "Having or showing a lack of thought", "Related to vacuums", "Extremely vocal"], "correct_index": 1},
    {"text": "What does 'whimsical' mean?", "options": ["Very serious", "Playfully quaint or fanciful", "Related to whistles", "Extremely wise"], "correct_index": 1},
    {"text": "What does 'aberrant' mean?", "options": ["Perfectly normal", "Departing from what is normal", "Related to bears", "Extremely accurate"], "correct_index": 1},
    {"text": "What does 'auspicious' mean?", "options": ["Very unlucky", "Giving a sign of future success", "Related to suspicion", "Extremely suspicious"], "correct_index": 1},
    {"text": "What does 'bellicose' mean?", "options": ["Very peaceful", "Demonstrating aggression", "Related to bells", "Extremely beautiful"], "correct_index": 1},
    {"text": "What does 'circumspect' mean?", "options": ["Very reckless", "Wary and unwilling to take risks", "Related to circles", "Extremely specific"], "correct_index": 1},
    {"text": "What does 'disparate' mean?", "options": ["Very similar", "Fundamentally different", "Related to despair", "Extremely desperate"], "correct_index": 1},
    {"text": "What does 'fastidious' mean?", "options": ["Very sloppy", "Very attentive to detail", "Related to fasting", "Extremely fast"], "correct_index": 1},
    {"text": "What does 'hubris' mean?", "options": ["Great humility", "Excessive pride or arrogance", "A type of car", "A hybrid animal"], "correct_index": 1},
    {"text": "What does 'impecunious' mean?", "options": ["Very wealthy", "Having little or no money", "Related to money", "Extremely impulsive"], "correct_index": 1},
    {"text": "What does 'judicious' mean?", "options": ["Very unwise", "Having good judgement", "Related to judges", "Extremely judicial"], "correct_index": 1},
    {"text": "What does 'lugubrious' mean?", "options": ["Very cheerful", "Looking sad and dismal", "Related to luggage", "Extremely loud"], "correct_index": 1},
    {"text": "What does 'myopic' mean?", "options": ["Seeing far ahead", "Lacking imagination or foresight", "Related to music", "Extremely mysterious"], "correct_index": 1},
    {"text": "What does 'pernicious' mean?", "options": ["Very beneficial", "Having a harmful effect", "Related to pears", "Extremely permanent"], "correct_index": 1},
    {"text": "What does 'probity' mean?", "options": ["Great dishonesty", "Strong moral principles", "A type of test", "A legal procedure"], "correct_index": 1},
    {"text": "What does 'quixotic' mean?", "options": ["Very realistic", "Extremely idealistic and impractical", "Related to quick movements", "Extremely quick"], "correct_index": 1},
    {"text": "What does 'recondite' mean?", "options": ["Very well known", "Not known by many people", "Related to recycles", "Extremely recent"], "correct_index": 1},
    {"text": "What does 'salient' mean?", "options": ["Very unimportant", "Most noticeable or important", "Related to salt", "Extremely silent"], "correct_index": 1},
    {"text": "What does 'truculent' mean?", "options": ["Very gentle", "Quick to argue or fight", "Related to trucks", "Extremely true"], "correct_index": 1},
    {"text": "What does 'umbrage' mean?", "options": ["Great pleasure", "Offence or annoyance", "A type of shadow", "A shady tree"], "correct_index": 1},
    {"text": "What does 'vapid' mean?", "options": ["Very exciting", "Offering nothing stimulating", "Related to vapour", "Extremely rapid"], "correct_index": 1},
    {"text": "What does 'wanton' mean?", "options": ["Very controlled", "Deliberate and unprovoked", "Related to wanting", "Extremely wise"], "correct_index": 1},
    {"text": "What does 'xenophobia' mean?", "options": ["Love of foreign cultures", "Dislike of people from other countries", "Fear of animals", "Love of science"], "correct_index": 1},
    {"text": "What does 'zeal' mean?", "options": ["Complete indifference", "Great energy in pursuit of a cause", "A type of fish", "Extreme jealousy"], "correct_index": 1},
    {"text": "What does 'affable' mean?", "options": ["Very rude", "Friendly and easy to talk to", "Related to fables", "Extremely fashionable"], "correct_index": 1},
    {"text": "What does 'bilious' mean?", "options": ["Very cheerful", "Feeling or appearing unwell", "Related to bills", "Extremely brilliant"], "correct_index": 1},
    {"text": "What does 'cavalier' mean?", "options": ["Very careful", "Showing a lack of concern", "A type of horse", "Extremely brave"], "correct_index": 1},
    {"text": "What does 'dauntless' mean?", "options": ["Very fearful", "Showing fearlessness", "Related to dawn", "Extremely daunting"], "correct_index": 1},
    {"text": "What does 'ebullient' mean?", "options": ["Very gloomy", "Full of energy and enthusiasm", "Related to bubbles", "Extremely old"], "correct_index": 1},
    {"text": "What does 'candour' mean?", "options": ["A type of bird", "Frankness and openness", "Great bravery", "Musical talent"], "correct_index": 1},
    {"text": "What does 'acrimonious' mean?", "options": ["Very pleasant", "Bitter and angry", "Extremely accurate", "Related to actions"], "correct_index": 1},
    {"text": "What does 'complicit' mean?", "options": ["Very complex", "Involved in wrongdoing", "Completely explicit", "Related to compliments"], "correct_index": 1},
    {"text": "What does 'duplicitous' mean?", "options": ["Having two copies", "Deceitful", "Very complicated", "Extremely loud"], "correct_index": 1},
    {"text": "What does 'equivocal' mean?", "options": ["Perfectly clear", "Open to more than one interpretation", "Very equal", "Related to horses"], "correct_index": 1},
    {"text": "What does 'fervent' mean?", "options": ["Very cold", "Having intense feeling", "Related to fermentation", "Extremely distant"], "correct_index": 1},
]

SPEED_POOL: list[dict] = [
    {"text": "Which of these is a prime number?", "options": ["15", "21", "17", "25"], "correct_index": 2},
    {"text": "Which of these is a prime number?", "options": ["9", "11", "15", "21"], "correct_index": 1},
    {"text": "Which of these is a prime number?", "options": ["27", "33", "35", "29"], "correct_index": 3},
    {"text": "Which of these is a prime number?", "options": ["49", "51", "53", "57"], "correct_index": 2},
    {"text": "Which of these is a prime number?", "options": ["39", "41", "45", "49"], "correct_index": 1},
    {"text": "Which of these is NOT a prime number?", "options": ["2", "3", "4", "5"], "correct_index": 2},
    {"text": "Which of these is NOT a prime number?", "options": ["7", "11", "13", "15"], "correct_index": 3},
    {"text": "Which of these is NOT a prime number?", "options": ["17", "19", "21", "23"], "correct_index": 2},
    {"text": "Which of these is a perfect square?", "options": ["50", "60", "64", "70"], "correct_index": 2},
    {"text": "Which of these is a perfect square?", "options": ["24", "36", "40", "48"], "correct_index": 1},
    {"text": "Which of these is a perfect square?", "options": ["80", "90", "100", "110"], "correct_index": 2},
    {"text": "Which of these is a perfect square?", "options": ["120", "144", "150", "160"], "correct_index": 1},
    {"text": "Which of these is NOT a perfect square?", "options": ["16", "25", "35", "49"], "correct_index": 2},
    {"text": "Which of these numbers is divisible by 3?", "options": ["101", "112", "123", "134"], "correct_index": 2},
    {"text": "Which of these numbers is divisible by 3?", "options": ["200", "201", "202", "203"], "correct_index": 1},
    {"text": "Which of these numbers is divisible by 7?", "options": ["40", "42", "44", "46"], "correct_index": 1},
    {"text": "Which of these numbers is divisible by 7?", "options": ["50", "54", "56", "58"], "correct_index": 2},
    {"text": "Which of these numbers is divisible by 11?", "options": ["100", "110", "112", "115"], "correct_index": 1},
    {"text": "Which of these is an even number?", "options": ["111", "223", "334", "445"], "correct_index": 2},
    {"text": "Which of these is an odd number?", "options": ["200", "222", "244", "301"], "correct_index": 3},
    {"text": "Which of these is a multiple of 8?", "options": ["50", "60", "64", "70"], "correct_index": 2},
    {"text": "Which of these is a multiple of 9?", "options": ["82", "83", "84", "81"], "correct_index": 3},
    {"text": "Which of these is a multiple of 12?", "options": ["70", "84", "90", "98"], "correct_index": 1},
    {"text": "Which word is spelled correctly?", "options": ["Accomodate", "Acommodate", "Accommodate", "Accommodaate"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Recieve", "Receve", "Recieve", "Receive"], "correct_index": 3},
    {"text": "Which word is spelled correctly?", "options": ["Occurance", "Occurence", "Occurrence", "Ocurrence"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Independant", "Independant", "Independent", "Indeependant"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Definately", "Definitely", "Definitly", "Definatly"], "correct_index": 1},
    {"text": "Which word is spelled correctly?", "options": ["Seperate", "Seprate", "Separate", "Separete"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Garentee", "Guarantee", "Garantee", "Guarentee"], "correct_index": 1},
    {"text": "Which word is spelled correctly?", "options": ["Neccessary", "Neccesary", "Necessary", "Necessery"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Harrass", "Harras", "Harass", "Harrass"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Millenium", "Milennium", "Milennium", "Millennium"], "correct_index": 3},
    {"text": "Which word is spelled correctly?", "options": ["Priviledge", "Privilege", "Privelege", "Privlege"], "correct_index": 1},
    {"text": "Which word is spelled correctly?", "options": ["Supercede", "Superseed", "Supersede", "Superceed"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Concious", "Conshous", "Conscious", "Consious"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Wierd", "Wired", "Weird", "Weerd"], "correct_index": 2},
    {"text": "Which word is spelled correctly?", "options": ["Liason", "Liaison", "Liaisson", "Leason"], "correct_index": 1},
    {"text": "Which of these is the largest fraction?", "options": ["½", "⅓", "¼", "⅙"], "correct_index": 0},
    {"text": "Which of these is the smallest fraction?", "options": ["½", "⅓", "¼", "⅕"], "correct_index": 3},
    {"text": "Which of these is the largest decimal?", "options": ["0.3", "0.33", "0.303", "0.033"], "correct_index": 1},
    {"text": "Which of these is the smallest decimal?", "options": ["0.5", "0.05", "0.55", "0.505"], "correct_index": 1},
    {"text": "Which of these numbers is closest to 100?", "options": ["89", "94", "107", "112"], "correct_index": 1},
    {"text": "Which of these numbers is closest to 50?", "options": ["43", "46", "53", "58"], "correct_index": 2},
    {"text": "Which of these is a factor of 24?", "options": ["5", "7", "8", "9"], "correct_index": 2},
    {"text": "Which of these is a factor of 36?", "options": ["5", "7", "8", "9"], "correct_index": 3},
    {"text": "Which of these is NOT a factor of 30?", "options": ["5", "6", "7", "10"], "correct_index": 2},
    {"text": "Which of these is a factor of 48?", "options": ["7", "9", "11", "12"], "correct_index": 3},
    {"text": "Which Roman numeral equals 9?", "options": ["VIIII", "IIX", "IX", "XI"], "correct_index": 2},
    {"text": "Which Roman numeral equals 40?", "options": ["XXXX", "XL", "LX", "VL"], "correct_index": 1},
    {"text": "Which Roman numeral equals 90?", "options": ["LXXXX", "XC", "CX", "LXXL"], "correct_index": 1},
    {"text": "Which Roman numeral equals 14?", "options": ["XIIII", "IVX", "XIV", "VIX"], "correct_index": 2},
    {"text": "What is 2⁵?", "options": ["10", "16", "32", "64"], "correct_index": 2},
    {"text": "What is 3³?", "options": ["9", "18", "27", "81"], "correct_index": 2},
    {"text": "What is 4²?", "options": ["8", "12", "16", "20"], "correct_index": 2},
    {"text": "What is √144?", "options": ["10", "11", "12", "13"], "correct_index": 2},
    {"text": "What is √64?", "options": ["6", "7", "8", "9"], "correct_index": 2},
    {"text": "What is √225?", "options": ["13", "14", "15", "16"], "correct_index": 2},
    {"text": "Which of these angles is obtuse?", "options": ["45°", "90°", "120°", "180°"], "correct_index": 2},
    {"text": "Which of these angles is acute?", "options": ["90°", "100°", "120°", "60°"], "correct_index": 3},
    {"text": "How many sides does a hexagon have?", "options": ["5", "6", "7", "8"], "correct_index": 1},
    {"text": "How many sides does a heptagon have?", "options": ["6", "7", "8", "9"], "correct_index": 1},
    {"text": "How many sides does a decagon have?", "options": ["8", "9", "10", "12"], "correct_index": 2},
    {"text": "How many sides does an octagon have?", "options": ["6", "7", "8", "9"], "correct_index": 2},
    {"text": "Which planet is closest to the Sun?", "options": ["Venus", "Earth", "Mars", "Mercury"], "correct_index": 3},
    {"text": "Which is the largest planet in our solar system?", "options": ["Saturn", "Jupiter", "Neptune", "Uranus"], "correct_index": 1},
    {"text": "How many planets are in our solar system?", "options": ["7", "8", "9", "10"], "correct_index": 1},
    {"text": "Which element has the symbol O?", "options": ["Gold", "Osmium", "Oxygen", "Oganesson"], "correct_index": 2},
    {"text": "Which element has the symbol Fe?", "options": ["Fluorine", "Francium", "Iron", "Fermium"], "correct_index": 2},
    {"text": "Which element has the symbol Au?", "options": ["Silver", "Aluminium", "Gold", "Argon"], "correct_index": 2},
    {"text": "Which element has the symbol Na?", "options": ["Nitrogen", "Neon", "Sodium", "Nickel"], "correct_index": 2},
    {"text": "Which element has the symbol K?", "options": ["Krypton", "Potassium", "Kurchatovium", "Kelvin"], "correct_index": 1},
    {"text": "Which element has the symbol Ag?", "options": ["Argon", "Silver", "Aluminium", "Antimony"], "correct_index": 1},
    {"text": "Which element has the symbol Pb?", "options": ["Phosphorus", "Platinum", "Lead", "Polonium"], "correct_index": 2},
    {"text": "Which element has the symbol Hg?", "options": ["Hydrogen", "Holmium", "Mercury", "Hafnium"], "correct_index": 2},
    {"text": "Which element has the symbol Cu?", "options": ["Calcium", "Cobalt", "Copper", "Chromium"], "correct_index": 2},
    {"text": "What is the chemical formula for water?", "options": ["HO", "H2O", "H2O2", "HO2"], "correct_index": 1},
    {"text": "What is the chemical formula for table salt?", "options": ["KCl", "MgCl", "CaCl2", "NaCl"], "correct_index": 3},
    {"text": "What is the chemical formula for carbon dioxide?", "options": ["CO", "CO2", "C2O", "CO3"], "correct_index": 1},
    {"text": "Which country has the largest land area?", "options": ["Canada", "China", "USA", "Russia"], "correct_index": 3},
    {"text": "Which is the longest river in the world?", "options": ["Amazon", "Yangtze", "Nile", "Mississippi"], "correct_index": 2},
    {"text": "Which is the tallest mountain in the world?", "options": ["K2", "Kangchenjunga", "Everest", "Lhotse"], "correct_index": 2},
    {"text": "Which is the largest ocean?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "correct_index": 3},
    {"text": "Which is the smallest continent?", "options": ["Europe", "Antarctica", "Australia", "South America"], "correct_index": 2},
    {"text": "Which is the largest continent?", "options": ["Africa", "Asia", "North America", "Europe"], "correct_index": 1},
    {"text": "How many bones are in the adult human body?", "options": ["186", "196", "206", "216"], "correct_index": 2},
    {"text": "How many chromosomes do humans have?", "options": ["23", "44", "46", "48"], "correct_index": 2},
    {"text": "What is the atomic number of carbon?", "options": ["4", "6", "8", "12"], "correct_index": 1},
    {"text": "What is the atomic number of hydrogen?", "options": ["1", "2", "3", "4"], "correct_index": 0},
    {"text": "What is the atomic number of oxygen?", "options": ["6", "7", "8", "9"], "correct_index": 2},
    {"text": "How many degrees are in a triangle?", "options": ["90°", "120°", "180°", "360°"], "correct_index": 2},
    {"text": "How many degrees are in a full circle?", "options": ["180°", "270°", "360°", "400°"], "correct_index": 2},
    {"text": "How many letters are in the English alphabet?", "options": ["24", "25", "26", "27"], "correct_index": 2},
    {"text": "Which number is both even and prime?", "options": ["1", "2", "4", "6"], "correct_index": 1},
    {"text": "What is the next prime after 7?", "options": ["8", "9", "10", "11"], "correct_index": 3},
    {"text": "What is the next prime after 13?", "options": ["14", "15", "16", "17"], "correct_index": 3},
    {"text": "What is the next prime after 19?", "options": ["20", "21", "22", "23"], "correct_index": 3},
    {"text": "Which of these is a Fibonacci number?", "options": ["10", "12", "13", "15"], "correct_index": 2},
    {"text": "Which of these is a Fibonacci number?", "options": ["20", "21", "22", "24"], "correct_index": 1},
    {"text": "Which of these is NOT a Fibonacci number?", "options": ["8", "13", "20", "21"], "correct_index": 2},
    {"text": "What is 10% of 350?", "options": ["30", "35", "40", "45"], "correct_index": 1},
    {"text": "What is 25% of 200?", "options": ["25", "40", "50", "75"], "correct_index": 2},
    {"text": "What is 50% of 90?", "options": ["30", "40", "45", "55"], "correct_index": 2},
    {"text": "What is 75% of 80?", "options": ["45", "50", "60", "70"], "correct_index": 2},
    {"text": "How many seconds are in a minute?", "options": ["30", "45", "60", "100"], "correct_index": 2},
    {"text": "How many minutes are in an hour?", "options": ["30", "45", "60", "100"], "correct_index": 2},
    {"text": "How many hours are in a day?", "options": ["12", "20", "24", "48"], "correct_index": 2},
    {"text": "How many days are in a leap year?", "options": ["364", "365", "366", "367"], "correct_index": 2},
    {"text": "How many months have 31 days?", "options": ["5", "6", "7", "8"], "correct_index": 2},
    {"text": "Which of these is the speed of sound (approx) in m/s?", "options": ["33", "133", "343", "1343"], "correct_index": 2},
    {"text": "What is the boiling point of water in Celsius?", "options": ["90°C", "95°C", "100°C", "110°C"], "correct_index": 2},
    {"text": "What is the freezing point of water in Celsius?", "options": ["-10°C", "-5°C", "0°C", "5°C"], "correct_index": 2},
    {"text": "How many sides does a pentagon have?", "options": ["4", "5", "6", "7"], "correct_index": 1},
    {"text": "How many sides does a nonagon have?", "options": ["7", "8", "9", "10"], "correct_index": 2},
    {"text": "Which of these is a right angle?", "options": ["45°", "60°", "90°", "120°"], "correct_index": 2},
    {"text": "What is 1000 in Roman numerals?", "options": ["C", "D", "M", "L"], "correct_index": 2},
    {"text": "What is 500 in Roman numerals?", "options": ["C", "D", "L", "M"], "correct_index": 1},
    {"text": "What is 100 in Roman numerals?", "options": ["C", "D", "L", "M"], "correct_index": 0},
    {"text": "What is 50 in Roman numerals?", "options": ["C", "D", "L", "M"], "correct_index": 2},
]


# ── Pool seeding ──────────────────────────────────────────────────────────────

def seed_all_pools() -> None:
    db.seed_pool("geography", GEOGRAPHY_POOL)
    db.seed_pool("word", WORD_POOL)
    db.seed_pool("speed", SPEED_POOL)


# ── Daily question generation ─────────────────────────────────────────────────

async def generate_daily_questions(game_date: str) -> None:
    """Generate and persist 8 questions for the given date.

    Layout: Q1–Q4 math (tiers 1–4), Q5 geography, Q6–Q7 word, Q8 speed.
    """
    math_qs = generate_math_questions()

    pool_slots = [
        ("geography", "geography"),
        ("word", "word"),
        ("word", "word"),
        ("speed", "speed"),
    ]

    pool_qs = []
    for category, qtype in pool_slots:
        row = db.pick_pool_question(category, game_date)
        if row is None:
            # All questions used within last 30 days — reset and retry
            with _sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE question_pool SET last_used = NULL WHERE category = ?",
                    (category,)
                )
            row = db.pick_pool_question(category, game_date)
        if row:
            pool_qs.append({
                "type": qtype,
                "text": row["question_text"],
                "options": json.loads(row["options"]),
                "correct_index": row["correct_index"],
                "pool_id": row["id"],
            })

    all_qs = math_qs + pool_qs

    for i, q in enumerate(all_qs):
        db.store_question(
            game_date=game_date,
            question_index=i,
            question_type=q["type"],
            question_text=q["text"],
            options=q["options"],
            correct_index=q["correct_index"],
            pool_question_id=q.get("pool_id"),
        )
